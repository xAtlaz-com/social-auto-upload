# -*- coding: utf-8 -*-
"""
Xiaohongshu tracker - 小红书数据采集
- 大盘数据（账号整体数据）
- 笔记列表数据
"""
import asyncio
import os
import sys
from datetime import datetime
from typing import Dict, Any, List

from playwright.async_api import async_playwright

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from examples.stats_tracker.data_models import VideoStats, TrendPoint, CollectResult  # noqa: E402
from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS  # noqa: E402
from utils.base_social_media import set_init_script  # noqa: E402

COOKIE_FILE = os.path.join(PROJECT_ROOT, "cookies", "xiaohongshu_uploader", "account.json")


class XiaohongshuTracker:
    def __init__(self, headless: bool | None = None):
        self.headless = LOCAL_CHROME_HEADLESS if headless is None else headless

    async def fetch_all(self) -> CollectResult:
        """
        获取所有数据：
        1. 大盘数据（账号概览）
        2. 笔记列表基础数据
        """
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=self.headless,
                executable_path=LOCAL_CHROME_PATH if LOCAL_CHROME_PATH else None,
            )
            context = await browser.new_context(storage_state=COOKIE_FILE)
            context = await set_init_script(context)
            page = await context.new_page()

            note_list: List[Dict[str, Any]] = []
            account_stats: Dict[str, Any] = {}

            async def handle_response(response):
                url = response.url
                ct = response.headers.get("content-type", "")
                if ("json" not in ct and "text" not in ct) or "xiaohongshu.com" not in url:
                    return
                try:
                    data = await response.json()
                    
                    # 1. 捕获大盘数据（账号概览）
                    if "datacenter/home" in url or "account/overview" in url or "creator/home" in url:
                        d = data.get("data", {}) or {}
                        # 尝试提取各种大盘指标
                        if d.get("fans_count") is not None:
                            account_stats["follower_count"] = int(d.get("fans_count", 0) or 0)
                        if d.get("total_note_count") is not None:
                            account_stats["total_note_count"] = int(d.get("total_note_count", 0) or 0)
                        if d.get("total_read_count") is not None:
                            account_stats["total_view"] = int(d.get("total_read_count", 0) or 0)
                        if d.get("total_imp_count") is not None:
                            account_stats["total_imp"] = int(d.get("total_imp_count", 0) or 0)
                        if d.get("total_interact_count") is not None:
                            account_stats["total_interact"] = int(d.get("total_interact_count", 0) or 0)
                    
                    # 2. 捕获账号粉丝数据
                    if "user/info" in url or "creator/info" in url:
                        d = data.get("data", {}) or {}
                        if d.get("fans") is not None:
                            account_stats["follower_count"] = int(d.get("fans", 0) or 0)
                        if d.get("follows") is not None:
                            account_stats["following_count"] = int(d.get("follows", 0) or 0)
                    
                    # 3. 捕获数据概览
                    if "datacenter/overview" in url:
                        d = data.get("data", {}) or {}
                        for k, v in d.items():
                            if isinstance(v, (int, float)):
                                account_stats[k] = v
                    
                    # 4. 捕获笔记列表
                    if "note/analyze/list" in url:
                        notes = data.get("data", {}).get("note_infos", []) or []
                        note_list.extend(notes)
                except Exception:
                    pass

            page.on("response", handle_response)

            # 访问创作中心
            await page.goto("https://creator.xiaohongshu.com/publish/publish")
            try:
                await page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:
                pass

            # 点击 "内容分析"
            try:
                content_btn = page.locator('text=内容分析').first
                if await content_btn.count():
                    await content_btn.click()
                    await asyncio.sleep(3)
            except Exception:
                pass

            await asyncio.sleep(2)
            await context.storage_state(path=COOKIE_FILE)
            await browser.close()

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            results: List[VideoStats] = []
            for n in note_list:
                vid = str(n.get("id") or "")
                if not vid:
                    continue
                title = n.get("title", "")
                publish_time = n.get("post_time", "") or n.get("publish_time", "")
                cover = (n.get("cover", {}) or {}).get("url", "") if isinstance(n.get("cover"), dict) else ""
                imp = int(n.get("imp_count", 0) or 0)
                view = int(n.get("read_count", 0) or 0)
                like = int(n.get("like_count", 0) or 0)
                comment = int(n.get("comment_count", 0) or 0)
                fav = int(n.get("fav_count", 0) or 0)
                share = int(n.get("share_count", 0) or 0)
                click_rate = float(n.get("coverClickRate", 0) or 0.0)

                stats = VideoStats(
                    platform="xiaohongshu",
                    video_id=vid,
                    title=title,
                    publish_time=publish_time,
                    collect_time=now_str,
                    cover_url=cover,
                    imp_count=imp,
                    view_count=view,
                    like_count=like,
                    comment_count=comment,
                    collect_count=fav,
                    share_count=share,
                    click_rate=click_rate,
                )
                results.append(stats)

            ok = len(results) > 0
            return CollectResult(
                platform="xiaohongshu",
                collect_time=now_str,
                success=ok,
                message="ok" if ok else "no data",
                videos=results,
                account_stats=account_stats,
            )


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="获取所有笔记数据")
    parser.add_argument("--out", default="-", help="输出文件路径，'-' 表示 stdout")
    args = parser.parse_args()

    tracker = XiaohongshuTracker()
    result = await tracker.fetch_all()
    payload = result.to_json(indent=2)

    if args.out == "-":
        print(payload)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload)
        print(f"saved -> {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
