# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from __future__ import absolute_import, unicode_literals

import datetime
import time
from functools import partial
from typing import Optional

import arrow
import pytz
from django.conf import settings
from django.utils import timezone


def now():
    return timezone.now()


def now_str(_format="%Y-%m-%d %H:%M:%S"):
    return timezone.now().strftime(_format)


def localtime(value):
    """
    to local time
    :param value: datetime obj
    :return: 返回带本地(业务)时区的datetime对象
    """
    if timezone.is_aware(value):
        return timezone.localtime(value)
    return timezone.make_aware(value)


def mysql_time(value):
    """
    to mysql time
    :param value: datetime obj
    :return: 返回带本地(业务)时区的datetime对象
    """
    if settings.USE_TZ:
        if timezone.is_aware(value):
            return value
        else:
            return arrow.get(value).replace(tzinfo=timezone.get_current_timezone_name()).datetime
    else:
        if timezone.is_aware(value):
            return arrow.get(value).to(timezone.get_current_timezone_name()).naive
        else:
            return value


def biz_time_zone_offset():
    """
    获取业务的时区偏移
    """
    offset = arrow.now().replace(tzinfo=timezone.get_current_timezone().zone).format("Z")
    return str(offset[0]) + str(int(offset[1:3]))  # 转成小时的精度, 而不是分钟


def strftime_local(value, _format="%Y-%m-%d %H:%M:%S%z"):
    """
    转成业务时区字符串
    :param value: datetime obj
    """
    return localtime(value).strftime(_format)


def biz2utc_str(local_time, _format="%Y-%m-%d %H:%M:%S"):
    """
    功能: 业务时间字符串 转换成 零时区字符串
    场景: 界面传过来的时间需要转换成零时区去查询db或调用API
    """
    return arrow.get(local_time).replace(tzinfo=timezone.get_current_timezone().zone).to("utc").strftime(_format)


def utc2biz_str(utc_time, _format="%Y-%m-%d %H:%M:%S"):
    """
    功能: 零时区字符串 转换成 业务时间字符串
    场景: 从DB或调用API传回来的时间(utc时间)需要转换成业务时间再给到前端显示
    """
    return arrow.get(utc_time).to(timezone.get_current_timezone().zone).strftime(_format)


def get_timestamp_range_by_biz_date(date):
    """
    功能: 解析从浏览器传过来的日期格式字符串, 转成时间戳timestamp格式
    @return tuple(timestamp(unit: s), timestamp(unit: s))
    """
    start_timestamp = arrow.get(date).replace(tzinfo=timezone.get_current_timezone().zone).timestamp
    end_timestamp = start_timestamp + 86400  # 24 * 3600
    return start_timestamp, end_timestamp


def gen_default_time_range(days=1, offset=0):
    """
    功能: 生成默认的业务时间日期范围
    """
    biz_today = timezone.localtime(timezone.now()).date()
    if days + offset < 1:
        return (biz_today, biz_today + datetime.timedelta(1))
    return (biz_today - datetime.timedelta(days + offset - 1), biz_today + datetime.timedelta(1 - offset))


def parse_time_range(time_range=None, days=1, offset=0, _time_format="%Y-%m-%d %H:%M"):
    """
    功能: 解析从浏览器传过来的time_range, 转成UTC时区, 再返回timestamp
    场景: 获取图表数据
    @return tuple(timestamp(unit: s), timestamp(unit: s))
    """
    if not time_range:
        # 默认取业务时区当天的数据
        start, end = gen_default_time_range(days, offset)
    else:
        time_range = time_range.replace("&nbsp;", " ")
        start, end = [i.strip() for i in time_range.split("--")]
        # start = date_convert(start, 'datetime', _time_format)
        # end = date_convert(end, 'datetime', _time_format)
    tzinfo = timezone.get_current_timezone().zone
    start = arrow.get(start)
    end = arrow.get(end)

    # 没有时区信息时，使用业务时区补全
    if not hasattr(start.tzinfo, "_offset"):
        start = start.replace(tzinfo=tzinfo)
    if not hasattr(end.tzinfo, "_offset"):
        end = end.replace(tzinfo=tzinfo)
    return start.timestamp, end.timestamp


def str2date(_str, _format="%Y-%m-%d %H:%M:%S"):
    return datetime.datetime.strptime(_str, _format).date()


