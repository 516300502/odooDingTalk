# -*- coding: utf-8 -*-
###################################################################################
#    Copyright (C) 2019 SuXueFeng GNU
###################################################################################

import base64
import hashlib
import hmac
import logging
import time
from datetime import datetime, timedelta
from odoo import fields, _
from urllib.parse import quote
from dingtalk.client import AppKeyClient
from dingtalk.storage.memorystorage import MemoryStorage
from odoo.http import request

mem_storage = MemoryStorage()
_logger = logging.getLogger(__name__)


def get_client(obj=None):
    """
    得到客户端
    :param obj: 当自动任务时获取客户端时需传入一个对象，否则会报对象无绑定的错误
    :return: client
    """
    try:
        dt_corp_id = request.env['ir.config_parameter'].sudo().get_param('dingtalk_base.dt_corp_id')
        app_key, app_secret = get_key_and_secrect(request)
    except Exception:
        dt_corp_id = obj.env['ir.config_parameter'].sudo().get_param('dingtalk_base.dt_corp_id')
        app_key, app_secret = get_key_and_secrect(obj)
    return AppKeyClient(dt_corp_id, app_key, app_secret, storage=mem_storage)


def get_key_and_secrect(obj):
    """
    获取配置项中钉钉key和app_secret
    :return:
    """
    app_key = obj.env['ir.config_parameter'].sudo().get_param('dingtalk_base.dt_app_key')
    app_secret = obj.env['ir.config_parameter'].sudo().get_param('dingtalk_base.dt_app_secret')
    if app_key and app_secret:
        return app_key.replace(' ', ''), app_secret.replace(' ', '')
    return '0000', '0000'


def get_delete_is_synchronous():
    """
    判读是否删除odoo员工、部门、联系人时同时删除钉钉上的数据
    :return:
    """
    return request.env['ir.config_parameter'].sudo().get_param('dingtalk_base.dt_delete_is_sy')


def get_login_id():
    """
    返回登录id
    :return: login_id
    """
    login_id = request.env['ir.config_parameter'].sudo().get_param('dingtalk_base.dt_login_id')
    if login_id:
        return login_id.replace(' ', '')
    return '0000'


def get_login_id_and_key():
    """
    :return: login_id
    """
    login_id = request.env['ir.config_parameter'].sudo().get_param('dingtalk_base.dt_login_id')
    dt_login_secret = request.env['ir.config_parameter'].sudo().get_param('dingtalk_base.dt_login_secret')
    if login_id and dt_login_secret:
        return login_id.replace(' ', ''), dt_login_secret.replace(' ', '')
    return '0000', '0000'


def get_dt_corp_id():
    """
    :return: dt_corp_id
    """
    dt_corp_id = request.env['ir.config_parameter'].sudo().get_param('dingtalk_base.dt_corp_id')
    if dt_corp_id:
        return dt_corp_id.replace(' ', '')
    return '0000'


def get_serial_number():
    """
    :return: dt_serial_number
    """
    dt_serial_number = request.env['ir.config_parameter'].sudo().get_param('dingtalk_base.dt_serial_number')
    if dt_serial_number:
        return dt_serial_number.replace(' ', '')
    return False


def timestamp_to_local_date(time_num):
    """
    将13位毫秒时间戳转换为本地日期(+8h)
    :param time_num:
    :return: string datetime
    """
    to_second_timestamp = float(time_num / 1000)  # 毫秒转秒
    to_utc_datetime = time.gmtime(to_second_timestamp)  # 将时间戳转换为UTC时区（0时区）的时间元组struct_time
    to_str_datetime = time.strftime("%Y-%m-%d %H:%M:%S", to_utc_datetime)  # 将时间元组转成指定格式日期字符串
    to_datetime = fields.Datetime.from_string(to_str_datetime)  # 将字符串转成datetime对象
    to_local_datetime = fields.Datetime.context_timestamp(request, to_datetime)  # 将原生的datetime值(无时区)转换为具体时区的datetime
    to_str_datetime = fields.Datetime.to_string(to_local_datetime)  # datetime 转成 字符串
    return to_str_datetime


def datetime_to_stamp(time_num):
    """
    将时间转成13位时间戳
    :param time_num:
    :return: date_stamp
    """
    date_str = fields.Datetime.to_string(time_num)
    date_stamp = time.mktime(time.strptime(date_str, "%Y-%m-%d %H:%M:%S"))
    date_stamp = date_stamp * 1000
    return int(date_stamp)


def get_user_info_by_code(code):
    """
    根据扫码或账号密码登录返回的code获取用户信息
    :param code: code  账号或扫码登录返回的code
    :return:
    """
    login_id, login_secret = get_login_id_and_key()
    milli_time = lambda: int(round(time.time() * 1000))
    timestamp = str(milli_time())
    signature = hmac.new(login_secret.encode('utf-8'), timestamp.encode('utf-8'), hashlib.sha256).digest()
    signature = quote(base64.b64encode(signature), 'utf-8')
    url = "sns/getuserinfo_bycode?signature={}&timestamp={}&accessKey={}".format(signature, timestamp, login_id)
    result = get_client().post(url, {
        'tmp_auth_code': code,
        'signature': signature,
        'timestamp': timestamp,
        'accessKey': login_id
    })
    return result


def list_cut(mylist, limit):
    """
    列表分段
    :param mylist:列表集
    :param limit: 子列表元素限制数量
    :return:
    """
    length = len(mylist)
    cut_list = [mylist[i:i + limit] for i in range(0, length, limit)]
    return cut_list


def day_cut(begin_time, end_time, days):
    """
    日期分段
    :param begin_date:开始日期
    :param end_date:结束日期
    :param days: 最大间隔时间
    :return:
    """
    cut_day = []
    begin_time = datetime.strptime(str(begin_time), "%Y-%m-%d")
    end_time = datetime.strptime(str(end_time), "%Y-%m-%d")
    delta = timedelta(days=days)
    t1 = begin_time
    while t1 <= end_time:
        if end_time < t1 + delta:
            t2 = end_time
        else:
            t2 = t1 + delta
        t1_str = t1.strftime("%Y-%m-%d %H:%M:%S")
        t2_str = t2.strftime("%Y-%m-%d %H:%M:%S")
        cut_day.append([t1_str, t2_str])
        t1 = t2 + timedelta(seconds=1)
    return cut_day
