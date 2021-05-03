# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback

# third-party
import requests
from flask import Blueprint, request, Response, send_file, render_template, redirect, jsonify
from flask_login import login_required

# sjva 공용
from framework.logger import get_logger
from framework import app, db, scheduler, check_api
from framework.util import Util

# 패키지
package_name = __name__.split('.')[0]
logger = get_logger(package_name)
from .logic import Logic
from .logic import LogicNormal
from .model import ModelSetting, ModelRss, ModelFeed
#########################################################


#########################################################
# 플러그인 공용    
#########################################################
blueprint = Blueprint(package_name, package_name, url_prefix='/%s' %  package_name, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
menu = {
    'main' : [package_name, u'RSS 다운로드'],
    'sub' : [
        ['setting', u'설정'], ['rss', u'RSS 관리'], ['list', u'Feed 목록'], ['log', u'로그']
    ],
    'category' : 'torrent'
}  

plugin_info = {
    'version' : '0.1.0.0',
    'name' : package_name,
    'category_name' : 'torrent',
    'developer' : 'soju6jan',
    'description' : u'RSS 다운로드',
    'home' : 'https://github.com/soju6jan/' + package_name,
    'more' : '',
}

def plugin_load():
    logger.info('%s plugin load' % package_name)
    Logic.plugin_load()

def plugin_unload():
    Logic.plugin_unload()

def process_telegram_data(data):
    pass
        
#########################################################
# WEB Menu   
#########################################################
@blueprint.route('/')
def home():
    return redirect('/%s/list' % package_name)

@blueprint.route('/<sub>')
@login_required
def first_menu(sub):
    arg = ModelSetting.to_dict()
    arg['package_name']  = package_name
    if sub == 'setting':

        arg['scheduler'] = str(scheduler.is_include(package_name))
        arg['is_running'] = str(scheduler.is_running(package_name))
        return render_template('%s_%s.html' % (package_name, sub), arg=arg)
    elif sub == 'rss':
        try:
            import downloader
            arg['default_download_program'], arg['default_download_path'] = downloader.Logic.get_default_value()
            arg['default_download_path'] = arg['default_download_path'].replace('\\', '\\\\')
        except:
            arg['default_download_program'] = '0'
            arg['default_download_path'] = ''
        return render_template('%s_%s.html' % (package_name, sub), arg=arg)
    elif sub == 'list':
        arg['is_torrent_info_installed'] = False
        try:
            import torrent_info
            arg['is_torrent_info_installed'] = True
        except Exception as e: 
            pass
        arg['is_offcloud_installed'] = False
        try:
            import offcloud2
            arg['is_offcloud_installed'] = True
        except Exception as e: 
            pass
        try:
            arg['rss_id'] = request.args.get('rss_id')
        except Exception as e: 
            pass
        if arg['rss_id'] is None:
            arg['rss_id'] = 'all'
        arg['rss_list'] = ModelRss.get_list(by_dict=True)
        return render_template('%s_%s.html' % (package_name, sub), arg=arg)
    elif sub == 'log':
        return render_template('log.html', package=package_name)
    return render_template('sample.html', title='%s - %s' % (package_name, sub))


#########################################################
# For UI
#########################################################
@blueprint.route('/ajax/<sub>', methods=['GET', 'POST'])
@login_required
def ajax(sub):
    try:
        if sub == 'setting_save':
            ret = ModelSetting.setting_save(request)
            return jsonify(ret)
        elif sub == 'scheduler':
            go = request.form['scheduler']
            logger.debug('scheduler :%s', go)
            if go == 'true':
                Logic.scheduler_start()
            else:
                Logic.scheduler_stop()
            return jsonify(go)
        elif sub == 'one_execute':
            ret = Logic.one_execute()
            return jsonify(ret)
        elif sub == 'reset_db':
            ret = Logic.reset_db()
            return jsonify(ret)  

        # rss
        elif sub == 'rss_list':
            ret = {}
            ret['rss_list'] = ModelRss.get_list(by_dict=True)
            return jsonify(ret)
        elif sub == 'save_rss':
            ret = {}
            ret['ret'] = ModelRss.save(request)
            ret['rss_list'] = ModelRss.get_list(by_dict=True)
            return jsonify(ret)
        elif sub == 'rss_remove':
            ret = {}
            rss_id = request.form['rss_id']
            ModelFeed.remove(rss_id)
            ret['ret'] = ModelRss.remove(rss_id)
            ret['rss_list'] = ModelRss.get_list(by_dict=True)
            return jsonify(ret)

        # list
        elif sub == 'web_list':
            ret = ModelFeed.web_list(request)
            ret['rss_list'] = ModelRss.get_list(by_dict=True)
            return jsonify(ret)
        elif sub == 'feed_download':
            LogicNormal.feed_download(request.form['id'])
            return jsonify({})
    except Exception as e: 
        logger.error('Exception:%s', e)
        logger.error(traceback.format_exc())     
