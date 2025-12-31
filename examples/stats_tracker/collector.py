# -*- coding: utf-8 -*-
"""
统一数据采集器
直接调用即可返回：
- 大盘数据（账号概览）
- 视频/笔记列表
- 每日播放趋势（抖音）
- 新视频每小时播放曲线（24h内，抖音）
"""
import asyncio

from .douyin_tracker import DouyinTracker
from .xhs_tracker import XiaohongshuTracker
from .data_models import CollectResult


class StatsCollector:
    @staticmethod
    async def collect(platform: str, with_trends: bool = True) -> CollectResult:
        """
        采集指定平台的所有数据
        
        Args:
            platform: "douyin" 或 "xiaohongshu" / "xhs"
            with_trends: 是否获取趋势数据（仅抖音支持）
        
        Returns:
            CollectResult 包含：
            - account_stats: 大盘数据
            - videos: 视频/笔记列表，每个视频包含 daily_trend 和 hourly_trend
        """
        p = (platform or "").lower()
        if p == "douyin":
            tracker = DouyinTracker()
            return await tracker.fetch_all(with_trends=with_trends)
        if p in ("xiaohongshu", "xhs"):
            tracker = XiaohongshuTracker()
            return await tracker.fetch_all()
        raise ValueError(f"unsupported platform: {platform}")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="数据采集器")
    parser.add_argument("--platform", required=True, choices=["douyin", "xiaohongshu", "xhs"])
    parser.add_argument("--out", default="-")
    parser.add_argument("--no-trends", action="store_true", help="不获取趋势数据")
    args = parser.parse_args()

    result = await StatsCollector.collect(args.platform, with_trends=not args.no_trends)
    payload = result.to_json(indent=2)
    if args.out == "-":
        print(payload)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload)
        print(f"saved -> {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