def str2utc(_str, _format="%Y-%m-%d %H:%M:%S"):
    """
    字符串转UTC
    """
    _datetime = datetime.datetime.strptime(_str, _format)
    return int(time.mktime(_datetime.timetuple()))


def datetime2utc(_datetime, _format="%Y-%m-%d %H:%M:%S"):
    """
    datetime转UTC
    """
    return int(time.mktime(_datetime.timetuple()))


def utc2datetime(_utc, _format="%Y-%m-%d %H:%M:%S"):
    """
    UTC转datetime
    """
    return time.strftime(_format, time.localtime(int(_utc)))


def utc2date(_utc, _format="%Y-%m-%d %H:%M"):
    """
    UTC转date
    """
    return time.strftime(_format, time.localtime(int(_utc)))


def get_datetime_range(period, distance, now=None, rounding=True):
    now = now or localtime(timezone.now())
    if period == "day":
        begin = arrow.get(now).replace(days=-distance)
        end = arrow.get(now)
        if rounding:
            begin = begin.ceil("day")
            end = end.ceil("day")
    elif period == "hour":
        begin = arrow.get(now).replace(days=-distance)
        end = arrow.get(now)
        if rounding:
            begin = begin.ceil("hour")
            end = end.ceil("hour")
    else:
        raise TypeError("invalid period: %r" % period)

    if settings.USE_TZ:
        return begin.datetime, end.datetime
    else:
        return begin.naive, end.naive


def get_datetime_list(begin_time, end_time, period):
    if period == "day":
        timedelta = "days"
    elif period == "hour":
        timedelta = "hours"
    else:
        raise TypeError("invalid period: %r" % period)

    datetime_list = []
    item = begin_time
    while item < end_time:
        datetime_list.append(item)
        item = item + timezone.timedelta(**{timedelta: 1})

    return datetime_list


def utcoffset_in_seconds():
    """
    获取当前时区偏移量（秒）
    """
    return localtime(now()).utcoffset().total_seconds()


def datetime2timestamp(value):
    """
    datetime转timestamp格式
    """
    return time.mktime(localtime(value).timetuple())


def hms_string(sec_elapsed, display_num=2, day_unit="d", hour_unit="h", minute_unit="m", second_unit="s"):
    """
    将秒数转化为 人类易读时间 1d 12h 3m
    """
    d = int(sec_elapsed / (60 * 60) / 24)
    h = int((sec_elapsed - d * 24 * 3600) / 3600)
    m = int((sec_elapsed - d * 24 * 3600 - h * 3600) / 60)
    s = int(sec_elapsed - d * 24 * 3600 - h * 3600 - m * 60)

    units = [(d, day_unit), (h, hour_unit), (m, minute_unit), (s, second_unit)]
    time_str = ""
    index = 0
    for unit in units:
        if unit[0] == 0:
            continue

        index += 1
        time_str += "{}{}".format(unit[0], unit[1])
        if index >= display_num:
            return time_str

    return time_str


def dt_str2dt_as_timezone(
    dt_str: Optional[str], origin_tz: pytz.BaseTzInfo, target_tz: pytz.BaseTzInfo, fmt: str = "%Y-%m-%d %H:%M:%S"
) -> Optional[datetime.datetime]:
    """
    将时间字符串转换为指定时区的datetime对象
    :param dt_str: 时间字符串
    :param origin_tz: 给定时间对应的时区
    :param target_tz: 目标时区
    :param fmt: 给定时间字符串的格式
    :return: 转换为目标时区的datetime对象
    参考：https://stackoverflow.com/questions/79797/how-to-convert-local-time-string-to-utc
    """
    # 将给定时间字符串转为datetime对象并注入时区信息
    if not dt_str:
        return None

    dt_without_tz = datetime.datetime.strptime(dt_str, fmt)
    dt_with_tz: datetime.datetime = origin_tz.localize(dt_without_tz, is_dst=None)

    # 转换为目标时区
    target_dt = dt_with_tz.astimezone(target_tz)

    return target_dt


# 本地时间字符串转utc时间
local_dt_str2utc_dt = partial(dt_str2dt_as_timezone, origin_tz=timezone.get_current_timezone(), target_tz=pytz.utc)

utc_dt_str2utc_dt = partial(dt_str2dt_as_timezone, origin_tz=pytz.utc, target_tz=pytz.utc)
