# -*- coding: utf-8 -*-
"""
微博搜索爬虫核心类
基于requests实现，替代原Scrapy框架
支持多线程和反爬优化
"""

import os
import sys
import re
import csv
import time
import logging
import random
import threading
from datetime import datetime, timedelta
from urllib.parse import quote, unquote
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from lxml import html

from config import Config
from weibo_item import WeiboItem
from user_agents import get_random_user_agent
from utils import (
    convert_weibo_type, convert_contain_type, get_keyword_list,
    process_keywords, get_regions, standardize_date, validate_dates,
    get_article_url, get_location, get_at_users, get_topics,
    get_vip_info, extract_number, get_user_auth
)
from anti_detect import AntiDetectManager, AdaptiveDelay


class WeiboCrawler:
    """
    微博搜索爬虫类
    支持按关键词、时间范围、地区等条件搜索微博
    支持多线程和反爬优化
    """
    
    def __init__(self, config=None, thread_safe=False):
        """
        初始化爬虫
        :param config: 配置对象，默认使用Config类
        :param thread_safe: 是否启用线程安全模式（多线程时使用）
        """
        self.config = config or Config()
        self.session = requests.Session()
        self.base_url = 'https://s.weibo.com'
        
        # 初始化统计数据
        self.result_count = 0
        self.seen_ids = set()  # 用于去重
        
        # 线程安全相关
        self.thread_safe = thread_safe
        self._lock = threading.Lock() if thread_safe else None
        self._seen_ids_lock = threading.Lock()  # 专门用于 seen_ids 的锁
        
        # 初始化反爬管理器
        self.anti_detect = AntiDetectManager(self.config)
        
        # 自适应延迟控制器
        self.adaptive_delay = None
        if hasattr(self.config, 'ENABLE_ANTI_DETECT') and self.config.ENABLE_ANTI_DETECT:
            # 从 DOWNLOAD_DELAY 获取延迟范围
            delay_config = getattr(self.config, 'DOWNLOAD_DELAY', [2, 8])
            if isinstance(delay_config, (list, tuple)) and len(delay_config) == 2:
                min_delay, max_delay = delay_config[0], delay_config[1]
            else:
                min_delay, max_delay = delay_config * 0.8, delay_config * 1.2
            self.adaptive_delay = AdaptiveDelay(
                min_delay=min_delay,
                max_delay=max_delay
            )
        
        # 初始化配置
        self._init_config()
        
        # 初始化日志
        self._init_logger()
        
        # 初始化请求头
        self._init_headers()
        
        # 初始化CSV文件句柄缓存
        self._csv_files = {}  # keyword -> file_handle
        self._csv_writers = {}  # keyword -> csv_writer
        self._csv_first_write = {}  # keyword -> bool
        
        # IP属地缓存，避免重复请求
        self._ip_cache = {}  # bid -> ip
    
    def _init_config(self):
        """初始化配置参数"""
        # 获取关键词列表
        raw_keywords = get_keyword_list(self.config.KEYWORD_LIST)
        # 处理话题格式并编码URL
        processed_keywords = process_keywords(raw_keywords)
        # 保存原始关键词用于日志显示（解码URL编码）
        self.keyword_list_original = [unquote(kw) for kw in processed_keywords]
        # 对关键词进行URL编码（处理特殊字符）用于URL构造
        self.keyword_list = [quote(kw) if not kw.startswith('%23') else kw for kw in processed_keywords]
        # 创建编码关键词到原始关键词的映射，用于日志显示
        self._keyword_map = dict(zip(self.keyword_list, self.keyword_list_original))
        
        # 转换微博类型（现在返回列表）和包含类型
        self.weibo_type_list = convert_weibo_type(self.config.WEIBO_TYPE)
        # 设置默认 weibo_type（取第一个），防止多线程模式下某些方法访问时未设置
        if not self.weibo_type_list:
            self.weibo_type_list = ['&typeall=1']
            self.logger.warning('WEIBO_TYPE配置无效，使用默认类型：全部微博')
        self.weibo_type = self.weibo_type_list[0]
        self.contain_type = convert_contain_type(self.config.CONTAIN_TYPE)
        
        # 获取地区配置
        self.regions = get_regions(self.config.REGION)
        
        # 验证日期
        validate_dates(self.config.START_DATE, self.config.END_DATE)
        self.start_date = self.config.START_DATE
        self.end_date = self.config.END_DATE
        
        # 其他配置
        self.further_threshold = self.config.FURTHER_THRESHOLD
        self.limit_result = self.config.LIMIT_RESULT
        # DOWNLOAD_DELAY 支持范围配置 [min, max]，每次获取随机值
        delay_config = self.config.DOWNLOAD_DELAY
        if isinstance(delay_config, (list, tuple)) and len(delay_config) == 2:
            self.download_delay_range = (delay_config[0], delay_config[1])
            self.download_delay = delay_config[0]  # 默认值
        else:
            self.download_delay_range = (delay_config, delay_config)
            self.download_delay = delay_config
    
    def _init_logger(self):
        """初始化日志记录器（防止重复配置）"""
        self.logger = logging.getLogger('WeiboCrawler')
        
        # 如果已经配置过，直接返回
        if self.logger.handlers:
            self.logger.setLevel(getattr(logging, self.config.LOG_LEVEL.upper()))
            return
        
        self.logger.setLevel(getattr(logging, self.config.LOG_LEVEL.upper()))
        
        # 注意：日志处理器由main.py统一配置，这里不再重复添加
        # 避免重复输出到weibo_crawler.log文件
    
    def _get_user_agent(self):
        """获取 User-Agent"""
        if self.config.USE_RANDOM_USER_AGENT:
            return get_random_user_agent()
        return self.config.USER_AGENT
    
    def _get_original_keyword(self, encoded_keyword):
        """
        获取编码关键词对应的原始关键词（用于日志显示）
        :param encoded_keyword: URL编码后的关键词
        :return: 原始中文关键词
        """
        return self._keyword_map.get(encoded_keyword, encoded_keyword)
    
    def _init_headers(self):
        """初始化请求头"""
        # 初始化时只设置Cookie，其他请求头由每次请求时动态构建
        self.session.headers.update({
            'Cookie': self.config.COOKIE,
            'User-Agent': self._get_user_agent()
        })
    
    def _update_user_agent(self):
        """更新请求头中的 User-Agent（用于每次请求时更换）"""
        if self.config.USE_RANDOM_USER_AGENT:
            self.session.headers.update({'User-Agent': get_random_user_agent()})
    
    def _get_random_timeout(self):
        """获取随机超时时间（支持范围配置）"""
        timeout_config = self.config.REQUEST_TIMEOUT
        if isinstance(timeout_config, (list, tuple)) and len(timeout_config) == 2:
            return random.uniform(timeout_config[0], timeout_config[1])
        return timeout_config
    
    def _get_random_retries(self):
        """获取随机重试次数（支持范围配置）"""
        retries_config = self.config.RETRY_TIMES
        if isinstance(retries_config, (list, tuple)) and len(retries_config) == 2:
            return random.randint(retries_config[0], retries_config[1])
        return retries_config
    
    def _make_request(self, url, retries=None, referer=None):
        """
        发送HTTP请求（支持反爬优化）
        :param url: 请求URL
        :param retries: 重试次数
        :param referer: 来源页面URL
        :return: HTML文档对象或None
        """
        if retries is None:
            retries = self._get_random_retries()
        
        for attempt in range(retries + 1):
            try:
                # 每次请求前更新请求头（如果启用反爬优化）
                if hasattr(self.config, 'ENABLE_ANTI_DETECT') and self.config.ENABLE_ANTI_DETECT:
                    headers, proxies = self.anti_detect.get_session_config(referer, url)
                    # 保留原始Cookie，避免被覆盖
                    original_cookie = self.session.headers.get('Cookie', '')
                    # 清空session headers并重新设置
                    self.session.headers.clear()
                    self.session.headers.update(headers)
                    # 确保Cookie正确设置
                    if original_cookie:
                        self.session.headers['Cookie'] = original_cookie
                else:
                    # 传统方式更新User-Agent
                    self._update_user_agent()
                    proxies = {'http': None, 'https': None}
                
                self.logger.debug(f'请求URL: {url}')
                self.logger.debug(f'使用User-Agent: {self.session.headers.get("User-Agent", "")[:50]}...')
                
                response = self.session.get(
                    url, 
                    timeout=self._get_random_timeout(),
                    proxies=proxies
                )
                
                # 检查是否触发反爬
                if hasattr(self.config, 'ENABLE_ANTI_DETECT') and self.config.ENABLE_ANTI_DETECT:
                    is_blocked, message, is_cookie_invalid = self.anti_detect.check_response(response)
                    if is_blocked:
                        # 如果是Cookie失效，给出明确提示并退出
                        if is_cookie_invalid:
                            self._handle_cookie_invalid()
                            return None
                        
                        self.logger.warning(f'触发反爬检测: {message}')
                        if self.adaptive_delay:
                            self.adaptive_delay.record_failure()
                        if attempt < retries:
                            # 增强退避策略：指数退避 + 随机抖动 + 最大限制
                            base_delay = min(2 ** attempt, 120)  # 最大120秒
                            jitter = random.uniform(0, 10)  # 0-10秒随机抖动
                            sleep_time = base_delay + jitter
                            self.logger.info(f'等待 {sleep_time:.1f} 秒后重试...')
                            time.sleep(sleep_time)
                            continue
                        else:
                            self.logger.error(f'请求最终失败（触发反爬）: {url}')
                            return None
                    else:
                        if self.adaptive_delay:
                            self.adaptive_delay.record_success()
                
                response.raise_for_status()
                response.encoding = 'utf-8'
                return html.fromstring(response.text)
            except requests.exceptions.RequestException as e:
                self.logger.warning(f'请求失败 (尝试 {attempt + 1}/{retries + 1}): {e}')
                if self.adaptive_delay:
                    self.adaptive_delay.record_failure()
                if attempt < retries:
                    # 增强退避策略
                    base_delay = min(2 ** attempt, 120)  # 最大120秒
                    jitter = random.uniform(0, 10)  # 0-10秒随机抖动
                    sleep_time = base_delay + jitter
                    time.sleep(sleep_time)
                else:
                    self.logger.error(f'请求最终失败: {url}')
                    return None
        return None
    
    def _check_limit(self):
        """检查是否达到爬取结果数量限制（线程安全）"""
        if self.thread_safe and self._lock:
            with self._lock:
                if self.limit_result > 0 and self.result_count >= self.limit_result:
                    self.logger.info(f'已达到爬取结果数量限制：{self.limit_result}条，停止爬取')
                    return True
                return False
        else:
            if self.limit_result > 0 and self.result_count >= self.limit_result:
                self.logger.info(f'已达到爬取结果数量限制：{self.limit_result}条，停止爬取')
                return True
            return False
    
    def _increment_result_count(self, count=1):
        """增加结果计数（线程安全）"""
        if self.thread_safe and self._lock:
            with self._lock:
                self.result_count += count
        else:
            self.result_count += count
    
    def _check_and_add_seen_id(self, weibo_id):
        """检查并添加已见ID（线程安全）"""
        # 始终使用专门的锁保护 seen_ids，确保多线程安全
        with self._seen_ids_lock:
            if weibo_id in self.seen_ids:
                return True
            self.seen_ids.add(weibo_id)
            return False
    
    def _sanitize_filename(self, filename):
        """
        清理文件名中的非法字符
        Windows非法字符: \ / : * ? " < > |
        获取失败时返回空字符串，不影响其他功能
        """
        try:
            # 处理非字符串输入
            if not isinstance(filename, str):
                filename = str(filename) if filename else ''
            
            # 解码URL编码的字符（包括中文）
            from urllib.parse import unquote
            decoded = unquote(filename)
            # 替换Windows非法字符
            invalid_chars = '\\/:*?"<>|'
            for char in invalid_chars:
                decoded = decoded.replace(char, '_')
            # 限制文件名长度
            if len(decoded) > 100:
                decoded = decoded[:100]
            return decoded
        except Exception:
            # 处理失败时返回安全默认值
            return 'unknown'
    
    def _get_csv_path(self, keyword):
        """获取CSV文件路径（带时间戳，直接存储在输出目录下）"""
        # 使用原始关键词（解码后的中文）作为文件名
        original_keyword = self._get_original_keyword(keyword)
        # 清理文件名中的非法字符
        safe_keyword = self._sanitize_filename(original_keyword)
        
        # 生成时间戳：年月日时分秒
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # 确保输出目录存在
        if not os.path.isdir(self.config.OUTPUT_DIR):
            os.makedirs(self.config.OUTPUT_DIR)
        return os.path.join(self.config.OUTPUT_DIR, f'{safe_keyword}-{timestamp}.csv')
    
    def _get_csv_writer(self, keyword):
        """
        获取CSV写入器（使用缓存，避免频繁打开关闭文件）
        线程安全：多线程模式下加锁保护文件创建和表头写入
        """
        # 多线程模式下加锁保护文件创建操作
        if self.thread_safe and self._lock:
            with self._lock:
                return self._create_csv_writer(keyword)
        else:
            return self._create_csv_writer(keyword)
    
    def _create_csv_writer(self, keyword):
        """实际创建CSV写入器的内部方法"""
        if keyword not in self._csv_writers:
            file_path = self._get_csv_path(keyword)
            is_first_write = not os.path.isfile(file_path)
            
            # 打开文件并缓存
            f = open(file_path, 'a', encoding='utf-8-sig', newline='')
            writer = csv.writer(f)
            
            self._csv_files[keyword] = f
            self._csv_writers[keyword] = writer
            self._csv_first_write[keyword] = is_first_write
            
            # 写入表头
            if is_first_write:
                writer.writerow(WeiboItem.get_csv_header())
        
        return self._csv_writers[keyword]
    
    def _close_csv_files(self):
        """关闭所有CSV文件句柄（线程安全）"""
        # 多线程模式下加锁保护字典遍历
        if self.thread_safe and self._lock:
            with self._lock:
                self._do_close_csv_files()
        else:
            self._do_close_csv_files()
    
    def _do_close_csv_files(self):
        """实际关闭CSV文件的内部方法"""
        for keyword, f in self._csv_files.items():
            try:
                f.close()
                # 使用原始关键词显示日志
                original_keyword = self._get_original_keyword(keyword)
                self.logger.debug(f'已关闭CSV文件: {original_keyword}')
            except (IOError, OSError) as e:
                self.logger.warning(f'关闭CSV文件失败: {e}')
        self._csv_files.clear()
        self._csv_writers.clear()
        self._csv_first_write.clear()
    
    def _save_to_csv(self, weibo_item, keyword):
        """
        保存微博数据到CSV文件
        :param weibo_item: WeiboItem对象
        :param keyword: 搜索关键词（可能是URL编码的）
        """
        try:
            # 将URL编码的keyword转换为原始中文keyword（用于CSV文件名）
            original_keyword = self._get_original_keyword(keyword)
            
            # 多线程模式下加锁保护文件写入操作
            if self.thread_safe and self._lock:
                with self._lock:
                    writer = self._get_csv_writer(original_keyword)
                    writer.writerow(weibo_item.to_csv_row())
                    # 立即刷新到磁盘，防止数据丢失
                    self._csv_files[original_keyword].flush()
            else:
                writer = self._get_csv_writer(original_keyword)
                writer.writerow(weibo_item.to_csv_row())
                # 立即刷新到磁盘，防止数据丢失
                self._csv_files[original_keyword].flush()
            
            self.logger.debug(f'已保存微博: {weibo_item.id}')
        except (IOError, OSError) as e:
            self.logger.error(f'保存CSV失败: {e}')
    
    def _get_ip(self, bid):
        """
        获取微博的IP属地（带缓存机制）
        :param bid: 微博bid
        :return: IP属地字符串
        """
        if not bid:
            return ""
        
        # 检查缓存
        if bid in self._ip_cache:
            return self._ip_cache[bid]
        
        url = f"https://weibo.com/ajax/statuses/show?id={bid}&locale=zh-CN"
        try:
            response = self.session.get(url, timeout=5)  # IP获取使用固定短超时
            if response.status_code == 200:
                try:
                    data = response.json()
                    ip_str = data.get("region_name", "")
                    if ip_str:
                        # 提取最后一部分（通常是省份/城市）
                        parts = ip_str.split()
                        ip_result = parts[-1] if parts else ""
                        # 缓存结果
                        self._ip_cache[bid] = ip_result
                        return ip_result
                except ValueError:
                    pass  # 静默失败
        except (requests.exceptions.Timeout, requests.exceptions.RequestException):
            pass  # 静默失败，不记录日志避免刷屏
        except Exception:
            pass  # 静默失败
        
        # 缓存空结果，避免重复请求
        self._ip_cache[bid] = ""
        return ""
    
    def _parse_weibo(self, card, keyword):
        """
        解析单条微博
        :param card: 微博卡片HTML元素
        :param keyword: 搜索关键词
        :return: (weibo_item, retweet_item) 元组，retweet_item可能为None
        """
        # 检查是否达到限制
        if self._check_limit():
            return None, None
        
        weibo = WeiboItem()
        
        # 获取微博ID
        mid = card.xpath('@mid')
        if not mid:
            return None, None
        weibo.id = mid[0]
        
        # 检查是否已抓取过（去重）- 线程安全
        if self._check_and_add_seen_id(weibo.id):
            return None, None
        
        # 获取微博bid
        from_a = card.xpath('.//div[@class="from"]/a[1]/@href')
        if from_a:
            weibo.bid = from_a[0].split('/')[-1].split('?')[0]
        
        # 获取用户信息
        info = card.xpath(
            "div[@class='card']/div[@class='card-feed']/div[@class='content']/div[@class='info']"
        )
        if not info:
            return None, None
        
        info = info[0]
        
        # 用户ID和昵称
        user_link = info.xpath('div[2]/a/@href')
        if user_link:
            weibo.user_id = user_link[0].split('?')[0].split('/')[-1]
        weibo.screen_name = info.xpath('div[2]/a/@nick-name')
        if weibo.screen_name:
            weibo.screen_name = weibo.screen_name[0]
        else:
            weibo.screen_name = ''
        
        # VIP信息
        weibo.vip_type, weibo.vip_level = get_vip_info(info)
        
        # 获取正文
        txt_sel = card.xpath('.//p[@class="txt"]')
        if not txt_sel:
            return None, None
        txt_sel = txt_sel[0]
        
        # 检查是否是转发微博
        retweet_sel = card.xpath('.//div[@class="card-comment"]')
        retweet_txt_sel = None
        if retweet_sel:
            retweet_txt = retweet_sel[0].xpath('.//p[@class="txt"]')
            if retweet_txt:
                retweet_txt_sel = retweet_txt[0]
        
        # 检查长微博
        content_full = card.xpath('.//p[@node-type="feed_list_content_full"]')
        is_long_weibo = False
        is_long_retweet = False
        
        if content_full:
            if not retweet_sel:
                txt_sel = content_full[0]
                is_long_weibo = True
            elif len(content_full) == 2:
                txt_sel = content_full[0]
                retweet_txt_sel = content_full[1]
                is_long_weibo = True
                is_long_retweet = True
            elif retweet_sel and retweet_sel[0].xpath('.//p[@node-type="feed_list_content_full"]'):
                retweet_full = retweet_sel[0].xpath('.//p[@node-type="feed_list_content_full"]')
                retweet_txt_sel = retweet_full[0]
                is_long_retweet = True
            else:
                txt_sel = content_full[0]
                is_long_weibo = True
        
        # 提取正文文本
        text = txt_sel.xpath('string(.)')
        if text:
            weibo.text = text.replace('\u200b', '').replace('\ue627', '')
        
        # 获取文章URL
        weibo.article_url = get_article_url(txt_sel)
        
        # 获取位置
        weibo.location = get_location(txt_sel)
        if weibo.location and isinstance(weibo.text, str):
            weibo.text = weibo.text.replace('2' + weibo.location, '')
        
        # 清理文本 - 移除前导空格和特殊字符
        weibo.text = weibo.text.strip().replace('\u200b', '').replace('\ue627', '')
        # 移除开头的 "2" 字符（位置标记）和空格
        if weibo.text.startswith('2'):
            weibo.text = weibo.text[1:].strip()
        weibo.text = weibo.text.replace(' ', '')
        # 移除长微博末尾的 "展开" 标记
        if is_long_weibo and weibo.text.endswith('展开'):
            weibo.text = weibo.text[:-2].strip()
        
        # 获取@用户和话题
        weibo.at_users = get_at_users(txt_sel)
        weibo.topics = get_topics(txt_sel)
        
        # 获取互动数据
        # 转发数
        reposts = card.xpath('.//a[@action-type="feed_list_forward"]/text()')
        if reposts:
            reposts_text = ''.join(reposts)
            weibo.reposts_count = extract_number(reposts_text)
        
        # 评论数
        comments = card.xpath('.//a[@action-type="feed_list_comment"]/text()')
        if comments:
            weibo.comments_count = extract_number(comments[0])
        
        # 点赞数
        attitudes = card.xpath('.//a[@action-type="feed_list_like"]//span[@class="woo-like-count"]/text()')
        if not attitudes:
            attitudes = card.xpath('.//a[@action-type="feed_list_like"]/button/span[2]/text()')
        if attitudes:
            weibo.attitudes_count = extract_number(attitudes[0])
        
        # 发布时间
        created_at = card.xpath('.//div[@class="from"]/a[1]/text()')
        if created_at:
            created_at = created_at[0].replace(' ', '').replace('\n', '').split('前')[0]
            weibo.created_at = standardize_date(created_at)
        
        # 发布工具
        source = card.xpath('.//div[@class="from"]/a[2]/text()')
        weibo.source = source[0] if source else ''
        
        # 获取图片（延迟赋值，根据是否是转发微博决定归属）
        pics = []
        is_exist_pic = card.xpath('.//div[@class="media media-piclist"]')
        if is_exist_pic:
            pics = is_exist_pic[0].xpath('ul[1]/li/img/@src')
            pics = [pic[8:] if pic.startswith('https://') else pic for pic in pics]
            pics = [re.sub(r'/.*?/', '/large/', pic, 1) for pic in pics]
            pics = ['https://' + pic for pic in pics]
        
        # 获取视频（延迟赋值，根据是否是转发微博决定归属）
        video_url = ''
        is_exist_video = card.xpath('.//div[@class="thumbnail"]//video-player')
        if is_exist_video:
            try:
                video_html = html.tostring(is_exist_video[0], encoding='unicode')
                video_match = re.findall(r'src:\'(.*?)\'', video_html)
                if video_match:
                    video_url = video_match[0].replace('&amp;', '&')
                    video_url = 'http:' + video_url if not video_url.startswith('http') else video_url
            except (ValueError, TypeError) as e:
                self.logger.debug(f'解析视频URL失败: {e}')
        
        # 处理转发微博
        retweet = None
        if retweet_sel and retweet_sel[0].xpath('.//div[@node-type="feed_list_forwardContent"]/a[1]'):
            retweet = WeiboItem()
            
            # 转发微博ID
            retweet_id = retweet_sel[0].xpath('.//a[@action-type="feed_list_like"]/@action-data')
            if retweet_id:
                retweet.id = retweet_id[0][4:] if retweet_id[0].startswith('mid=') else retweet_id[0]
            
            # 转发微博bid
            retweet_bid = retweet_sel[0].xpath('.//p[@class="from"]/a/@href')
            if retweet_bid:
                retweet.bid = retweet_bid[0].split('/')[-1].split('?')[0]
            
            # 转发微博用户信息
            retweet_info = retweet_sel[0].xpath('.//div[@node-type="feed_list_forwardContent"]/a[1]')[0]
            retweet_user_link = retweet_info.xpath('@href')
            if retweet_user_link:
                retweet.user_id = retweet_user_link[0].split('/')[-1]
            retweet.screen_name = retweet_info.xpath('@nick-name')
            if retweet.screen_name:
                retweet.screen_name = retweet.screen_name[0]
            else:
                retweet.screen_name = ''
            
            # VIP信息
            retweet.vip_type, retweet.vip_level = get_vip_info(retweet_info)
            
            # 转发微博正文
            if retweet_txt_sel is not None:
                retweet_text = retweet_txt_sel.xpath('string(.)')
                if retweet_text:
                    retweet.text = retweet_text.replace('\u200b', '').replace('\ue627', '')
            
            retweet.article_url = get_article_url(retweet_txt_sel) if retweet_txt_sel else ''
            retweet.location = get_location(retweet_txt_sel) if retweet_txt_sel else ''
            if retweet.location and isinstance(retweet.text, str):
                retweet.text = retweet.text.replace('2' + retweet.location, '')
            
            retweet.text = retweet.text[2:].replace(' ', '') if len(retweet.text) > 2 else retweet.text
            if is_long_retweet and retweet.text.endswith('展开'):
                retweet.text = retweet.text[:-2]
            
            retweet.at_users = get_at_users(retweet_txt_sel) if retweet_txt_sel else ''
            retweet.topics = get_topics(retweet_txt_sel) if retweet_txt_sel else ''
            
            # 转发微博的互动数据
            retweet_reposts = retweet_sel[0].xpath('.//ul[@class="act s-fr"]/li[1]/a[1]/text()')
            if retweet_reposts:
                retweet.reposts_count = extract_number(retweet_reposts[0])
            
            retweet_comments = retweet_sel[0].xpath('.//ul[@class="act s-fr"]/li[2]/a[1]/text()')
            if retweet_comments:
                retweet.comments_count = extract_number(retweet_comments[0])
            
            retweet_attitudes = retweet_sel[0].xpath(
                './/a[@class="woo-box-flex woo-box-alignCenter woo-box-justifyCenter"]//span[@class="woo-like-count"]/text()'
            )
            if retweet_attitudes:
                retweet.attitudes_count = extract_number(retweet_attitudes[0])
            
            retweet_created = retweet_sel[0].xpath('.//p[@class="from"]/a[1]/text()')
            if retweet_created:
                retweet_created = retweet_created[0].replace(' ', '').replace('\n', '').split('前')[0]
                retweet.created_at = standardize_date(retweet_created)
            
            retweet_source = retweet_sel[0].xpath('.//p[@class="from"]/a[2]/text()')
            retweet.source = retweet_source[0] if retweet_source else ''
            
            retweet.retweet_id = ''
            
            # 转发微博通常不包含自己的媒体资源，资源在主微博中展示
            # 如果转发微博有独立的媒体资源，需要单独解析（当前逻辑保持简洁）
            retweet.pics = []
            retweet.video_url = ''
            
            # 检查转发微博是否已存在（去重）
            if retweet.id and self._check_and_add_seen_id(retweet.id):
                self.logger.debug(f'转发微博已存在，跳过: {retweet.id}')
                weibo.retweet_id = retweet.id  # 仍然设置转发ID，但不再保存转发微博
                retweet = None
            else:
                # 增加计数（线程安全）
                self._increment_result_count(1)
                
                # 保存转发微博
                self._save_to_csv(retweet, keyword)
                
                # 设置主微博的转发ID
                weibo.retweet_id = retweet.id
        
        # 获取IP属地
        weibo.ip = self._get_ip(weibo.bid)
        
        # 获取用户认证信息
        avator = card.xpath(
            "div[@class='card']/div[@class='card-feed']/div[@class='avator']"
        )
        if avator:
            weibo.user_authentication = get_user_auth(avator[0])
        
        # 根据是否是转发微博，分配媒体资源
        # 主微博（原创或转发的载体）拥有媒体资源
        weibo.pics = pics
        weibo.video_url = video_url
        
        # 增加计数（线程安全）
        self._increment_result_count(1)
        
        # 保存主微博
        self._save_to_csv(weibo, keyword)
        
        # 获取当前计数（线程安全读取）
        if self.thread_safe and self._lock:
            with self._lock:
                current_count = self.result_count
        else:
            current_count = self.result_count
        
        self.logger.info(f'已抓取微博 [{current_count}]: {weibo.screen_name} - {weibo.text[:30]}...')
        
        return weibo, retweet
    
    def _parse_page(self, doc, keyword, base_url, province=None):
        """
        解析搜索结果页面
        :param doc: HTML文档对象
        :param keyword: 搜索关键词
        :param base_url: 基础URL
        :param province: 省份信息（可选）
        :return: 下一页URL或None
        """
        # 检查是否为空结果
        is_empty = doc.xpath('//div[@class="card card-no-result s-pt20b40"]')
        if is_empty:
            self.logger.info('当前页面搜索结果为空')
            return None
        
        # 获取页码数量
        page_count = len(doc.xpath('//ul[@class="s-scroll"]/li'))
        
        # 解析微博列表
        cards = doc.xpath("//div[@class='card-wrap']")
        for card in cards:
            if self._check_limit():
                return None
            self._parse_weibo(card, keyword)
            # 使用反爬优化的随机延迟或固定延迟
            self._apply_delay()
        
        # 获取下一页链接
        next_url = doc.xpath('//a[@class="next"]/@href')
        if next_url:
            return self.base_url + next_url[0]
        return None
    
    def _crawl_by_page(self, url, keyword, base_url, province=None):
        """
        按页爬取（用于页数较少的情况）
        """
        current_url = url
        while current_url and not self._check_limit():
            self.logger.info(f'正在爬取: {current_url}')
            doc = self._make_request(current_url)
            if doc is None:
                break
            
            next_url = self._parse_page(doc, keyword, base_url, province)
            current_url = next_url
            
            if current_url:
                self._apply_delay()
    
    def _crawl_by_day(self, url, keyword, base_url, province=None, date=None):
        """
        按天为单位筛选爬取
        """
        self.logger.info(f'按天筛选: {date}')
        doc = self._make_request(url)
        if doc is None:
            return
        
        # 检查是否为空结果
        is_empty = doc.xpath('//div[@class="card card-no-result s-pt20b40"]')
        if is_empty:
            self.logger.info(f'{date} 搜索结果为空')
            return
        
        # 获取页码数量
        page_count = len(doc.xpath('//ul[@class="s-scroll"]/li'))
        
        if page_count < self.further_threshold:
            # 页数较少，直接按页爬取
            self._parse_page(doc, keyword, base_url, province)
            
            # 获取下一页
            next_url = doc.xpath('//a[@class="next"]/@href')
            while next_url and not self._check_limit():
                self._apply_delay()
                next_full_url = self.base_url + next_url[0]
                doc = self._make_request(next_full_url)
                if doc is None:
                    break
                next_url = self._parse_page(doc, keyword, base_url, province)
        else:
            # 页数较多，按小时细分
            start_date_str = date + '-0'
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d-%H')
            
            for i in range(24):
                if self._check_limit():
                    return
                
                start_str = start_date.strftime('%Y-%m-%d-') + str(start_date.hour)
                start_date = start_date + timedelta(hours=1)
                end_str = start_date.strftime('%Y-%m-%d-') + str(start_date.hour)
                
                hour_url = base_url + self.weibo_type + self.contain_type
                hour_url += '&timescope=custom:{}:{}&page=1'.format(start_str, end_str)
                
                if province:
                    self._crawl_by_hour_province(hour_url, keyword, start_str, end_str, province)
                else:
                    self._crawl_by_hour(hour_url, keyword, start_str, end_str)
                
                self._apply_delay()
    
    def _crawl_by_hour(self, url, keyword, start_time, end_time):
        """
        按小时为单位筛选爬取
        """
        self.logger.info(f'按小时筛选: {start_time} - {end_time}')
        doc = self._make_request(url)
        if doc is None:
            return
        
        # 检查是否为空结果
        is_empty = doc.xpath('//div[@class="card card-no-result s-pt20b40"]')
        if is_empty:
            return
        
        # 获取页码数量
        page_count = len(doc.xpath('//ul[@class="s-scroll"]/li'))
        
        if page_count < self.further_threshold:
            # 页数较少，直接按页爬取
            self._parse_page(doc, keyword, url.split('&timescope')[0])
            
            next_url = doc.xpath('//a[@class="next"]/@href')
            while next_url and not self._check_limit():
                self._apply_delay()
                next_full_url = self.base_url + next_url[0]
                doc = self._make_request(next_full_url)
                if doc is None:
                    break
                next_url = self._parse_page(doc, keyword, url.split('&timescope')[0])
        else:
            # 页数较多，按地区细分
            for region_name, region_info in self.regions.items():
                if self._check_limit():
                    return
                
                region_url = 'https://s.weibo.com/weibo?q={}&region=custom:{}:1000'.format(
                    keyword, region_info['code']
                )
                region_url += self.weibo_type + self.contain_type
                region_url += '&timescope=custom:{}:{}&page=1'.format(start_time, end_time)
                
                self._crawl_by_hour_province(region_url, keyword, start_time, end_time, region_info)
                self._apply_delay()
    
    def _crawl_by_hour_province(self, url, keyword, start_time, end_time, province):
        """
        按小时和省份为单位筛选爬取
        """
        self.logger.info(f'按小时+省份筛选: {start_time} - {end_time}, 省份: {province}')
        doc = self._make_request(url)
        if doc is None:
            return
        
        # 检查是否为空结果
        is_empty = doc.xpath('//div[@class="card card-no-result s-pt20b40"]')
        if is_empty:
            return
        
        # 获取页码数量
        page_count = len(doc.xpath('//ul[@class="s-scroll"]/li'))
        
        if page_count < self.further_threshold:
            # 页数较少，直接按页爬取
            self._parse_page(doc, keyword, url.split('&timescope')[0], province)
            
            next_url = doc.xpath('//a[@class="next"]/@href')
            while next_url and not self._check_limit():
                self._apply_delay()
                next_full_url = self.base_url + next_url[0]
                doc = self._make_request(next_full_url)
                if doc is None:
                    break
                next_url = self._parse_page(doc, keyword, url.split('&timescope')[0], province)
        else:
            # 页数较多，按城市细分
            for city_name, city_code in province.get('city', {}).items():
                if self._check_limit():
                    return
                
                city_url = 'https://s.weibo.com/weibo?q={}&region=custom:{}:{}'.format(
                    keyword, province['code'], city_code
                )
                city_url += self.weibo_type + self.contain_type
                city_url += '&timescope=custom:{}:{}&page=1'.format(start_time, end_time)
                
                self._crawl_by_page(city_url, keyword, city_url.split('&timescope')[0], province)
                self._apply_delay()
    
    def _crawl_single_keyword(self, keyword_info):
        """
        爬取单个关键词（用于多线程）
        :param keyword_info: (index, keyword, keyword_display, weibo_type) 元组
        """
        i, keyword, keyword_display, weibo_type = keyword_info
        
        # 设置当前微博类型
        self.weibo_type = weibo_type
        type_name = self._get_weibo_type_name(weibo_type)
        
        # 多线程模式下每个线程创建独立的 session，避免共享导致的线程安全问题
        thread_session = requests.Session()
        thread_session.headers.update(self.session.headers)
        original_session = self.session
        self.session = thread_session
        
        # 多线程模式下添加随机初始延迟，避免所有线程同时请求
        import random
        initial_delay = random.uniform(1, 5)
        time.sleep(initial_delay)
        
        self.logger.info(f'[线程] 开始搜索关键词: {keyword_display} | 类型: {type_name}')
        
        try:
            start_datetime = datetime.strptime(self.start_date, '%Y-%m-%d')
            end_datetime = datetime.strptime(self.end_date, '%Y-%m-%d') + timedelta(days=1)
            start_str = start_datetime.strftime('%Y-%m-%d') + '-0'
            end_str = end_datetime.strftime('%Y-%m-%d') + '-0'
            
            if self._check_limit():
                return
            
            # 检查是否按地区筛选
            if not self.config.REGION or '全部' in self.config.REGION:
                # 不按地区筛选
                base_url = 'https://s.weibo.com/weibo?q={}'.format(keyword)
                url = base_url + self.weibo_type + self.contain_type
                url += '&timescope=custom:{}:{}'.format(start_str, end_str)
                
                self.logger.info(f'[线程] 搜索URL: {url}')
                doc = self._make_request(url)
                if doc is None:
                    return
                
                # 检查是否为空结果
                is_empty = doc.xpath('//div[@class="card card-no-result s-pt20b40"]')
                if is_empty:
                    self.logger.info('[线程] 当前页面搜索结果为空')
                    return
                
                # 获取页码数量
                page_count = len(doc.xpath('//ul[@class="s-scroll"]/li'))
                self.logger.info(f'[线程] 搜索结果页数: {page_count}')
                
                if page_count < self.further_threshold:
                    # 页数较少，直接按页爬取
                    self._parse_page(doc, keyword, base_url)
                    
                    next_url = doc.xpath('//a[@class="next"]/@href')
                    while next_url and not self._check_limit():
                        self._apply_delay()
                        next_full_url = self.base_url + next_url[0]
                        doc = self._make_request(next_full_url, referer=url)
                        if doc is None:
                            break
                        next_url = self._parse_page(doc, keyword, base_url)
                else:
                    # 页数较多，按天细分
                    current_date = datetime.strptime(self.start_date, '%Y-%m-%d')
                    end_date = datetime.strptime(self.end_date, '%Y-%m-%d')
                    
                    while current_date <= end_date and not self._check_limit():
                        day_start = current_date.strftime('%Y-%m-%d') + '-0'
                        current_date = current_date + timedelta(days=1)
                        day_end = current_date.strftime('%Y-%m-%d') + '-0'
                        
                        day_url = base_url + self.weibo_type + self.contain_type
                        day_url += '&timescope=custom:{}:{}&page=1'.format(day_start, day_end)
                        
                        self._crawl_by_day(day_url, keyword, base_url, None, day_start[:-2])
                        self._apply_delay()
            else:
                # 按地区筛选
                for region_name, region_info in self.regions.items():
                    if self._check_limit():
                        break
                    
                    self.logger.info(f'[线程] 搜索地区: {region_name}')
                    base_url = 'https://s.weibo.com/weibo?q={}&region=custom:{}:1000'.format(
                        keyword, region_info['code']
                    )
                    url = base_url + self.weibo_type + self.contain_type
                    url += '&timescope=custom:{}:{}'.format(start_str, end_str)
                    
                    doc = self._make_request(url)
                    if doc is None:
                        continue
                    
                    # 检查是否为空结果
                    is_empty = doc.xpath('//div[@class="card card-no-result s-pt20b40"]')
                    if is_empty:
                        self.logger.info(f'[线程] {region_name} 搜索结果为空')
                        continue
                    
                    # 获取页码数量
                    page_count = len(doc.xpath('//ul[@class="s-scroll"]/li'))
                    
                    if page_count < self.further_threshold:
                        # 页数较少，直接按页爬取
                        self._parse_page(doc, keyword, base_url, region_info)
                        
                        next_url = doc.xpath('//a[@class="next"]/@href')
                        while next_url and not self._check_limit():
                            self._apply_delay()
                            next_full_url = self.base_url + next_url[0]
                            doc = self._make_request(next_full_url, referer=url)
                            if doc is None:
                                break
                            next_url = self._parse_page(doc, keyword, base_url, region_info)
                    else:
                        # 页数较多，按天细分
                        current_date = datetime.strptime(self.start_date, '%Y-%m-%d')
                        end_date = datetime.strptime(self.end_date, '%Y-%m-%d')
                                            
                        while current_date <= end_date and not self._check_limit():
                            day_start = current_date.strftime('%Y-%m-%d') + '-0'
                            current_date = current_date + timedelta(days=1)
                            day_end = current_date.strftime('%Y-%m-%d') + '-0'
                                                
                            day_url = base_url + self.weibo_type + self.contain_type
                            day_url += '&timescope=custom:{}:{}&page=1'.format(day_start, day_end)
                                                
                            self._crawl_by_day(day_url, keyword, base_url, region_info, day_start[:-2])
                            self._apply_delay()
            
            self.logger.info(f'[线程] 关键词 {keyword_display} 爬取完成')
            
        finally:
            # 恢复原始 session（确保即使发生异常也能恢复）
            self.session = original_session
    
    def _get_weibo_type_name(self, weibo_type_param):
        """获取微博类型的中文名称"""
        type_names = {
            '&typeall=1': '全部微博',
            '&scope=ori': '原创微博',
            '&xsort=hot': '热门微博',
            '&atten=1': '关注人微博',
            '&vip=1': '认证用户微博',
            '&category=4': '媒体微博',
            '&viewpoint=1': '观点微博'
        }
        return type_names.get(weibo_type_param, '未知类型')
    
    def _get_random_delay(self):
        """获取随机延迟时间（支持范围配置）"""
        min_delay, max_delay = self.download_delay_range
        # 使用正态分布生成更自然的延迟，但限制在范围内
        mean = (min_delay + max_delay) / 2
        std = (max_delay - min_delay) / 4
        delay = random.gauss(mean, std)
        return max(min_delay, min(max_delay, delay))
    
    def _apply_delay(self):
        """应用延迟（支持反爬优化和范围配置）"""
        if hasattr(self.config, 'ENABLE_ANTI_DETECT') and self.config.ENABLE_ANTI_DETECT:
            if self.adaptive_delay:
                self.adaptive_delay.sleep()
            else:
                delay = self.anti_detect.get_random_delay()
                time.sleep(delay)
        else:
            # 使用范围配置的随机延迟
            delay = self._get_random_delay()
            self.logger.debug(f'随机延迟: {delay:.2f}秒')
            time.sleep(delay)
    
    def _handle_cookie_invalid(self):
        """
        处理Cookie失效情况
        输出详细的重新获取指南
        """
        self.logger.error('=' * 60)
        self.logger.error('Cookie已失效！')
        self.logger.error('=' * 60)
        self.logger.error('')
        self.logger.error('请按以下步骤重新获取Cookie：')
        self.logger.error('')
        self.logger.error('方法1（推荐）：')
        self.logger.error('  1. 用Chrome打开 https://passport.weibo.cn/signin/login')
        self.logger.error('  2. 输入微博用户名和密码登录')
        self.logger.error('  3. 登录成功后跳转到 https://m.weibo.cn')
        self.logger.error('  4. 按F12打开开发者工具 -> Network')
        self.logger.error('  5. 在地址栏输入并跳转到 https://weibo.cn')
        self.logger.error('  6. 点击任意一条微博，在Network中找到weibo.cn请求')
        self.logger.error('  7. 在Request Headers中找到Cookie值，复制到config.py')
        self.logger.error('')
        self.logger.error('方法2（新版微博）：')
        self.logger.error('  1. 用Chrome打开 https://weibo.com/ 并登录')
        self.logger.error('  2. 按F12打开开发者工具 -> Network')
        self.logger.error('  3. 刷新页面，找到任意weibo.cn或weibo.com请求')
        self.logger.error('  4. 在Request Headers中找到Cookie值，复制到config.py')
        self.logger.error('')
        self.logger.error('注意事项：')
        self.logger.error('  - Cookie有效期通常为几天到几周，失效后需要重新获取')
        self.logger.error('  - 请勿泄露Cookie给他人，否则可能导致账号被盗')
        self.logger.error('  - 建议定期更新Cookie以确保爬虫稳定运行')
        self.logger.error('=' * 60)
    
    def crawl(self):
        """
        主爬取入口
        支持多线程和单线程模式
        """
        self.logger.info('=' * 50)
        self.logger.info('微博搜索爬虫启动')
        self.logger.info(f'关键词: {self.keyword_list_original}')
        self.logger.info(f'时间范围: {self.start_date} 至 {self.end_date}')
        
        # 判断是否启用多线程
        enable_multithread = getattr(self.config, 'ENABLE_MULTITHREAD', False)
        max_workers = getattr(self.config, 'MAX_WORKERS', 3)
        
        if enable_multithread and len(self.keyword_list) > 1:
            self.logger.info(f'多线程模式: 启用 (最大并发: {max_workers})')
            self.logger.info('=' * 50)
            return self._crawl_multithread(max_workers)
        else:
            self.logger.info('多线程模式: 禁用')
            self.logger.info('=' * 50)
            return self._crawl_singlethread()
    
    def _crawl_multithread(self, max_workers):
        """
        多线程爬取（支持多微博类型）
        :param max_workers: 最大并发线程数
        """
        # 启用线程安全模式
        self.thread_safe = True
        self._lock = threading.Lock()
        
        # 准备任务列表（类型 + 关键词的组合）
        tasks = []
        for weibo_type in self.weibo_type_list:
            for i, keyword in enumerate(self.keyword_list):
                keyword_display = self.keyword_list_original[i]
                tasks.append((i, keyword, keyword_display, weibo_type))
        
        # 使用线程池执行
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_task = {
                executor.submit(self._crawl_single_keyword, task): task 
                for task in tasks
            }
            
            # 等待所有任务完成
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                keyword_display = task[2]
                try:
                    future.result()
                except Exception as e:
                    self.logger.error(f'关键词 {keyword_display} 爬取异常: {e}')
        
        self.logger.info('=' * 50)
        self.logger.info(f'爬虫执行完毕，共抓取 {self.result_count} 条微博')
        self.logger.info('=' * 50)
        
        # 关闭所有CSV文件
        self._close_csv_files()
        
        return self.result_count
    
    def _crawl_singlethread(self):
        """
        单线程爬取（支持多微博类型）
        外层循环遍历微博类型，内层循环遍历关键词
        """
        start_datetime = datetime.strptime(self.start_date, '%Y-%m-%d')
        end_datetime = datetime.strptime(self.end_date, '%Y-%m-%d') + timedelta(days=1)
        start_str = start_datetime.strftime('%Y-%m-%d') + '-0'
        end_str = end_datetime.strftime('%Y-%m-%d') + '-0'
        
        # 遍历每种微博类型
        for weibo_type in self.weibo_type_list:
            if self._check_limit():
                break
            
            self.weibo_type = weibo_type  # 设置当前类型
            type_name = self._get_weibo_type_name(weibo_type)
            self.logger.info(f'当前微博类型: {type_name}')
            
            for i, keyword in enumerate(self.keyword_list):
                if self._check_limit():
                    break
                
                # 使用原始关键词（中文）显示日志
                keyword_display = self.keyword_list_original[i]
                self.logger.info(f'开始搜索关键词: {keyword_display}')
                
                # 检查是否按地区筛选
                if not self.config.REGION or '全部' in self.config.REGION:
                    # 不按地区筛选
                    base_url = 'https://s.weibo.com/weibo?q={}'.format(keyword)
                    url = base_url + self.weibo_type + self.contain_type
                    url += '&timescope=custom:{}:{}'.format(start_str, end_str)
                    
                    self.logger.info(f'搜索URL: {url}')
                    doc = self._make_request(url)
                    if doc is None:
                        continue
                    
                    # 检查是否为空结果
                    is_empty = doc.xpath('//div[@class="card card-no-result s-pt20b40"]')
                    if is_empty:
                        self.logger.info('当前页面搜索结果为空')
                        continue
                    
                    # 获取页码数量
                    page_count = len(doc.xpath('//ul[@class="s-scroll"]/li'))
                    self.logger.info(f'搜索结果页数: {page_count}')
                    
                    if page_count < self.further_threshold:
                        # 页数较少，直接按页爬取
                        self._parse_page(doc, keyword, base_url)
                        
                        next_url = doc.xpath('//a[@class="next"]/@href')
                        while next_url and not self._check_limit():
                            self._apply_delay()
                            next_full_url = self.base_url + next_url[0]
                            doc = self._make_request(next_full_url, referer=url)
                            if doc is None:
                                break
                            next_url = self._parse_page(doc, keyword, base_url)
                    else:
                        # 页数较多，按天细分
                        current_date = datetime.strptime(self.start_date, '%Y-%m-%d')
                        end_date = datetime.strptime(self.end_date, '%Y-%m-%d')
                        
                        while current_date <= end_date and not self._check_limit():
                            day_start = current_date.strftime('%Y-%m-%d') + '-0'
                            current_date = current_date + timedelta(days=1)
                            day_end = current_date.strftime('%Y-%m-%d') + '-0'
                            
                            day_url = base_url + self.weibo_type + self.contain_type
                            day_url += '&timescope=custom:{}:{}&page=1'.format(day_start, day_end)
                            
                            self._crawl_by_day(day_url, keyword, base_url, None, day_start[:-2])
                            self._apply_delay()
                else:
                    # 按地区筛选
                    for region_name, region_info in self.regions.items():
                        if self._check_limit():
                            break
                        
                        self.logger.info(f'搜索地区: {region_name}')
                        base_url = 'https://s.weibo.com/weibo?q={}&region=custom:{}:1000'.format(
                            keyword, region_info['code']
                        )
                        url = base_url + self.weibo_type + self.contain_type
                        url += '&timescope=custom:{}:{}'.format(start_str, end_str)
                        
                        doc = self._make_request(url)
                        if doc is None:
                            continue
                        
                        # 检查是否为空结果
                        is_empty = doc.xpath('//div[@class="card card-no-result s-pt20b40"]')
                        if is_empty:
                            self.logger.info(f'{region_name} 搜索结果为空')
                            continue
                        
                        # 获取页码数量
                        page_count = len(doc.xpath('//ul[@class="s-scroll"]/li'))
                        
                        if page_count < self.further_threshold:
                            # 页数较少，直接按页爬取
                            self._parse_page(doc, keyword, base_url, region_info)
                            
                            next_url = doc.xpath('//a[@class="next"]/@href')
                            while next_url and not self._check_limit():
                                self._apply_delay()
                                next_full_url = self.base_url + next_url[0]
                                doc = self._make_request(next_full_url, referer=url)
                                if doc is None:
                                    break
                                next_url = self._parse_page(doc, keyword, base_url, region_info)
                        else:
                            # 页数较多，按天细分
                            current_date = datetime.strptime(self.start_date, '%Y-%m-%d')
                            end_date = datetime.strptime(self.end_date, '%Y-%m-%d')
                            
                            while current_date <= end_date and not self._check_limit():
                                day_start = current_date.strftime('%Y-%m-%d') + '-0'
                                current_date = current_date + timedelta(days=1)
                                day_end = current_date.strftime('%Y-%m-%d') + '-0'
                                
                                day_url = base_url + self.weibo_type + self.contain_type
                                day_url += '&timescope=custom:{}:{}&page=1'.format(day_start, day_end)
                                
                                self._crawl_by_day(day_url, keyword, base_url, region_info, day_start[:-2])
                                self._apply_delay()
        
        self.logger.info('=' * 50)
        self.logger.info(f'爬虫执行完毕，共抓取 {self.result_count} 条微博')
        self.logger.info('=' * 50)
        
        # 关闭所有CSV文件
        self._close_csv_files()
        
        return self.result_count
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口，确保资源释放"""
        self._close_csv_files()
        return False
