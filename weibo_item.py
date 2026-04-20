# -*- coding: utf-8 -*-
"""
微博数据模型
定义微博数据的字段结构
"""


class WeiboItem:
    """
    微博数据项类
    用于存储单条微博的所有字段信息
    """
    
    def __init__(self):
        # 微博ID
        self.id = ''
        # 微博bid
        self.bid = ''
        # 用户ID
        self.user_id = ''
        # 用户昵称
        self.screen_name = ''
        # 微博正文
        self.text = ''
        # 头条文章url
        self.article_url = ''
        # 发布位置
        self.location = ''
        # 艾特用户
        self.at_users = ''
        # 话题
        self.topics = ''
        # 转发数
        self.reposts_count = '0'
        # 评论数
        self.comments_count = '0'
        # 点赞数
        self.attitudes_count = '0'
        # 发布时间
        self.created_at = ''
        # 发布工具
        self.source = ''
        # 微博图片url列表
        self.pics = []
        # 微博视频url
        self.video_url = ''
        # 转发微博ID
        self.retweet_id = ''
        # IP属地
        self.ip = ''
        # 用户认证类型
        self.user_authentication = ''
        # 会员类型
        self.vip_type = ''
        # 会员等级
        self.vip_level = 0
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'bid': self.bid,
            'user_id': self.user_id,
            'screen_name': self.screen_name,
            'text': self.text,
            'article_url': self.article_url,
            'location': self.location,
            'at_users': self.at_users,
            'topics': self.topics,
            'reposts_count': self.reposts_count,
            'comments_count': self.comments_count,
            'attitudes_count': self.attitudes_count,
            'created_at': self.created_at,
            'source': self.source,
            'pics': self.pics,
            'video_url': self.video_url,
            'retweet_id': self.retweet_id,
            'ip': self.ip,
            'user_authentication': self.user_authentication,
            'vip_type': self.vip_type,
            'vip_level': self.vip_level
        }
    
    def to_csv_row(self):
        """
        转换为CSV行数据
        返回列表格式，与表头对应
        """
        return [
            self.id,
            self.bid,
            self.user_id,
            self.screen_name,
            self.text,
            self.article_url,
            self.location,
            self.at_users,
            self.topics,
            self.reposts_count,
            self.comments_count,
            self.attitudes_count,
            self.created_at,
            self.source,
            ','.join(self.pics) if self.pics else '',
            self.video_url,
            self.retweet_id,
            self.ip,
            self.user_authentication,
            self.vip_type,
            self.vip_level
        ]
    
    @staticmethod
    def get_csv_header():
        """获取CSV表头"""
        return [
            'id', 'bid', 'user_id', '用户昵称', '微博正文', '头条文章url',
            '发布位置', '艾特用户', '话题', '转发数', '评论数', '点赞数', '发布时间',
            '发布工具', '微博图片url', '微博视频url', 'retweet_id', 'ip', 'user_authentication',
            '会员类型', '会员等级'
        ]
    
    def __repr__(self):
        return f"<WeiboItem id={self.id} user={self.screen_name} text={self.text[:30]}...>"
