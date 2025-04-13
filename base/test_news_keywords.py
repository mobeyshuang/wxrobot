#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import requests
import time
from concurrent.futures import ThreadPoolExecutor

def test_keyword(keyword):
    """测试特定关键词是否返回结果"""
    url = "https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=7.7.5"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0"
    }
    data = {
        "type": "telegram", 
        "keyword": keyword, 
        "page": 0,
        "rn": 3,  # 只获取前3条减少请求大小 
        "os": "web", 
        "sv": "7.7.5", 
        "app": "CailianpressWeb"
    }
    
    try:
        rsp = requests.post(url=url, headers=headers, data=data)
        result = json.loads(rsp.text)
        news_list = result.get("data", {}).get("telegram", {}).get("data", [])
        count = len(news_list)
        
        if count > 0:
            first_item = news_list[0]
            title = first_item.get("title", "")
            if not title:
                title = first_item.get("content", "")[:30] if first_item.get("content") else ""
            
            # 获取创建时间
            create_time = first_item.get("ctime", "") or first_item.get("time", "")
            if create_time:
                try:
                    create_time = time.strftime("%Y-%m-%d", time.localtime(int(create_time)))
                except:
                    create_time = ""
                    
            return {
                "keyword": keyword,
                "count": count,
                "success": True,
                "sample": title,
                "date": create_time
            }
        else:
            return {
                "keyword": keyword,
                "count": 0,
                "success": False
            }
    except Exception as e:
        return {
            "keyword": keyword,
            "count": 0,
            "success": False,
            "error": str(e)
        }

def get_categories():
    """尝试从首页获取分类列表"""
    url = "https://www.cls.cn/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0"
    }
    
    try:
        rsp = requests.get(url, headers=headers)
        # 简单解析一下页面，寻找分类名称
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(rsp.text, "html.parser")
        
        # 尝试找导航栏目
        navs = soup.select("nav a")
        categories = [nav.text.strip() for nav in navs if nav.text.strip()]
        return categories
    except Exception as e:
        print(f"获取分类失败: {e}")
        return []

# 常见财经和新闻分类关键词列表
keywords_to_test = [
    # 财经分类
    "宏观", "股市", "债市", "外汇", "期货", "黄金", "原油", 
    "基金", "私募", "房地产", "银行", "保险", "证券",
    # 板块分类
    "科技", "医药", "消费", "新能源", "汽车", "制造业", "互联网",
    "区块链", "人工智能", "半导体", "5G", "元宇宙", "芯片",
    "新材料", "新能源汽车", "电动汽车", "储能", "光伏", "风电",
    # a股相关
    "A股", "港股", "美股", "沪指", "深指", "创指", "上证指数", 
    "深证成指", "创业板指", "中小板", "科创板", "北交所",
    # 市场动态
    "开盘", "收盘", "大宗交易", "龙虎榜", "融资融券", "北向资金",
    "新股", "IPO", "并购重组", "业绩预告", "业绩快报", 
    # 政策监管
    "央行", "证监会", "银保监会", "财政部", "发改委", "国务院",
    "政策解读", "货币政策", "财政政策", "监管动态", "利率",
    "降准", "降息", "上调", "下调", "税收", "减税",
    # 时政类
    "时政", "时政新闻", "中央政治局", "中共中央", "国常会", 
    "中央经济工作会议", "两会", "全国人大", "全国政协",
    "一带一路", "粤港澳大湾区", "长三角一体化", "京津冀协同发展",
    # 热点新闻分类
    "要闻", "独家", "财经要闻", "国内要闻", "国际要闻", "中国时政",
    "国际政治", "产业动态", "公司新闻", "投资机会", "热点追踪",
    "国内经济", "今日焦点",
    # 特定栏目
    "早报", "收评", "盘前", "盘后", "晚间公告", "研报精选",
    "你需要知道的隔夜全球要闻", "财联社今日热点", "每日复盘",
    "热点前瞻", "财联社早报", "今日要闻", "今日导读",
    # 新闻源
    "央视新闻", "人民日报", "新华社", "中国证券报", "上证报",
    "证券时报", "21世纪经济报道", "财新", "界面", "第一财经",
    "经济日报", "金融时报", "环球时报", "华尔街日报",
    # 地域分类
    "中国", "美国", "欧洲", "日本", "亚太", "新兴市场",
    "北京", "上海", "深圳", "广州", "香港", "台湾",
    # 产业政策
    "产业政策", "工业政策", "科技政策", "农业政策", "能源政策",
    "环保政策", "医疗政策", "教育政策", "住房政策",
]

