# -*- coding: utf-8 -*-
"""
统一数据模型定义
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
import json


@dataclass
class TrendPoint:
    """时间趋势数据点"""
    date_time: str       # 时间点 (格式: YYYY-MM-DD HH:00:00 或 YYYY-MM-DD)
    value: int           # 数值
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VideoStats:
    """视频/笔记统计数据"""
    # 基础信息
    platform: str              # 平台: douyin / xiaohongshu
    video_id: str              # 视频/笔记 ID
    title: str                 # 标题
    publish_time: str          # 发布时间
    collect_time: str          # 采集时间
    cover_url: str = ""        # 封面图URL
    
    # 核心指标
    play_count: int = 0        # 播放量 (抖音)
    imp_count: int = 0         # 曝光量 (小红书)
    view_count: int = 0        # 观看量 (小红书)
    like_count: int = 0        # 点赞数
    comment_count: int = 0     # 评论数
    collect_count: int = 0     # 收藏数 (小红书)
    share_count: int = 0       # 分享数
    
    # 抖音特有指标
    avg_play_duration: float = 0.0    # 平均播放时长(秒)
    completion_rate_5s: float = 0.0   # 5秒完播率
    bounce_rate_2s: float = 0.0       # 2秒跳出率
    new_fans: int = 0                 # 新增粉丝
    
    # 小红书特有指标
    click_rate: float = 0.0           # 封面点击率
    avg_view_time: int = 0            # 平均观看时长(秒)
    
    # 时间趋势数据 (仅抖音支持)
    daily_trend: List[TrendPoint] = field(default_factory=list)    # 每日趋势
    hourly_trend: List[TrendPoint] = field(default_factory=list)   # 每小时趋势
    
    def to_dict(self) -> dict:
        """转换为字典，方便 JSON 序列化"""
        data = asdict(self)
        data['daily_trend'] = [t if isinstance(t, dict) else asdict(t) for t in self.daily_trend]
        data['hourly_trend'] = [t if isinstance(t, dict) else asdict(t) for t in self.hourly_trend]
        return data
    
    def get_summary(self) -> dict:
        """获取摘要数据（不含趋势详情）"""
        return {
            'platform': self.platform,
            'video_id': self.video_id,
            'title': self.title,
            'publish_time': self.publish_time,
            'collect_time': self.collect_time,
            'play_count': self.play_count,
            'imp_count': self.imp_count,
            'view_count': self.view_count,
            'like_count': self.like_count,
            'comment_count': self.comment_count,
            'collect_count': self.collect_count,
            'share_count': self.share_count,
        }
    
    def get_trend_summary(self) -> dict:
        """获取趋势汇总"""
        daily_total = sum(t.value if isinstance(t, TrendPoint) else t.get('value', 0) for t in self.daily_trend)
        hourly_total = sum(t.value if isinstance(t, TrendPoint) else t.get('value', 0) for t in self.hourly_trend)
        
        return {
            'daily_points': len(self.daily_trend),
            'daily_total': daily_total,
            'hourly_points': len(self.hourly_trend),
            'hourly_total': hourly_total,
        }


@dataclass  
class CollectResult:
    """采集结果"""
    platform: str                      # 平台
    collect_time: str                  # 采集时间
    success: bool                      # 是否成功
    message: str = ""                  # 消息
    videos: List[VideoStats] = field(default_factory=list)  # 视频列表
    
    # 账号概览数据 (小红书)
    account_stats: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            'platform': self.platform,
            'collect_time': self.collect_time,
            'success': self.success,
            'message': self.message,
            'video_count': len(self.videos),
            'videos': [v.to_dict() for v in self.videos],
            'account_stats': self.account_stats,
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
    
    def save(self, filepath: str):
        """保存到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
    
    def get_flat_records(self) -> List[dict]:
        """
        获取扁平化记录列表，方便导入飞书多维表格
        每条视频一行，包含所有基础指标
        """
        records = []
        for video in self.videos:
            record = {
                'platform': video.platform,
                'video_id': video.video_id,
                'title': video.title,
                'publish_time': video.publish_time,
                'collect_time': video.collect_time,
                'play_count': video.play_count,
                'imp_count': video.imp_count,
                'view_count': video.view_count,
                'like_count': video.like_count,
                'comment_count': video.comment_count,
                'collect_count': video.collect_count,
                'share_count': video.share_count,
                'avg_play_duration': video.avg_play_duration,
                'completion_rate_5s': video.completion_rate_5s,
                'click_rate': video.click_rate,
                'new_fans': video.new_fans,
            }
            records.append(record)
        return records
    
    def get_trend_records(self) -> List[dict]:
        """
        获取趋势数据记录列表，方便导入飞书多维表格
        每个趋势点一行
        """
        records = []
        for video in self.videos:
            # 每日趋势
            for point in video.daily_trend:
                p = point if isinstance(point, dict) else point.to_dict()
                records.append({
                    'platform': video.platform,
                    'video_id': video.video_id,
                    'title': video.title,
                    'trend_type': 'daily',
                    'date_time': p['date_time'],
                    'value': p['value'],
                    'collect_time': video.collect_time,
                })
            # 每小时趋势  
            for point in video.hourly_trend:
                p = point if isinstance(point, dict) else point.to_dict()
                records.append({
                    'platform': video.platform,
                    'video_id': video.video_id,
                    'title': video.title,
                    'trend_type': 'hourly',
                    'date_time': p['date_time'],
                    'value': p['value'],
                    'collect_time': video.collect_time,
                })
        return records
