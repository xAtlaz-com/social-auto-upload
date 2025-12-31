# -*- coding: utf-8 -*-
"""
Douyin tracker - 抖音数据采集
- 大盘数据（账号整体数据）
- 视频列表 + 每日播放趋势
- 新视频（24h内）每小时播放曲线
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from playwright.async_api import async_playwright, Page

# Allow running as a module or script
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from examples.stats_tracker.data_models import VideoStats, TrendPoint, CollectResult  # noqa: E402
from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS  # noqa: E402

COOKIE_FILE = os.path.join(PROJECT_ROOT, "cookies", "douyin_uploader", "account.json")


class DouyinTracker:
    def __init__(self, headless: bool | None = None):
        self.headless = LOCAL_CHROME_HEADLESS if headless is None else headless

    async def fetch_all(self, with_trends: bool = True) -> CollectResult:
        """
        获取所有数据：
        1. 大盘数据（账号概览）
        2. 视频列表基础数据
        3. 每个视频的每日播放趋势
        4. 新视频（24h内）的每小时播放曲线
        
        Args:
            with_trends: 是否获取趋势数据（会增加采集时间）
        """
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=self.headless,
                executable_path=LOCAL_CHROME_PATH if LOCAL_CHROME_PATH else None,
            )
            context = await browser.new_context(storage_state=COOKIE_FILE)
            page = await context.new_page()

            video_list: List[Dict[str, Any]] = []
            account_stats: Dict[str, Any] = {}
            
            # 用于存储趋势数据 {video_id: {"hourly": [...], "daily": [...]}}
            trends_data: Dict[str, Dict[str, List]] = {}

            async def handle_response(response):
                url = response.url
                ct = response.headers.get("content-type", "")
                if "application/json" not in ct:
                    return
                try:
                    data = await response.json()
                    
                    # 1. 捕获大盘数据（账号概览）
                    if "item_analysis/overview" in url:
                        account_stats.update({
                            "avg_like_per_video": data.get("average_like_count_per_video", {}).get("metric_value", 0),
                            "avg_comment_per_video": data.get("average_comment_count_per_video", {}).get("metric_value", 0),
                            "avg_share_per_video": data.get("average_share_count_per_video", {}).get("metric_value", 0),
                            "avg_play_per_video": data.get("average_play_count_per_video", {}).get("metric_value", 0),
                            "total_play": data.get("total_play_count", {}).get("metric_value", 0),
                            "total_like": data.get("total_like_count", {}).get("metric_value", 0),
                            "total_comment": data.get("total_comment_count", {}).get("metric_value", 0),
                            "total_share": data.get("total_share_count", {}).get("metric_value", 0),
                        })
                    
                    # 2. 捕获作者概览数据（粉丝数等）
                    if "author/overview" in url or "user/info" in url:
                        follower = data.get("follower_count") or data.get("fans_count", 0)
                        if follower:
                            account_stats["follower_count"] = int(follower)
                    
                    # 3. 捕获视频列表
                    if "item_analysis/item_performance" in url:
                        for item in data.get("items", []) or []:
                            vid = str(item.get("item_id") or "")
                            if not vid:
                                continue
                            video_list.append({
                                "item_id": vid,
                                "title": item.get("title", ""),
                                "play_count": int(item.get("play_count", 0) or 0),
                                "like_count": int(item.get("like_count", 0) or 0),
                                "comment_count": int(item.get("comment_count", 0) or 0),
                                "share_count": int(item.get("share_count", 0) or 0),
                                "publish_time": item.get("publish_time", ""),
                                "average_play_duration": float(item.get("average_play_duration", 0) or 0.0),
                                "bounce_rate_2s": float(item.get("bounce_rate_2s", 0) or 0.0),
                                "completion_rate_5s": float(item.get("completion_rate_5s", 0) or 0.0),
                                "new_fans": int(item.get("subscribe_count", 0) or 0),
                                "cover": (item.get("cover", {}) or {}).get("url_list", [""])[0] if item.get("cover") else "",
                            })
                    
                    # 4. 捕获趋势数据 (metrics_trend)
                    if "metrics_trend" in url:
                        trend_map = data.get("trend_map", {}) or {}
                        view_count_data = trend_map.get("view_count", {}).get("0", [])
                        if view_count_data:
                            # 从URL提取video_id
                            # URL格式: ...metrics_trend?item_id=xxx&...
                            import re
                            match = re.search(r'item_id=([^&]+)', url)
                            if match:
                                vid = match.group(1)
                                if vid not in trends_data:
                                    trends_data[vid] = {"hourly": [], "daily": []}
                                
                                # 判断是小时数据还是天数据（通过数据点的时间间隔判断）
                                if len(view_count_data) >= 2:
                                    dt1 = view_count_data[0].get("date_time", "")
                                    dt2 = view_count_data[1].get("date_time", "")
                                    # 如果包含小时信息（如 2025-01-01 01:00:00）
                                    if " " in dt1 and ":" in dt1:
                                        trends_data[vid]["hourly"] = view_count_data
                                    else:
                                        trends_data[vid]["daily"] = view_count_data
                                else:
                                    # 单个点，按日数据处理
                                    trends_data[vid]["daily"] = view_count_data
                                    
                except Exception:
                    pass

            page.on("response", handle_response)

            # Step 1: 访问数据中心获取基础数据
            await page.goto("https://creator.douyin.com/creator-micro/data/stats/video")
            try:
                await page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:
                pass
            await asyncio.sleep(2)
            
            # Step 2: 如果需要趋势数据，逐个获取每个视频的趋势
            if with_trends and video_list:
                now = datetime.now()
                for v in video_list:
                    vid = v["item_id"]
                    publish_time_str = v.get("publish_time", "")
                    
                    # 判断是否为新视频（24h内）
                    is_new_video = False
                    if publish_time_str:
                        try:
                            # 格式: 2025-01-01 10:00:00 或 2025-01-01
                            if " " in publish_time_str:
                                pub_time = datetime.strptime(publish_time_str, "%Y-%m-%d %H:%M:%S")
                            else:
                                pub_time = datetime.strptime(publish_time_str, "%Y-%m-%d")
                            is_new_video = (now - pub_time) < timedelta(hours=24)
                        except:
                            pass
                    
                    # 访问视频详情页获取趋势
                    await self._fetch_video_trend(page, vid, is_new_video)
                    await asyncio.sleep(1)  # 避免请求过快

            await context.storage_state(path=COOKIE_FILE)
            await browser.close()

            # 构建结果
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            results: List[VideoStats] = []
            
            for v in video_list:
                vid = v["item_id"]
                trend_info = trends_data.get(vid, {})
                
                # 转换趋势数据
                hourly_trend = [
                    TrendPoint(date_time=p.get("date_time", ""), value=int(float(p.get("value", 0) or 0)))
                    for p in trend_info.get("hourly", [])
                ]
                daily_trend = [
                    TrendPoint(date_time=p.get("date_time", ""), value=int(float(p.get("value", 0) or 0)))
                    for p in trend_info.get("daily", [])
                ]
                
                # 如果有小时数据但没有日数据，按日聚合
                if hourly_trend and not daily_trend:
                    daily_acc: Dict[str, int] = {}
                    for hp in hourly_trend:
                        day = hp.date_time[:10] if hp.date_time else ""
                        if day:
                            daily_acc[day] = daily_acc.get(day, 0) + hp.value
                    daily_trend = [TrendPoint(date_time=d, value=val) for d, val in sorted(daily_acc.items())]
                
                stats = VideoStats(
                    platform="douyin",
                    video_id=vid,
                    title=v["title"],
                    publish_time=v["publish_time"],
                    collect_time=now_str,
                    cover_url=v["cover"],
                    play_count=v["play_count"],
                    like_count=v["like_count"],
                    comment_count=v["comment_count"],
                    share_count=v["share_count"],
                    avg_play_duration=v["average_play_duration"],
                    completion_rate_5s=v["completion_rate_5s"],
                    bounce_rate_2s=v["bounce_rate_2s"],
                    new_fans=v["new_fans"],
                    daily_trend=daily_trend,
                    hourly_trend=hourly_trend,
                )
                results.append(stats)

            ok = len(results) > 0
            return CollectResult(
                platform="douyin",
                collect_time=now_str,
                success=ok,
                message="ok" if ok else "no data",
                videos=results,
                account_stats=account_stats,
            )

    async def _fetch_video_trend(self, page: Page, video_id: str, fetch_hourly: bool = False):
        """
        获取单个视频的趋势数据
        
        Args:
            page: Playwright page
            video_id: 视频ID
            fetch_hourly: 是否获取小时级数据（新视频）
        """
        # 访问视频详情页
        detail_url = f"https://creator.douyin.com/creator-micro/work-management/work-detail/{video_id}"
        await page.goto(detail_url)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except:
            pass
        
        # 点击"分析"按钮触发趋势API
        try:
            analysis_btn = page.locator('text=分析').first
            if await analysis_btn.count():
                await analysis_btn.click()
                await asyncio.sleep(2)
                
                # 如果需要小时数据，尝试切换到小时视图
                if fetch_hourly:
                    # 尝试点击"按小时"或"24小时"按钮
                    for text in ["按小时", "小时", "24小时", "24H"]:
                        btn = page.locator(f'text={text}').first
                        if await btn.count():
                            await btn.click()
                            await asyncio.sleep(2)
                            break
        except:
            pass


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="抖音数据采集")
    parser.add_argument("--out", default="-", help="输出文件路径，'-' 表示 stdout")
    parser.add_argument("--no-trends", action="store_true", help="不获取趋势数据（更快）")
    args = parser.parse_args()

    tracker = DouyinTracker()
    result = await tracker.fetch_all(with_trends=not args.no_trends)
    payload = result.to_json(indent=2)

    if args.out == "-":
        print(payload)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload)
        print(f"saved -> {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