def main():
    print("测试财联社API关键词搜索结果...")
    print("-" * 60)
    
    # 尝试获取网站分类
    web_categories = get_categories()
    if web_categories:
        print(f"从网站获取到的分类: {', '.join(web_categories)}")
        keywords_to_test.extend(web_categories)
    
    # 合并并去重
    unique_keywords = list(set(keywords_to_test))
    print(f"准备测试 {len(unique_keywords)} 个关键词...")
    
    # 使用线程池加速测试
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:  # 5个并发请求
        for i, result in enumerate(executor.map(test_keyword, unique_keywords)):
            results.append(result)
            # 打印进度
            print(f"\r测试进度: {i+1}/{len(unique_keywords)}", end="")
            time.sleep(0.2)  # 限制请求速率
    
    print("\n\n测试结果:")
    print("-" * 60)
    
    # 过滤出成功的关键词并排序
    successful_keywords = [r for r in results if r.get("success", False)]
    successful_keywords.sort(key=lambda x: x.get("count", 0), reverse=True)
    
    print(f"有效关键词数量: {len(successful_keywords)}/{len(unique_keywords)}")
    print("-" * 70)
    print("{:<20} {:<8} {:<10} {:<30}".format("关键词", "新闻数", "最新日期", "示例标题"))
    print("-" * 70)
    
    # 按类别分组输出
    category_groups = {
        "时政新闻": ["时政", "两会", "国常会", "中国时政", "国内要闻", "中央政治局", "央视新闻", "人民日报", "新华社"],
        "财经要闻": ["财经要闻", "要闻", "宏观", "早报", "热点", "隔夜全球要闻"],
        "股市相关": ["A股", "港股", "美股", "沪指", "创业板", "科创板", "北交所"],
        "行业板块": ["科技", "医药", "消费", "新能源", "汽车", "半导体", "芯片", "互联网"],
        "政策监管": ["央行", "证监会", "银保监会", "财政部", "发改委", "国务院", "政策解读", "产业政策"]
    }
    
    # 创建分类映射
    keyword_category = {}
    for category, keywords in category_groups.items():
        for kw in keywords:
            keyword_category[kw] = category
    
    # 记录已分类关键词
    categorized = set()
    
    # 按分类输出结果
    for category, keywords in category_groups.items():
        print(f"\n{category}类关键词:")
        print("-" * 70)
        
        category_results = []
        for result in successful_keywords:
            keyword = result.get("keyword", "")
            if keyword in keywords:
                categorized.add(keyword)
                category_results.append(result)
        
        # 输出该分类下的关键词
        for result in category_results:
            keyword = result.get("keyword", "")
            count = result.get("count", 0)
            date = result.get("date", "")
            sample = result.get("sample", "")[:30]
            print("{:<20} {:<8} {:<10} {:<30}".format(keyword, count, date, sample))
    
    # 输出其他未分类的有效关键词
    others = [r for r in successful_keywords if r.get("keyword") not in categorized]
    if others:
        print("\n其他有效关键词:")
        print("-" * 70)
        for result in others:
            keyword = result.get("keyword", "")
            count = result.get("count", 0)
            date = result.get("date", "")
            sample = result.get("sample", "")[:30]
            print("{:<20} {:<8} {:<10} {:<30}".format(keyword, count, date, sample))
    
    # 保存结果到文件
    print("\n保存结果到文件: news_keywords_result.txt")
    with open("news_keywords_result.txt", "w", encoding="utf-8") as f:
        f.write("财联社API有效关键词列表:\n")
        f.write("-" * 70 + "\n")
        
        # 按类别分组写入
        for category, keywords in category_groups.items():
            valid_keywords = [k for k in keywords if k in [r.get("keyword") for r in successful_keywords]]
            if valid_keywords:
                f.write(f"\n{category}类关键词: {', '.join(valid_keywords)}\n")
        
        # 写入其他未分类关键词
        other_keywords = [r.get("keyword") for r in others]
        if other_keywords:
            f.write(f"\n其他有效关键词: {', '.join(other_keywords)}\n")
    
    print("测试完成！")

if __name__ == "__main__":
    main() 