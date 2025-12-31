# -*- coding: utf-8 -*-
"""
社交媒体数据采集模块 - 抖音 & 小红书统一数据接口
输出标准化 JSON 数据，供飞书多维表格等后续分析使用
"""
from .data_models import VideoStats, TrendPoint, CollectResult
from .collector import StatsCollector

__all__ = ['VideoStats', 'TrendPoint', 'CollectResult', 'StatsCollector']
__version__ = '1.0.0'
