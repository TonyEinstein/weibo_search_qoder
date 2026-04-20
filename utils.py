# -*- coding: utf-8 -*-
"""
工具函数模块
包含日期转换、URL构建、关键词处理等辅助函数
"""

import sys
import re
import os
import logging
from datetime import datetime, timedelta
from urllib.parse import unquote

from region import region_dict

# 初始化日志记录器
logger = logging.getLogger('WeiboUtils')


def convert_weibo_type(weibo_type):
    """
    将微博类型转换成URL参数字符串
    支持单个类型(int)或多个类型(list)，返回列表
    """
    type_map = {
        0: '&typeall=1',
        1: '&scope=ori',
        2: '&xsort=hot',
        3: '&atten=1',
        4: '&vip=1',
        5: '&category=4',
        6: '&viewpoint=1'
    }
    
    # 支持列表或多个类型
    if isinstance(weibo_type, (list, tuple)):
        return [type_map.get(t, '&typeall=1') for t in weibo_type]
    else:
        # 单个类型，包装成列表返回
        return [type_map.get(weibo_type, '&typeall=1')]


def convert_contain_type(contain_type):
    """将包含类型转换成URL参数字符串"""
    if contain_type == 0:
        return '&suball=1'
    elif contain_type == 1:
        return '&haspic=1'
    elif contain_type == 2:
        return '&hasvideo=1'
    elif contain_type == 3:
        return '&hasmusic=1'
    elif contain_type == 4:
        return '&haslink=1'
    return '&suball=1'


def get_keyword_list(keyword_config):
    """
    获取关键词列表
    支持列表类型或文件路径
    """
    if isinstance(keyword_config, list):
        return keyword_config
    
    # 从文件读取
    if not os.path.isabs(keyword_config):
        keyword_config = os.getcwd() + os.sep + keyword_config
    if not os.path.isfile(keyword_config):
        logger.error('不存在%s文件' % keyword_config)
        sys.exit(1)
    
    with open(keyword_config, 'rb') as f:
        try:
            lines = f.read().splitlines()
            lines = [line.decode('utf-8-sig') for line in lines]
        except UnicodeDecodeError:
            logger.error('%s文件应为utf-8编码，请先将文件编码转为utf-8再运行程序' % keyword_config)
            sys.exit(1)
    
    keyword_list = []
    for line in lines:
        if line:
            keyword_list.append(line)
    return keyword_list


def process_keywords(keyword_list):
    """
    处理关键词列表
    将话题格式 #话题# 转换为URL编码格式
    """
    processed = []
    for keyword in keyword_list:
        if len(keyword) > 2 and keyword[0] == '#' and keyword[-1] == '#':
            processed.append('%23' + keyword[1:-1] + '%23')
        else:
            processed.append(keyword)
    return processed


def get_regions(region_list):
    """
    根据区域筛选条件返回符合要求的region字典
    """
    if not region_list or '全部' in region_list:
        return region_dict
    
    new_region = {}
    for key in region_list:
        if region_dict.get(key):
            new_region[key] = region_dict[key]
    
    if not new_region:
        return region_dict
    return new_region


def standardize_date(created_at):
    """
    标准化微博发布时间
    将各种格式转换为标准格式：YYYY-MM-DD HH:MM
    """
    if not created_at:
        return ''
    
    try:
        if "刚刚" in created_at:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        elif "秒" in created_at:
            second = created_at[:created_at.find(u"秒")]
            second = timedelta(seconds=int(second))
            created_at = (datetime.now() - second).strftime("%Y-%m-%d %H:%M")
        elif "分钟" in created_at:
            minute = created_at[:created_at.find(u"分钟")]
            minute = timedelta(minutes=int(minute))
            created_at = (datetime.now() - minute).strftime("%Y-%m-%d %H:%M")
        elif "小时" in created_at:
            hour = created_at[:created_at.find(u"小时")]
            hour = timedelta(hours=int(hour))
            created_at = (datetime.now() - hour).strftime("%Y-%m-%d %H:%M")
        elif "今天" in created_at:
            today = datetime.now().strftime('%Y-%m-%d')
            created_at = today + ' ' + created_at[2:]
        elif '年' not in created_at:
            year = datetime.now().strftime("%Y")
            month = created_at[:2]
            day = created_at[3:5]
            time = created_at[6:]
            created_at = year + '-' + month + '-' + day + ' ' + time
        else:
            year = created_at[:4]
            month = created_at[5:7]
            day = created_at[8:10]
            time = created_at[11:]
            created_at = year + '-' + month + '-' + day + ' ' + time
    except (ValueError, IndexError, TypeError) as e:
        logger.warning(f'日期解析失败: {created_at}, 错误: {e}')
        return created_at  # 返回原始值
    
    return created_at


def str_to_time(text):
    """将字符串转换成时间类型"""
    return datetime.strptime(text, '%Y-%m-%d')


