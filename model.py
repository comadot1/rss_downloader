# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback
import json
import datetime
# third-party
from sqlalchemy import or_, and_, func, not_, desc
from sqlalchemy.orm.attributes import flag_modified

# sjva 공용
from framework import db, app, path_app_root
from framework.util import Util

# 패키지
from downloader import ModelDownloaderItem #이게 있어야 먼저 DB 로딩
from .plugin import logger, package_name


#########################################################

app.config['SQLALCHEMY_BINDS'][package_name] = 'sqlite:///%s' % (os.path.join(path_app_root, 'data', 'db', '%s.db' % package_name))

class ModelSetting(db.Model):
    __tablename__ = '%s_setting' % package_name
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = package_name

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String, nullable=False)
 
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __repr__(self):
        return repr(self.as_dict())

    def as_dict(self):
        return {x.name: getattr(self, x.name) for x in self.__table__.columns}

    @staticmethod
    def get(key):
        try:
            return db.session.query(ModelSetting).filter_by(key=key).first().value.strip()
        except Exception as e:
            logger.error('Exception:%s %s', e, key)
            logger.error(traceback.format_exc())
            
    
    @staticmethod
    def get_int(key):
        try:
            return int(ModelSetting.get(key))
        except Exception as e:
            logger.error('Exception:%s %s', e, key)
            logger.error(traceback.format_exc())
    
    @staticmethod
    def get_bool(key):
        try:
            return (ModelSetting.get(key) == 'True')
        except Exception as e:
            logger.error('Exception:%s %s', e, key)
            logger.error(traceback.format_exc())

    @staticmethod
    def set(key, value):
        try:
            item = db.session.query(ModelSetting).filter_by(key=key).with_for_update().first()
            if item is not None:
                item.value = value.strip()
                db.session.commit()
            else:
                db.session.add(ModelSetting(key, value.strip()))
        except Exception as e:
            logger.error('Exception:%s %s', e, key)
            logger.error(traceback.format_exc())

    @staticmethod
    def to_dict():
        try:
            return Util.db_list_to_dict(db.session.query(ModelSetting).all())
        except Exception as e:
            logger.error('Exception:%s %s', e, key)
            logger.error(traceback.format_exc())


    @staticmethod
    def setting_save(req):
        try:
            for key, value in req.form.items():
                logger.debug('Key:%s Value:%s', key, value)
                if key in ['scheduler', 'is_running', 'global_scheduler_sub']:
                    continue
                if key == 'default_username' and value.startswith('==='):
                    continue
                entity = db.session.query(ModelSetting).filter_by(key=key).with_for_update().first()
                entity.value = value
            db.session.commit()
            return True                  
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            logger.debug('Error Key:%s Value:%s', key, value)
            return False

    @staticmethod
    def get_list(key):
        try:
            value = ModelSetting.get(key)
            values = [x.strip().replace(' ', '').strip() for x in value.replace('\n', '|').split('|')]
            values = Util.get_list_except_empty(values)
            return values
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            logger.error('Error Key:%s Value:%s', key, value)

#########################################################

class ModelRss(db.Model):
    __tablename__ = '%s_rss' % package_name
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = package_name

    id = db.Column(db.Integer, primary_key=True)
    created_time = db.Column(db.DateTime)
    reserved = db.Column(db.JSON)

    update_time = db.Column(db.DateTime)
    name = db.Column(db.String)
    rss_url = db.Column(db.String)
    download_program = db.Column(db.String)
    download_path = db.Column(db.String)
    
    download_mode = db.Column(db.String) #0:필터 사용 1:모두 받기. 2: RSS만 저장, 

    include_keyword = db.Column(db.String)
    exclude_keyword = db.Column(db.String)

    use_filename_filter = db.Column(db.Boolean)
    filename_include_keyword = db.Column(db.String)  #정규식 혹은 키워드  || 폴더 
    filename_exclude_keyword = db.Column(db.String)

    feed_list = db.relationship('ModelFeed', backref='rss', lazy=True) 
    

    def __init__(self):
        self.created_time = datetime.datetime.now()
        self.use_filename_filter = False

    def __repr__(self):
        return repr(self.as_dict())

    def as_dict(self):
        ret = {x.name: getattr(self, x.name) for x in self.__table__.columns}
        ret['created_time'] = self.created_time.strftime('%m-%d %H:%M:%S')
        ret['update_time'] = '' if self.update_time is None else self.created_time.strftime('%m-%d %H:%M:%S')
        ret['name'] = self.name if self.name is not None else self.id
        
        return ret
    
    @staticmethod
    def save(req):
        try:
            rss_id = req.form['rss_id']
            if rss_id == '-1':
                entity = ModelRss()
            else:
                entity = db.session.query(ModelRss).filter_by(id=rss_id).first()
            entity.name = req.form['name']
            entity.rss_url = req.form['rss_url']
            entity.download_program = req.form['download_program']
            entity.download_path = req.form['download_path']
            entity.download_mode = req.form['download_mode']
            entity.include_keyword = req.form['include_keyword']
            entity.exclude_keyword = req.form['exclude_keyword']
            """
            entity.use_filename_filter = (req.form['use_filename_filter'] == 'True')
            entity.filename_include_keyword = req.form['filename_include_keyword']
            entity.filename_exclude_keyword = req.form['filename_exclude_keyword']
            """
            db.session.add(entity)
            db.session.commit()
            return 'success'                  
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return 'fail'
    
    @staticmethod
    def get_list(by_dict=False):
        try:
            tmp = db.session.query(ModelRss).all()
            if by_dict:
                tmp = [x.as_dict() for x in tmp]
            return tmp
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    
    @staticmethod
    def remove(rss_id):
        try:
            logger.debug('remove_rss id:%s', rss_id)
            entity = db.session.query(ModelRss).filter_by(id=rss_id).first()
            db.session.delete(entity)
            db.session.commit()
            return 'success'
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return 'fail'
    """
    @staticmethod
    def get_by_name(name):
        try:
            return db.session.query(ModelOffcloud2Job).filter_by(name=name).first()
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    """


