# -*- coding: utf-8 -*-
"""
探索抖音单个视频详情页的 API，查找时间维度数据 (24H/7D/30D)
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright
from conf import LOCAL_CHROME_PATH

COOKIE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                           "cookies", "douyin_uploader", "account.json")


async def explore_douyin_video_detail():
    """探索抖音单视频详情 API"""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=False,
            executable_path=LOCAL_CHROME_PATH if LOCAL_CHROME_PATH else None
        )
        
        context = await browser.new_context(storage_state=COOKIE_FILE)
        page = await context.new_page()
        
        all_responses = []
        video_ids = []
        
        async def handle_response(response):
            url = response.url
            content_type = response.headers.get("content-type", "")
            
            if "application/json" not in content_type:
                return
            
            if "douyin.com" not in url:
                return
                
            try:
                data = await response.json()
                all_responses.append({"url": url, "data": data})
                print(f"[+] 捕获: {url[:80]}...")
                
                # 提取视频ID
                if "item_analysis/item_performance" in url or "item/list" in url:
                    items = data.get("items", [])
                    for item in items:
                        vid = item.get("item_id") or item.get("id")
                        if vid and vid not in video_ids:
                            video_ids.append(vid)
                
                # 检查是否包含时间维度数据
                data_str = json.dumps(data)
                if any(k in data_str.lower() for k in ["trend", "daily", "hourly", "24h", "7d", "30d"]):
                    print(f"    ★ 可能包含时间维度数据!")
                        
            except Exception as e:
                pass
        
        page.on("response", handle_response)
        
        # 1. 访问数据中心 - 作品分析页面
        print("[+] 访问抖音作品分析页面...")
        await page.goto("https://creator.douyin.com/creator-micro/data/stats/video")
        await asyncio.sleep(5)
        
        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except:
            pass
        
        await page.screenshot(path="examples/douyin_stats_video.png", full_page=True)
        print("[+] 截图已保存: douyin_stats_video.png")
        
        await asyncio.sleep(3)
        
        # 2. 尝试点击某个视频查看详情
        print("[+] 尝试点击视频查看详情...")
        try:
            # 尝试找到视频列表中的行
            rows = page.locator('tr').all()
            for row in await rows:
                text = await row.text_content()
                if text and len(text) > 10:  # 跳过表头
                    await row.click()
                    print("[+] 已点击视频行")
                    await asyncio.sleep(5)
                    await page.screenshot(path="examples/douyin_video_detail.png", full_page=True)
                    print("[+] 点击后截图: douyin_video_detail.png")
                    break
        except Exception as e:
            print(f"[-] 点击失败: {e}")
        
        # 3. 如果获取到了视频ID，尝试直接访问详情页面
        if video_ids:
            print(f"[+] 获取到 {len(video_ids)} 个视频ID，尝试访问详情页面...")
            vid = video_ids[0]
            
            detail_urls = [
                f"https://creator.douyin.com/creator-micro/data/stats/video/{vid}",
                f"https://creator.douyin.com/creator-micro/data/item/{vid}",
                f"https://creator.douyin.com/creator-micro/content/item/detail/{vid}",
            ]
            
            for url in detail_urls:
                print(f"[+] 尝试访问: {url[:70]}...")
                await page.goto(url)
                await asyncio.sleep(5)
                
                # 检查是否跳转回主页
                current_url = page.url
                if vid in current_url:
                    await page.screenshot(path="examples/douyin_video_direct.png", full_page=True)
                    print(f"[+] 访问成功! 当前URL: {current_url[:70]}")
                    break
        
        # 4. 访问单视频诊断页面（如果存在）
        print("[+] 尝试访问单视频诊断页面...")
        try:
            await page.goto("https://creator.douyin.com/creator-micro/data/stats/video")
            await asyncio.sleep(3)
            
            # 查找"查看详情"或"数据分析"按钮
            for text in ["查看详情", "数据分析", "诊断", "分析"]:
                btn = page.locator(f'text={text}').first
                if await btn.count():
                    print(f"[+] 找到 '{text}' 按钮，点击它")
                    await btn.click()
                    await asyncio.sleep(5)
                    await page.screenshot(path=f"examples/douyin_{text}.png", full_page=True)
                    break
        except Exception as e:
            print(f"[-] 访问诊断页面失败: {e}")
        
        # 保存所有捕获的 API
        output_file = "examples/douyin_video_detail_api_explore.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_responses, f, ensure_ascii=False, indent=2)
        print(f"[+] API 响应已保存到: {output_file}")
        
        print(f"\n[+] 共捕获 {len(all_responses)} 个 API")
        print(f"[+] 发现 {len(video_ids)} 个视频ID: {video_ids[:3]}...")
        
        # 分析有用的API
        print("\n" + "="*60)
        print("可能包含时间维度数据的 API:")
        print("="*60)
        for resp in all_responses:
            url = resp["url"]
            data_str = json.dumps(resp["data"])
            if any(k in data_str.lower() for k in ["trend", "daily", "hourly", "24", "7d", "30d", "day_data"]):
                print(f"\n★ {url[:80]}")
                if isinstance(resp["data"], dict):
                    print(f"  Keys: {list(resp['data'].keys())[:10]}")
        
        input("\n按 Enter 键关闭浏览器...")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(explore_douyin_video_detail())
