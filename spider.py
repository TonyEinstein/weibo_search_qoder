# -*- coding: utf-8 -*-
"""
微博爬虫类 - 面向对象接口
便于集成到其他项目中
"""

from config import Config
from weibo_crawler import WeiboCrawler


class WeiboSpider:
    """
    微博爬虫类（面向对象接口）
    便于集成到其他项目中
    
    示例用法:
        # 方式1：普通使用
        spider = WeiboSpider()
        spider.set_keywords(['迪丽热巴'])
        spider.set_date_range('2026-01-01', '2026-01-31')
        spider.set_limit(100)
        count = spider.run()
        
        # 方式2：链式调用
        count = WeiboSpider()\
            .set_keywords(['周杰伦'])\
            .set_date_range('2026-01-01', '2026-01-31')\
            .set_limit(100)\
            .run()
        
        # 方式3：上下文管理器（推荐）
        with WeiboSpider() as spider:
            spider.set_keywords(['林俊杰'])
            count = spider.run()
    """
    
    def __init__(self):
        self.config = Config()
        self.crawler = None
    
    def set_keywords(self, keyword_list):
        """设置关键词列表"""
        self.config.KEYWORD_LIST = keyword_list
        return self
    
    def set_cookie(self, cookie):
        """设置Cookie"""
        self.config.COOKIE = cookie
        return self
    
    def set_date_range(self, start_date, end_date):
        """设置日期范围"""
        self.config.START_DATE = start_date
        self.config.END_DATE = end_date
        return self
    
    def set_weibo_type(self, weibo_type):
        """
        设置微博类型
        支持单个类型: 5 或多个类型: [1, 5]
        0: 全部微博
        1: 原创微博
        2: 热门微博
        3: 关注人微博
        4: 认证用户微博
        5: 媒体微博
        6: 观点微博
        """
        # 支持列表或单个值
        if isinstance(weibo_type, (list, tuple)):
            self.config.WEIBO_TYPE = list(weibo_type)
        else:
            self.config.WEIBO_TYPE = [weibo_type]
        return self
    
    def set_contain_type(self, contain_type):
        """
        设置包含类型
        0: 不筛选
        1: 包含图片
        2: 包含视频
        3: 包含音乐
        4: 包含短链接
        """
        self.config.CONTAIN_TYPE = contain_type
        return self
    
    def set_region(self, region_list):
        """设置地区列表，如 ['北京', '上海']"""
        self.config.REGION = region_list
        return self
    
    def set_threshold(self, threshold):
        """设置细分阈值"""
        self.config.FURTHER_THRESHOLD = threshold
        return self
    
    def set_limit(self, limit):
        """设置结果数量限制（0表示不限制）"""
        self.config.LIMIT_RESULT = limit
        return self
    
    def set_delay(self, delay):
        """设置下载延迟（秒）"""
        self.config.DOWNLOAD_DELAY = delay
        return self
    
    def set_multithread(self, enable, max_workers=3):
        """
        设置多线程模式
        :param enable: 是否启用多线程
        :param max_workers: 最大并发线程数
        """
        self.config.ENABLE_MULTITHREAD = enable
        self.config.MAX_WORKERS = max_workers
        return self
    
    def set_anti_detect(self, enable, random_delay_min=2, random_delay_max=8):
        """
        设置反爬优化
        :param enable: 是否启用反爬优化
        :param random_delay_min: 最小随机延迟
        :param random_delay_max: 最大随机延迟
        """
        self.config.ENABLE_ANTI_DETECT = enable
        self.config.RANDOM_DELAY_MIN = random_delay_min
        self.config.RANDOM_DELAY_MAX = random_delay_max
        return self
    
    def set_output_dir(self, output_dir):
        """设置输出目录"""
        self.config.OUTPUT_DIR = output_dir
        return self
    
    def set_log_level(self, level):
        """
        设置日志级别
        level: 'DEBUG', 'INFO', 'WARNING', 'ERROR'
        """
        self.config.LOG_LEVEL = level
        return self
    
    def run(self):
        """运行爬虫"""
        self.crawler = WeiboCrawler(self.config)
        return self.crawler.crawl()
    
    def get_stats(self):
        """获取统计信息"""
        if self.crawler:
            return {
                'result_count': self.crawler.result_count,
                'seen_ids': len(self.crawler.seen_ids)
            }
        return None
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口，确保资源释放"""
        try:
            if self.crawler:
                self.crawler._close_csv_files()
        except Exception:
            pass  # 忽略资源释放时的异常
        return False