class ModelFeed(db.Model):
    __tablename__ = '%s_feed' % package_name
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = package_name

    id = db.Column(db.Integer, primary_key=True)
    created_time = db.Column(db.DateTime)
    reserved = db.Column(db.JSON)

    rss_id = db.Column(db.Integer, db.ForeignKey('%s_rss.id' % package_name))
    title = db.Column(db.String)
    link = db.Column(db.String)
    description = db.Column(db.String)
    guid = db.Column(db.String)
    pubDate = db.Column(db.DateTime)

    status = db.Column(db.Integer) # 0: 최초상태. 1:요청 실패  10 : 요청 성공  11 : rss만 저장, 12:필터 조건 False

    downloader_item_id = db.Column(db.Integer, db.ForeignKey('plugin_downloader_item.id'))
    downloader_item = db.relationship('ModelDownloaderItem')

    log = db.Column(db.String)

    torrent_info = db.Column(db.JSON)
    filename = db.Column(db.String)
    dirname = db.Column(db.String)
    filecount = db.Column(db.Integer)


    def __init__(self):
        self.created_time = datetime.datetime.now()
        self.status = 0

    def __repr__(self):
        return repr(self.as_dict())

    def as_dict(self):
        ret = {x.name: getattr(self, x.name) for x in self.__table__.columns}
        ret['created_time'] = self.created_time.strftime('%m-%d %H:%M:%S')
        ret['rss'] = self.rss.as_dict()

        try:
            ret['downloader_item'] = self.downloader_item.as_dict()
        except:
            pass
        return ret
    
    @staticmethod
    def get_feed_list_by_scheduler(rss):
        try:
            query = db.session.query(ModelFeed) \
                .filter(ModelFeed.rss_id == rss.id ) \
                .filter(ModelFeed.status < 10 ) \
                .filter(ModelFeed.created_time > datetime.datetime.now() + datetime.timedelta(days=-7))
                # \
                #.filter(ModelFeed.oc_status != 'NOSTATUS')
            return query.all()
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    """
    def make_torrent_info(self):
        try:
            if self.job.use_tracer and self.torrent_info is None and self.link.startswith('magnet'):
                from torrent_info import Logic as TorrentInfoLogic
                tmp = TorrentInfoLogic.parse_magnet_uri(self.link)
                if tmp is not None:
                    self.torrent_info = tmp
                    flag_modified(self, "torrent_info")
                    info = Util.get_max_size_fileinfo(tmp)
                    self.filename = info['filename']
                    self.dirname = info['dirname']
                    self.filecount = tmp['num_files']
                    return True
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        return False
    """

    @staticmethod
    def remove(rss_id):
        try:
            db.session.query(ModelFeed).filter_by(rss_id=rss_id).delete()
            db.session.commit()
            return 'success'
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return 'fail'
    

    @staticmethod
    def web_list(req):
        try:
            ret = {}
            page = 1
            page_size = 30
            job_id = ''
            search = ''
            if 'page' in req.form:
                page = int(req.form['page'])
            if 'search_word' in req.form:
                search = req.form['search_word']
            rss_select = 'all'
            if 'rss_select' in req.form:
                rss_select = req.form['rss_select']
            
            option = 'all'
            if 'option' in req.form:
                option = req.form['option']

            query = ModelFeed.make_query(rss_id=rss_select, option=option, search=search)
            
            count = query.count()
            query = (query.order_by(desc(ModelFeed.id))
                        .limit(page_size)
                        .offset((page-1)*page_size)
                )
            logger.debug('ModelFeed count:%s', count)

            lists = query.all()
            ret['list'] = [item.as_dict() for item in lists]
            ret['paging'] = Util.get_paging_info(count, page, page_size)
            return ret
        except Exception as e:
            logger.debug('Exception:%s', e)
            logger.debug(traceback.format_exc())

    """
    @staticmethod
    def api_list(req):
        try:
            job = req.args.get('job')
            option = req.args.get('option')
            search = req.args.get('search')
            count = req.args.get('count')
            if count is None or count == '':
                count = 100

            query = ModelFeed.make_query(job_name=job, option=option, search=search)
            query = (query.order_by(desc(ModelFeed.id))
                        .limit(count)
                )
            lists = query.all()
            return lists
        except Exception as e:
            logger.debug('Exception:%s', e)
            logger.debug(traceback.format_exc())
    """

    @staticmethod
    def make_query(rss_id='all', option='all', search=''):
        try:
            query = db.session.query(ModelFeed)
            job = None
            if rss_id != 'all':
                query = query.filter_by(rss_id=rss_id)

            if search is not None and search != '':
                if search.find('|') != -1:
                    tmp = search.split('|')
                    conditions = []
                    for tt in tmp:
                        if tt != '':
                            conditions.append(ModelFeed.title.like('%'+tt.strip()+'%') )
                    query = query.filter(or_(*conditions))
                elif search.find(',') != -1:
                    tmp = search.split(',')
                    for tt in tmp:
                        if tt != '':
                            query = query.filter(ModelFeed.title.like('%'+tt.strip()+'%'))
                else:
                    query = query.filter(ModelFeed.title.like('%'+search+'%'))

            if option != 'all':
                query = query.filter(ModelFeed.status == int(option))
            return query
        except Exception as e:
            logger.debug('Exception:%s', e)
            logger.debug(traceback.format_exc())

    
    


