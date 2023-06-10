# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback
from datetime import datetime
import re

# third-party

# sjva 공용
from framework import app, db, scheduler, path_app_root
from framework.job import Job
from framework.util import Util
from framework.common.rss import RssUtil
from system.logic import SystemLogic


# 패키지
from .plugin import logger, package_name
from .model import ModelSetting, ModelRss, ModelFeed
#########################################################

class LogicNormal(object):
    @staticmethod
    def scheduler_function():
        try:
            logger.debug('scheduler_function')
            LogicNormal.process_insert_feed()
            LogicNormal.process_download_mode()

        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())



    @staticmethod
    def process_insert_feed():
        try:
            rss_list = ModelRss.get_list()
            for rss in rss_list:
                try:
                    logger.debug('Rss :%s', rss.id)
                    feed_list = RssUtil.get_rss(rss.rss_url)
                    #logger.debug(feed_list)
                    if not feed_list:
                        continue
                    flag_commit = False
                    count = 0
                    #
                    for feed in reversed(feed_list):
                        if ModelSetting.get_bool('allow_duplicate'):
                            entity = db.session.query(ModelFeed).filter_by(rss_id=rss.id, link=feed.link).first()
                        else:
                            entity = db.session.query(ModelFeed).filter_by(link=feed.link).first()
                        if entity is None:
                            r = ModelFeed()
                            r.title = feed.title
                            r.link = feed.link
                            #db.session.add(r)
                            rss.feed_list.append(r)
                            flag_commit = True
                            count += 1
                    if flag_commit:
                        db.session.commit()
                    logger.debug('Rss:%s flag_commit:%s count:%s', rss.id, flag_commit, count)
                except Exception as e:
                    logger.error(e)
                    logger.error(traceback.format_exc())
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())
    

    @staticmethod
    def get_filter(f, is_include):
        tmps = [x.strip().replace(' ', '').strip() for x in f.replace('\n', '||').split('||')]
        tmps = Util.get_list_except_empty(tmps)
        if is_include:
            ret = []
            for t in tmps:
                tt = t.split('>>')
                if len(tt) == 1:
                    ret.append([tt[0], None])
                else:
                    ret.append([tt[0], tt[1]])
            return ret
        else:
            return tmps
        

    @staticmethod
    def process_download_mode():
        try:
            for rss in ModelRss.get_list():
                if rss.download_mode == '0':
                    include_keywords = LogicNormal.get_filter(rss.include_keyword, True) 
                    exclude_keywords = LogicNormal.get_filter(rss.exclude_keyword, False)

                for feed in ModelFeed.get_feed_list_by_scheduler(rss):
                    try:
                        feed.log = ''
                        request_download = False
                        if rss.download_mode == '0': #필터
                            for tmp in include_keywords:
                                match = re.search(tmp[0], feed.title.replace(' ', '').strip())
                                if match or tmp[1] == 'all':
                                    request_download = True
                                    feed.log += u'\n매칭:%s' % tmp[0]
                                    if feed.downloader_item.title == feed.downloader_item.download_url[20:60]:
                                        feed.downloader_item.title = feed.title
                                    download_url = feed.link
                                    download_program = rss.download_program
                                    download_path = rss.download_path if tmp[1] is None else tmp[1]
                                    break
                            if request_download:
                                for tmp in exclude_keywords:
                                    match = re.search(tmp, feed.title.replace(' ', '').strip())
                                    if match:
                                        request_download = False
                                        feed.log += u'\n제외:%s' % tmp
                                        feed.status = 12
                                        break
                            else:
                                feed.log += u'매칭 조건 없음'
                                feed.status = 12

                        elif rss.download_mode == '1': #모두받기
                            request_download = True
                            if feed.downloader_item.title == feed.downloader_item.download_url[20:60]:
                                feed.downloader_item.title = feed.title
                            download_url = feed.link
                            download_program = rss.download_program
                            download_path = rss.download_path
                            feed.log = u'다운로드 모드 : 모두 받기'
                        elif rss.download_mode == '2': #저장만
                            #feed.log = u'다운로드 모드 : Feed만 저장'
                            feed.status = 11
                            db.session.add(feed)

                        if request_download:
                            logger.debug('Feed Title:%s', feed.title)
                            import downloader
                            ret = downloader.Logic.add_download2(download_url, download_program, download_path)
                            if ret['ret'] == 'error':
                                feed.status = 1
                            else:
                                feed.status = 10
                                feed.downloader_item_id = ret['downloader_item_id']
                            db.session.add(feed)
                    except Exception as e:
                        logger.error(e)
                        logger.error(traceback.format_exc())
            db.session.commit()
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())

    @staticmethod
    def feed_download(feed_id):
        try:
            feed = db.session.query(ModelFeed).filter_by(id=feed_id).with_for_update().first()
            if feed is not None:
                if feed.downloader_item.title == feed.downloader_item.download_url[20:60]:
                    feed.downloader_item.title = feed.title
                download_url = feed.link
                download_program = feed.rss.download_program
                download_path = feed.rss.download_path
                feed.log += u'\n수동 요청'

                import downloader
                ret = downloader.Logic.add_download2(download_url, download_program, download_path)
                if ret['ret'] == 'error':
                    feed.status = 1
                else:
                    feed.status = 10
                    feed.downloader_item_id = ret['downloader_item_id']
                db.session.commit()
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())

    
