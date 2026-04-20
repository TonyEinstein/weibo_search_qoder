# -*- coding: utf-8 -*-
"""
微博搜索爬虫 - 项目入口
IDE一键运行入口，支持直接调用或作为模块导入
"""

import sys
import os
import logging
from datetime import datetime

# 添加当前目录到路径（确保可以导入本地模块）
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from config import Config
from weibo_crawler import WeiboCrawler
from spider import WeiboSpider

# 初始化日志配置
log_dir = os.path.join(current_dir, 'log')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, datetime.now().strftime('%Y-%m-%d') + '.log')

# 配置根日志记录器
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8', mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('WeiboMain')


def run_crawler(config=None):
    """
    运行爬虫的主函数
    
    :param config: 配置对象，如果为None则使用默认配置
    :return: 抓取的微博数量
    
    示例用法:
        # 使用默认配置运行
        run_crawler()
        
        # 使用自定义配置运行
        custom_config = Config()
        custom_config.KEYWORD_LIST = ['周杰伦']
        custom_config.START_DATE = '2026-01-01'
        custom_config.END_DATE = '2026-01-31'
        run_crawler(custom_config)
    """
    # 使用传入的配置或默认配置
    crawler_config = config or Config()
    
    # 创建爬虫实例并运行
    crawler = WeiboCrawler(crawler_config)
    count = crawler.crawl()
    
    return count


def run_crawler_with_params(
    keyword_list=None,
    cookie=None,
    start_date=None,
    end_date=None,
    weibo_type=None,
    contain_type=None,
    region=None,
    further_threshold=None,
    limit_result=None,
    download_delay=None
):
    """
    使用参数运行爬虫的便捷函数
    
    所有参数均为可选，不传则使用默认配置
    
    :param keyword_list: 关键词列表，如 ['迪丽热巴', '周杰伦']
    :param cookie: Cookie字符串
    :param start_date: 开始日期，格式 '2026-01-01'
    :param end_date: 结束日期，格式 '2026-01-31'
    :param weibo_type: 微博类型 (0-6)，支持单个类型或列表如 [1, 5]
    :param contain_type: 包含类型 (0-4)
    :param region: 地区列表，如 ['北京', '上海']
    :param further_threshold: 细分阈值 (默认46)
    :param limit_result: 结果数量限制 (0表示不限制)
    :param download_delay: 下载延迟秒数 (默认10)
    :return: 抓取的微博数量
    
    示例用法:
        run_crawler_with_params(
            keyword_list=['周杰伦'],
            start_date='2026-01-01',
            end_date='2026-01-31',
            limit_result=100
        )
    """
    config = Config()
    
    if keyword_list is not None:
        config.KEYWORD_LIST = keyword_list
    if cookie is not None:
        config.COOKIE = cookie
    if start_date is not None:
        config.START_DATE = start_date
    if end_date is not None:
        config.END_DATE = end_date
    if weibo_type is not None:
        # 支持列表或单个值
        if isinstance(weibo_type, (list, tuple)):
            config.WEIBO_TYPE = list(weibo_type)
        else:
            config.WEIBO_TYPE = [weibo_type]
    if contain_type is not None:
        config.CONTAIN_TYPE = contain_type
    if region is not None:
        config.REGION = region
    if further_threshold is not None:
        config.FURTHER_THRESHOLD = further_threshold
    if limit_result is not None:
        config.LIMIT_RESULT = limit_result
    if download_delay is not None:
        config.DOWNLOAD_DELAY = download_delay
    
    return run_crawler(config)


# ==================== 主程序入口 ====================

if __name__ == '__main__':
    """
    IDE直接运行入口
    点击运行按钮即可启动爬虫
    """
    logger.info('=' * 60)
    logger.info('微博搜索爬虫 - 简化版 (基于requests)')
    logger.info('=' * 60)
    logger.info('')
    logger.info('启动方式:')
    logger.info('  1. 直接运行: 点击IDE运行按钮')
    logger.info('  2. 命令行: python main.py')
    logger.info('  3. 导入使用:')
    logger.info('     from main import run_crawler, run_crawler_with_params')
    logger.info('     from spider import WeiboSpider')
    logger.info('')
    logger.info('提示: 请在 config.py 中配置COOKIE后再运行！')
    logger.info('=' * 60)
    logger.info('')
    
    # 检查Cookie是否已配置
    if not Config.COOKIE or not Config.COOKIE.strip() or Config.COOKIE == '请从浏览器复制Cookie':
        logger.error('Cookie未配置！')
        logger.error('请先在 config.py 中设置有效的Cookie值')
        logger.info('')
        logger.info('获取Cookie方法:')
        logger.info('1. 使用浏览器登录微博')
        logger.info('2. 打开开发者工具(F12) -> Network')
        logger.info('3. 刷新页面，找到任意请求')
        logger.info('4. 复制Request Headers中的Cookie值')
        sys.exit(1)
    
    # 运行爬虫
    try:
        count = run_crawler()
        logger.info('')
        logger.info(f'爬虫执行完毕！共抓取 {count} 条微博')
        logger.info('')
    except KeyboardInterrupt:
        logger.info('')
        logger.info('用户中断爬虫')
        sys.exit(0)
    except Exception as e:
        logger.info('')
        logger.error(f'爬虫执行出错: {e}')
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
