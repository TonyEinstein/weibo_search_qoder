# -*- coding: utf-8 -*-
"""
微博爬虫配置文件
包含所有可配置参数
"""


from datetime import datetime


class Config:
    """爬虫配置类"""
    
    # ==================== 搜索参数配置 ====================
    
    # 要搜索的关键词列表，可写多个
    # 值可以是由关键词或话题组成的列表，也可以是包含关键词的txt文件路径
    # 如 'keyword_list.txt'，txt文件中每个关键词占一行
    KEYWORD_LIST = ['徐良']  # 或者 KEYWORD_LIST = 'keyword_list.txt'
    
    # Cookie配置（必须配置，否则无法获取数据）
    # 从浏览器开发者工具中复制Cookie值
    # 获取方法：
    # 1. 使用浏览器登录微博
    # 2. 按F12打开开发者工具 -> Network
    # 3. 刷新页面，找到任意请求
    # 4. 复制Request Headers中的Cookie值
    COOKIE = ''
    # Cookie池配置（用于多账号轮换，提高抗封能力）
    # 格式: [{'name': '账号1', 'cookie': 'xxx'}, {'name': '账号2', 'cookie': 'yyy'}]
    # 如果为空列表，则使用上面的单一COOKIE
    COOKIE_POOL = []
    
    # 要搜索的微博类型
    # 0代表搜索全部微博，1代表搜索全部原创微博，2代表热门微博，3代表关注人微博，4代表认证用户微博，5代表媒体微博，6代表观点微博
    # 支持单个类型: WEIBO_TYPE = 5 或 多个类型: WEIBO_TYPE = [1, 5]（会依次抓取每种类型的微博）
    WEIBO_TYPE = [2,5]
    
    # 筛选结果微博中必需包含的内容
    # 0代表不筛选，获取全部微博，1代表搜索包含图片的微博，2代表包含视频的微博，3代表包含音乐的微博，4代表包含短链接的微博
    CONTAIN_TYPE = 0
    
    # 筛选微博的发布地区，精确到省或直辖市
    # 值不应包含"省"或"市"等字，如想筛选北京市的微博请用"北京"而不是"北京市"
    # 可以写多个地区，不筛选请用"全部"
    REGION = ['全部']
    
    # 搜索的起始日期，为yyyy-mm-dd形式，搜索结果包含该日期
    START_DATE = '2026-03-15'
    
    # 搜索的终止日期，为yyyy-mm-dd形式，搜索结果包含该日期
    END_DATE = '2026-04-15'
    
    # 进一步细分搜索的阈值，若结果页数大于等于该值，则认为结果没有完全展示
    # 细分搜索条件重新搜索以获取更多微博。数值越大速度越快，也越有可能漏掉微博
    # 数值越小速度越慢，获取的微博就越多。建议数值大小设置在40到50之间
    FURTHER_THRESHOLD = 46
    
    # 爬取结果的数量限制，爬取到该数量的微博后自动停止，设置为0代表不限制
    LIMIT_RESULT = 600
    
    # ==================== 多线程配置 ====================
    
    # 是否启用多线程抓取
    ENABLE_MULTITHREAD = True
    
    # 最大并发线程数（建议2-5，过高容易触发反爬）
    MAX_WORKERS = 2
    
    # ==================== 反爬优化配置 ====================
    
    # 是否启用反爬优化
    ENABLE_ANTI_DETECT = True
    
    # 是否启用请求头伪装（添加Referer等）
    ENABLE_HEADER_SPOOFING = True
    
    # 代理配置
    # 是否启用代理
    ENABLE_PROXY = False
    
    # 代理池列表，格式: ['http://ip:port', 'http://user:pass@ip:port']
    PROXY_LIST = []
    
    # 代理轮换策略: 'random'随机选择, 'round_robin'轮询
    PROXY_STRATEGY = 'random'
    
    # 是否验证代理可用性
    VERIFY_PROXY = False
    
    # ==================== 请求配置 ====================
    
    # 访问完一个页面再访问下一个时需要等待的时间（秒）
    # 格式: [最小值, 最大值]，每次请求会在范围内随机选择，模拟人工操作
    # 建议值：单线程 [2, 5]，多线程 [3, 8] 或更高
    DOWNLOAD_DELAY = [3, 8]
    
    # 请求超时时间（秒）
    # 格式: [最小值, 最大值]，每次请求会在范围内随机选择
    REQUEST_TIMEOUT = [30, 60]
    
    # 请求重试次数
    # 格式: [最小值, 最大值]，每次请求会在范围内随机选择
    RETRY_TIMES = [2, 4]
    
    # User-Agent 配置
    # 设置为 True 则每次请求使用随机 User-Agent，False 则使用下方固定的 USER_AGENT
    USE_RANDOM_USER_AGENT = True
    
    # 固定 User-Agent（当 USE_RANDOM_USER_AGENT = False 时使用）
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    # ==================== 输出配置 ====================
    
    # 结果文件存储路径
    OUTPUT_DIR = '结果'
    
    # ==================== 日志配置 ====================
    
    # 日志级别: DEBUG, INFO, WARNING, ERROR
    LOG_LEVEL = 'INFO'
    
    # 是否输出到文件
    LOG_TO_FILE = True
