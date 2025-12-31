# -*- coding: utf-8 -*-
"""
抠音 & 小红书数据采集 CLI
直接运行即可获取：
- 大盘数据（账号概览）
- 视频/笔记列表
- 每日播放趋势（抖音）
- 新视频每小时播放曲线（24h内，抖音）

Examples:
  python -m examples.stats_tracker.cli --platform douyin
  python -m examples.stats_tracker.cli --platform douyin --no-trends  # 快速模式
  python -m examples.stats_tracker.cli --platform xhs --out out.json
"""
import asyncio
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from examples.stats_tracker.collector import StatsCollector  # noqa: E402


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="抖音 & 小红书数据采集")
    parser.add_argument("--platform", required=True, choices=["douyin", "xiaohongshu", "xhs"])
    parser.add_argument("--out", default="-", help="输出文件路径，'-' 表示 stdout")
    parser.add_argument("--no-trends", action="store_true", help="不获取趋势数据（更快，仅抖音）")
    args = parser.parse_args()

    res = await StatsCollector.collect(args.platform, with_trends=not args.no_trends)
    payload = res.to_json(indent=2)

    if args.out == "-":
        print(payload)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload)
        print(f"saved -> {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
