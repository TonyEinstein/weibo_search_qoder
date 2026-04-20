# -*- coding: utf-8 -*-
"""
User-Agent 随机生成器
使用 fake-useragent 库生成真实的随机 User-Agent
"""

import logging
import random

# 初始化日志
logger = logging.getLogger('UserAgent')

# 内置 User-Agent 列表（备用）
_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
]

# 尝试导入 fake-useragent
try:
    from fake_useragent import UserAgent
    _ua = UserAgent(fallback='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    _FAKE_UA_AVAILABLE = True
    logger.info('fake-useragent 加载成功')
except Exception as e:
    _FAKE_UA_AVAILABLE = False
    logger.warning(f'fake-useragent 加载失败: {e}，将使用内置 User-Agent 列表')


def get_random_user_agent():
    """
    获取随机 User-Agent
    优先使用 fake-useragent，如果未安装则使用内置列表
    
    :return: 随机选择的 User-Agent 字符串
    """
    if _FAKE_UA_AVAILABLE:
        try:
            return _ua.random
        except Exception as e:
            logger.warning(f'fake-useragent 获取失败: {e}，使用备用列表')
            return random.choice(_USER_AGENTS)
    else:
        return random.choice(_USER_AGENTS)


def get_user_agent_list():
    """
    获取 User-Agent 列表
    
    :return: User-Agent 列表
    """
    if _FAKE_UA_AVAILABLE:
        # fake-useragent 不支持获取完整列表，返回空列表
        return []
    else:
        return _USER_AGENTS.copy()


def is_fake_ua_available():
    """
    检查 fake-useragent 是否可用
    
    :return: True 如果 fake-useragent 可用，否则 False
    """
    return _FAKE_UA_AVAILABLE
