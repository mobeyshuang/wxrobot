#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import logging
import time
from datetime import datetime

import requests
from lxml import etree


class News(object):
    def __init__(self) -> None:
        self.LOG = logging.getLogger(__name__)
        self.week = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0"}

    def get_important_news(self):
        url = "https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=7.7.5"
        data = {"type": "telegram", "keyword": "你需要知道的隔夜全球要闻", "page": 0,
                "rn": 1, "os": "web", "sv": "7.7.5", "app": "CailianpressWeb"}
        try:
            rsp = requests.post(url=url, headers=self.headers, data=data)
            data = json.loads(rsp.text)["data"]["telegram"]["data"][0]
            news = data["descr"]
            timestamp = data["time"]
            ts = time.localtime(timestamp)
            weekday_news = datetime(*ts[:6]).weekday()
        except Exception as e:
            self.LOG.error(e)
            return ""

        weekday_now = datetime.now().weekday()
        if weekday_news != weekday_now:
            return ""  # 旧闻，观察发现周二～周六早晨6点半左右发布

        fmt_time = time.strftime("%Y年%m月%d日", ts)

        news = re.sub(r"(\d{1,2}、)", r"\n\1", news)
        fmt_news = "".join(etree.HTML(news).xpath(" // text()"))
        fmt_news = re.sub(r"周[一|二|三|四|五|六|日]你需要知道的", r"", fmt_news)

        return f"{fmt_time} {self.week[weekday_news]}\n{fmt_news}"
        
    def get_tech_news(self, count=15):
        """
        获取科技新闻
        
        通过财联社API获取最新的科技类新闻
        
        Args:
            count: 获取的新闻数量，默认为5条
            
        Returns:
            str: 格式化的科技新闻
        """
        url = "https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=7.7.5"
        # 可用关键词：科技、互联网、人工智能、芯片、半导体、5G
        keywords = ["科技", "芯片", "人工智能", "5G","小米", "华为", "汽车", "半导体", "互联网"] 
        all_news = []
        
        for keyword in keywords:
            data = {"type": "telegram", "keyword": keyword, "page": 0,
                    "rn": count, "os": "web", "sv": "7.7.5", "app": "CailianpressWeb"}
            try:
                rsp = requests.post(url=url, headers=self.headers, data=data)
                news_list = json.loads(rsp.text)["data"]["telegram"]["data"]
                
                # 添加到总新闻列表
                for news_item in news_list:
                    # 添加来源标记
                    news_item["keyword_source"] = keyword
                    all_news.append(news_item)
                    
            except Exception as e:
                self.LOG.error(f"获取科技新闻({keyword})出错: {e}")
        
        if not all_news:
            return "暂无科技新闻"
        
        # 根据时间排序，获取最新的
        all_news.sort(key=lambda x: int(x.get("time", 0)), reverse=True)
        # 去重（可能不同关键词返回相同新闻）
        unique_news = []
        seen_ids = set()
        for news in all_news:
            if news.get("id") not in seen_ids:
                unique_news.append(news)
                seen_ids.add(news.get("id"))
        
        # 只保留指定数量
        unique_news = unique_news[:count]
        
        # 获取当前日期
        today = datetime.now()
        fmt_date = today.strftime("%Y年%m月%d日")
        weekday = today.weekday()
        
        # 格式化输出
        result = f"{fmt_date} {self.week[weekday]} 科技新闻\n"
        
        # 处理新闻
        for i, news_item in enumerate(unique_news, 1):
            title = news_item.get("title", "")
            content = news_item.get("descr", "")
            source = news_item.get("keyword_source", "")
            
            # 提取纯文本内容
            if content:
                content = "".join(etree.HTML(content).xpath(" // text()"))
            
            # 格式化新闻条目
            result += f"{i}、{title}"
            if content:
                # 限制内容长度
                if len(content) > 200:
                    content = content[:200] + "..."
                result += f" {content}"
            result += f" [来源：{source}]\n"
        
        return result.strip()
    
    def get_domestic_news(self, count=15):
        """
        获取国内时政新闻
        
        通过财联社API获取最新的国内时政相关新闻
        
        Args:
            count: 获取的新闻数量，默认为5条
            
        Returns:
            str: 格式化的国内时政新闻
        """
        url = "https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=7.7.5"
        # 可用关键词：中国时政、国内要闻、中共中央、国务院、两会等
        keywords = ["中国", "时政", "国内要闻", "中共中央", "国务院", "央行", "财政部", "发改委", "国资委", "人社部", "产业政策"] 
        all_news = []
        
        for keyword in keywords:
            data = {"type": "telegram", "keyword": keyword, "page": 0,
                    "rn": count, "os": "web", "sv": "7.7.5", "app": "CailianpressWeb"}
            try:
                rsp = requests.post(url=url, headers=self.headers, data=data)
                news_list = json.loads(rsp.text)["data"]["telegram"]["data"]
                
                # 添加到总新闻列表
                for news_item in news_list:
                    # 添加来源标记
                    news_item["keyword_source"] = keyword
                    all_news.append(news_item)
                    
            except Exception as e:
                self.LOG.error(f"获取国内新闻({keyword})出错: {e}")
        
        if not all_news:
            return "暂无国内时政新闻"
        
        # 根据时间排序，获取最新的
        all_news.sort(key=lambda x: int(x.get("time", 0)), reverse=True)
        # 去重（可能不同关键词返回相同新闻）
        unique_news = []
        seen_ids = set()
        for news in all_news:
            if news.get("id") not in seen_ids:
                unique_news.append(news)
                seen_ids.add(news.get("id"))
        
        # 只保留指定数量
        unique_news = unique_news[:count]
        
        # 获取当前日期
        today = datetime.now()
        fmt_date = today.strftime("%Y年%m月%d日")
        weekday = today.weekday()
        
        # 格式化输出
        result = f"{fmt_date} {self.week[weekday]} 国内时政新闻\n"
        
        # 处理新闻
        for i, news_item in enumerate(unique_news, 1):
            title = news_item.get("title", "")
            content = news_item.get("descr", "")
            source = news_item.get("keyword_source", "")
            
            # 提取纯文本内容
            if content:
                content = "".join(etree.HTML(content).xpath(" // text()"))
            
            # 格式化新闻条目
            result += f"{i}、{title}"
            if content:
                # 限制内容长度
                if len(content) > 200:
                    content = content[:200] + "..."
                result += f" {content}"
            result += f" [来源：{source}]\n"
        
        return result.strip()


if __name__ == "__main__":
    news = News()
    print(news.get_important_news())
    print("\n" + "-"*50 + "\n")
    print(news.get_tech_news())
    print("\n" + "-"*50 + "\n")
    print(news.get_domestic_news())
