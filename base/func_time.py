#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from zhdate import ZhDate

def get_time() -> str:
    '''
    获取当前日期，时间，农历日期，星期几
    '''
    time = datetime.now()
    date2 = ZhDate.from_datetime(time)
    week_list = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

    return '{} {} {}'.format(time.strftime("%Y年%m月%d日 %H:%M:%S"), week_list[time.weekday()], '农历:' + date2.chinese()) 