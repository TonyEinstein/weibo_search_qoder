# -*- coding: utf-8 -*-
"""
反爬检测与防护模块
提供请求头伪装、代理管理、随机延迟等反爬功能
"""

import random
import time
import logging
import requests
from urllib.parse import urlparse

from user_agents import get_random_user_agent

logger = logging.getLogger('AntiDetect')


class AntiDetectManager:
    """反爬管理器"""
    
    def __init__(self, config):
        """
        初始化反爬管理器
        :param config: 配置对象
        """
        self.config = config
        self.proxy_index = 0
        self.cookie_index = 0
        
        # 初始化Cookie池
        self.cookie_pool = self._init_cookie_pool()
        
        # 初始化代理池
        self.proxy_pool = self._init_proxy_pool()
        
        # 请求头模板
        self.header_templates = [
            {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            },
            {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
        ]
    
    def _init_cookie_pool(self):
        """初始化Cookie池"""
        pool = []
        
        # 添加主Cookie（排除空值和占位符）
        if self.config.COOKIE and self.config.COOKIE.strip() and self.config.COOKIE != '请从浏览器复制Cookie':
            pool.append({'name': 'default', 'cookie': self.config.COOKIE})
        
        # 添加Cookie池中的Cookie
        if hasattr(self.config, 'COOKIE_POOL') and self.config.COOKIE_POOL:
            for item in self.config.COOKIE_POOL:
                if isinstance(item, dict) and 'cookie' in item:
                    pool.append(item)
        
        return pool
    
    def _init_proxy_pool(self):
        """初始化代理池"""
        if not hasattr(self.config, 'PROXY_LIST') or not self.config.PROXY_LIST:
            return []
        
        proxy_list = self.config.PROXY_LIST
        
        # 验证代理（如果启用）
        if hasattr(self.config, 'VERIFY_PROXY') and self.config.VERIFY_PROXY:
            valid_proxies = []
            for proxy in proxy_list:
                if self._verify_proxy(proxy):
                    valid_proxies.append(proxy)
                else:
                    logger.warning(f'代理验证失败: {proxy}')
            return valid_proxies
        
        return proxy_list
    
    def _verify_proxy(self, proxy):
        """验证代理是否可用"""
        try:
            test_url = 'https://weibo.com'
            proxies = {'http': proxy, 'https': proxy}
            response = requests.get(
                test_url, 
                proxies=proxies, 
                timeout=5,  # 减少超时时间，避免阻塞启动
                headers={'User-Agent': get_random_user_agent()}
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f'代理验证异常: {e}')
            return False
    
    def get_random_cookie(self):
        """获取随机Cookie"""
        if not self.cookie_pool:
            return None
        return random.choice(self.cookie_pool)
    
    def get_next_cookie(self):
        """轮询获取下一个Cookie"""
        if not self.cookie_pool:
            return None
        cookie = self.cookie_pool[self.cookie_index % len(self.cookie_pool)]
        self.cookie_index += 1
        return cookie
    
    def get_random_proxy(self):
        """获取随机代理"""
        if not self.proxy_pool:
            return None
        return random.choice(self.proxy_pool)
    
    def get_next_proxy(self):
        """轮询获取下一个代理"""
        if not self.proxy_pool:
            return None
        proxy = self.proxy_pool[self.proxy_index % len(self.proxy_pool)]
        self.proxy_index += 1
        return proxy
    
    def get_proxy(self):
        """根据策略获取代理"""
        if not self.proxy_pool:
            return None
        
        strategy = getattr(self.config, 'PROXY_STRATEGY', 'random')
        if strategy == 'round_robin':
            return self.get_next_proxy()
        return self.get_random_proxy()
    
    def build_headers(self, referer=None, url=None):
        """
        构建请求头
        :param referer: 来源页面URL
        :param url: 请求URL（用于提取Host）
        :return: 请求头字典
        """
        headers = {}
        
        # 基础User-Agent
        if self.config.USE_RANDOM_USER_AGENT:
            headers['User-Agent'] = get_random_user_agent()
        else:
            headers['User-Agent'] = self.config.USER_AGENT
        
        # 添加必要的标准请求头
        headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
        headers['Accept-Language'] = 'zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7'
        headers['Accept-Encoding'] = 'gzip, deflate, br'
        headers['Connection'] = 'keep-alive'
        headers['Upgrade-Insecure-Requests'] = '1'
        headers['Sec-Fetch-Dest'] = 'document'
        headers['Sec-Fetch-Mode'] = 'navigate'
        headers['Sec-Fetch-Site'] = 'none'
        headers['Sec-Fetch-User'] = '?1'
        headers['Cache-Control'] = 'max-age=0'
        
        # 添加Host（根据URL提取）
        if url:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            headers['Host'] = parsed.netloc
        else:
            headers['Host'] = 's.weibo.com'
        
        # 添加 Cookie（关键修复）- 注意：不在build_headers中添加Cookie，由调用方控制
        # 避免Cookie重复添加问题
        
        # 添加Referer
        if referer:
            headers['Referer'] = referer
        else:
            headers['Referer'] = 'https://s.weibo.com/'
        
        return headers
    
    def get_random_delay(self):
        """
        获取随机延迟时间
        统一使用 DOWNLOAD_DELAY 配置（支持范围 [min, max] 或固定值）
        :return: 延迟秒数
        """
        delay_config = getattr(self.config, 'DOWNLOAD_DELAY', 10)
        
        # 支持范围配置 [min, max]
        if isinstance(delay_config, (list, tuple)) and len(delay_config) == 2:
            min_delay, max_delay = delay_config[0], delay_config[1]
        else:
            # 固定值，使用 +/- 20% 波动
            min_delay = delay_config * 0.8
            max_delay = delay_config * 1.2
        
        # 使用正态分布生成更自然的延迟
        mean = (min_delay + max_delay) / 2
        std = (max_delay - min_delay) / 4
        delay = random.gauss(mean, std)
        
        # 限制在范围内
        delay = max(min_delay, min(max_delay, delay))
        return delay
    
    def sleep_random(self):
        """执行随机延迟"""
        delay = self.get_random_delay()
        logger.debug(f'随机延迟: {delay:.2f}秒')
        time.sleep(delay)
    
    def check_response(self, response):
        """
        检查响应是否触发反爬
        :param response: requests响应对象
        :return: (is_blocked, message, is_cookie_invalid) 元组
        """
        if response is None:
            return True, '响应为空', False
        
        # 检查状态码
        if response.status_code == 403:
            return True, 'IP被封禁(403)', False
        elif response.status_code == 429:
            return True, '请求过于频繁(429)', False
        elif response.status_code == 503:
            return True, '服务不可用(503)', False
        
        # 检查响应内容（仅在状态码正常时检查）
        if response.status_code == 200:
            content = response.text.lower()
            
            # 检测验证码页面（需要同时满足多个条件）
            captcha_keywords = ['验证码', 'captcha', '安全验证']
            if sum(1 for k in captcha_keywords if k in content) >= 2:
                return True, '触发验证码', False
            
            # 检测登录页面（更严格的判断：页面标题或主要内容区包含登录提示）
            login_indicators = ['请先登录', '登录后查看', 'login required', 'sign in to view']
            if any(indicator in content for indicator in login_indicators):
                return True, '需要登录', True  # Cookie失效标记
            
            # 检测Cookie失效的其他迹象
            cookie_invalid_indicators = ['登录超时', '重新登录', '账号已退出', '登录状态已失效']
            if any(indicator in content for indicator in cookie_invalid_indicators):
                return True, 'Cookie已失效', True  # Cookie失效标记
            
            # 检测封禁提示（需要明确的封禁关键词）
            block_keywords = ['访问受限', '操作频繁', '账号异常', '暂时无法访问', 'ip被封']
            if any(keyword in content for keyword in block_keywords):
                return True, '账号或IP受限', False
        
        return False, '正常', False
    
    def get_session_config(self, referer=None, url=None):
        """
        获取会话配置
        :param referer: 来源页面URL
        :param url: 请求URL（用于提取Host）
        :return: (headers, proxies) 元组
        """
        headers = self.build_headers(referer, url)
        
        proxies = None
        if hasattr(self.config, 'ENABLE_PROXY') and self.config.ENABLE_PROXY:
            proxy = self.get_proxy()
            if proxy:
                proxies = {'http': proxy, 'https': proxy}
                logger.debug(f'使用代理: {proxy}')
        
        return headers, proxies


class AdaptiveDelay:
    """自适应延迟控制器"""
    
    def __init__(self, min_delay=2, max_delay=15, initial_delay=3):
        """
        初始化自适应延迟控制器
        :param min_delay: 最小延迟
        :param max_delay: 最大延迟
        :param initial_delay: 初始延迟
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.current_delay = initial_delay
        self.success_count = 0
        self.fail_count = 0
        self.logger = logging.getLogger('AdaptiveDelay')
    
    def record_success(self):
        """记录成功请求"""
        self.success_count += 1
        self.fail_count = 0
        
        # 连续成功时适当降低延迟
        if self.success_count >= 5:
            self.current_delay = max(self.min_delay, self.current_delay * 0.9)
            self.success_count = 0
            self.logger.debug(f'延迟降低至: {self.current_delay:.2f}秒')
    
    def record_failure(self):
        """记录失败请求"""
        self.fail_count += 1
        self.success_count = 0
        
        # 失败时增加延迟
        self.current_delay = min(self.max_delay, self.current_delay * 1.5)
        self.logger.debug(f'延迟增加至: {self.current_delay:.2f}秒')
    
    def sleep(self):
        """执行延迟"""
        # 添加随机波动
        delay = self.current_delay * random.uniform(0.8, 1.2)
        delay = max(self.min_delay, min(self.max_delay, delay))
        self.logger.debug(f'自适应延迟: {delay:.2f}秒')
        time.sleep(delay)