def validate_dates(start_date, end_date):
    """验证日期范围是否合法"""
    try:
        start = str_to_time(start_date)
        end = str_to_time(end_date)
    except ValueError as e:
        logger.error(f'日期格式错误，请使用 yyyy-mm-dd 格式: {e}')
        sys.exit(1)
    
    if start > end:
        logger.error('配置错误，START_DATE值应早于或等于END_DATE值，请重新配置')
        sys.exit(1)
    return True


def get_article_url(selector):
    """
    从选择器中获取微博头条文章url
    selector: lxml.etree._Element
    获取失败时返回空字符串，不影响其他字段解析
    """
    try:
        article_url = ''
        text = selector.xpath('string(.)')
        if text:
            text = text.replace('\u200b', '').replace('\ue627', '').replace('\n', '').replace(' ', '')
        
        if text and text.startswith('发布了头条文章'):
            urls = selector.xpath('.//a')
            for url in urls:
                wbicon = url.xpath('.//i[@class="wbicon"]/text()')
                if wbicon and wbicon[0] == 'O':
                    href = url.xpath('@href')
                    if href and href[0].startswith('http://t.cn'):
                        article_url = href[0]
                    break
        return article_url
    except Exception:
        # 获取文章URL失败时返回空字符串，不影响其他字段
        return ''


def get_location(selector):
    """
    从选择器中获取微博发布位置
    获取失败时返回空字符串，不影响其他字段解析
    """
    try:
        a_list = selector.xpath('.//a')
        location = ''
        for a in a_list:
            wbicon = a.xpath('./i[@class="wbicon"]/text()')
            if wbicon and wbicon[0] == '2':
                loc_text = a.xpath('string(.)')
                if loc_text:
                    location = loc_text[1:]
                break
        return location
    except Exception:
        # 获取位置失败时返回空字符串，不影响其他字段
        return ''


def get_at_users(selector):
    """
    从选择器中获取微博中@的用户昵称
    获取失败时返回空字符串，不影响其他字段解析
    """
    try:
        a_list = selector.xpath('.//a')
        at_list = []
        for a in a_list:
            href = a.xpath('@href')
            text = a.xpath('string(.)')
            if href and text:
                href_decoded = unquote(href[0])
                if len(href_decoded) > 14 and len(text) > 1:
                    if href_decoded[14:] == text[1:]:
                        at_user = text[1:]
                        if at_user not in at_list:
                            at_list.append(at_user)
        return ','.join(at_list) if at_list else ''
    except Exception:
        # 获取@用户失败时返回空字符串，不影响其他字段
        return ''


def get_topics(selector):
    """
    从选择器中获取参与的微博话题
    获取失败时返回空字符串，不影响其他字段解析
    """
    try:
        a_list = selector.xpath('.//a')
        topic_list = []
        for a in a_list:
            text = a.xpath('string(.)')
            if text and len(text) > 2 and text[0] == '#' and text[-1] == '#':
                topic = text[1:-1]
                if topic not in topic_list:
                    topic_list.append(topic)
        return ','.join(topic_list) if topic_list else ''
    except Exception:
        # 获取话题失败时返回空字符串，不影响其他字段
        return ''


def get_vip_info(selector):
    """
    从选择器中获取用户的VIP类型和等级信息
    返回: (vip_type, vip_level)
    获取失败时返回默认值，不影响其他字段解析
    """
    try:
        vip_type = "非会员"
        vip_level = 0
        
        vip_container = selector.xpath('.//div[@class="user_vip_icon_container"]')
        if vip_container:
            svvip_img = vip_container[0].xpath('.//img[contains(@src, "svvip_")]')
            if svvip_img:
                vip_type = "超级会员"
                src = svvip_img[0].xpath('@src')
                if src:
                    level_match = re.search(r'svvip_(\d+)\.png', src[0])
                    if level_match:
                        vip_level = int(level_match.group(1))
            else:
                vip_img = vip_container[0].xpath('.//img[contains(@src, "vip_")]')
                if vip_img:
                    vip_type = "会员"
                    src = vip_img[0].xpath('@src')
                    if src:
                        level_match = re.search(r'vip_(\d+)\.png', src[0])
                        if level_match:
                            vip_level = int(level_match.group(1))
        
        return vip_type, vip_level
    except Exception:
        # 获取VIP信息失败时返回默认值，不影响其他字段
        return "非会员", 0


def extract_number(text):
    """从文本中提取数字"""
    if not text:
        return '0'
    numbers = re.findall(r'\d+', str(text))
    return numbers[0] if numbers else '0'


def get_user_auth(avator_selector):
    """
    从头像选择器中获取用户认证类型
    获取失败时返回默认值，不影响其他字段解析
    """
    try:
        user_auth = '普通用户'
        if avator_selector:
            svg_id = avator_selector.xpath('.//svg/@id')
            if svg_id:
                auth_map = {
                    'woo_svg_vblue': '蓝V',
                    'woo_svg_vyellow': '黄V',
                    'woo_svg_vorange': '红V',
                    'woo_svg_vgold': '金V'
                }
                user_auth = auth_map.get(svg_id[0], '普通用户')
        return user_auth
    except Exception:
        # 获取用户认证信息失败时返回默认值，不影响其他字段
        return '普通用户'
