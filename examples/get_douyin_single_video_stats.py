# -*- coding: utf-8 -*-
"""
获取抖音单个视频的详细数据（24小时、7天、30天趋势）
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from urllib.parse import urlencode

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright
from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS

COOKIE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                           "cookies", "douyin_uploader", "account.json")

# 设置为 True 以查看浏览器操作
DEBUG_MODE = False


async def get_video_list(page) -> list:
    """获取视频列表"""
    videos = []
    
    async def handle_response(response):
        url = response.url
        if "item_analysis/item_performance" in url:
            try:
                data = await response.json()
                items = data.get("items", [])
                for item in items:
                    videos.append({
                        "item_id": item.get("item_id"),
                        "title": item.get("title", ""),
                        "play_count": item.get("play_count", 0),
                        "publish_time": item.get("publish_time", ""),
                    })
            except:
                pass
    
    page.on("response", handle_response)
    
    await page.goto("https://creator.douyin.com/creator-micro/data/stats/video")
    await asyncio.sleep(5)
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except:
        pass
    
    return videos


async def get_single_video_trend(page, item_id: str, time_unit: int = 2) -> dict:
    """
    获取单个视频的时间趋势数据
    
    Args:
        page: Playwright page对象
        item_id: 视频ID
        time_unit: 时间单位 (1=天, 2=小时)
    
    Returns:
        趋势数据字典
    """
    trend_data = {}
    
    async def handle_trend_response(response):
        url = response.url
        if "metrics_trend" in url and item_id in url:
            try:
                data = await response.json()
                trend_map = data.get("trend_map", {})
                for metric_name, metric_data in trend_map.items():
                    if "0" in metric_data:
                        trend_data[metric_name] = metric_data["0"]
            except:
                pass
    
    page.on("response", handle_trend_response)
    
    # 访问单视频详情页面
    detail_url = f"https://creator.douyin.com/creator-micro/work-management/work-detail/{item_id}"
    await page.goto(detail_url)
    await asyncio.sleep(3)
    
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except:
        pass
    
    # 点击"分析"按钮触发数据加载
    try:
        analysis_btn = page.locator('text=分析').first
        if await analysis_btn.count():
            await analysis_btn.click()
            await asyncio.sleep(5)
    except:
        pass
    
    return trend_data


async def get_single_video_stats(video_id: str = None):
    """
    获取单个视频的完整统计数据
    
    Args:
        video_id: 视频ID，如果不提供则显示视频列表供选择
    """
    async with async_playwright() as playwright:
        headless = False if DEBUG_MODE else LOCAL_CHROME_HEADLESS
        browser = await playwright.chromium.launch(
            headless=headless,
            executable_path=LOCAL_CHROME_PATH if LOCAL_CHROME_PATH else None
        )
        
        context = await browser.new_context(storage_state=COOKIE_FILE)
        page = await context.new_page()
        
        # 存储捕获的数据
        video_detail = {}
        trend_data = {}
        
        async def handle_response(response):
            url = response.url
            content_type = response.headers.get("content-type", "")
            
            if "application/json" not in content_type:
                return
            
            try:
                data = await response.json()
                
                # 捕获视频性能数据
                if "item_analysis/item_performance" in url:
                    items = data.get("items", [])
                    for item in items:
                        vid = item.get("item_id")
                        if vid and (video_id is None or str(vid) == str(video_id)):
                            video_detail[vid] = {
                                "item_id": vid,
                                "title": item.get("title", ""),
                                "play_count": item.get("play_count", 0),
                                "publish_time": item.get("publish_time", ""),
                                "average_play_duration": item.get("average_play_duration", 0),
                                "bounce_rate_2s": item.get("bounce_rate_2s", 0),
                                "completion_rate_5s": item.get("completion_rate_5s", 0),
                                "cover": item.get("cover", {}).get("url_list", [""])[0] if item.get("cover") else "",
                            }
                            print(f"[+] 获取到视频: {item.get('title', '')[:30]}")
                
                # 捕获趋势数据
                if "metrics_trend" in url:
                    trend_map = data.get("trend_map", {})
                    for metric_name, metric_data in trend_map.items():
                        if "0" in metric_data:
                            if metric_name not in trend_data:
                                trend_data[metric_name] = []
                            trend_data[metric_name] = metric_data["0"]
                            print(f"[+] 获取到趋势数据: {metric_name} ({len(metric_data['0'])} 个数据点)")
                            
            except Exception as e:
                if DEBUG_MODE:
                    print(f"[-] 解析响应失败: {e}")
        
        page.on("response", handle_response)
        
        # 1. 先获取视频列表
        print("[+] 访问视频数据页面...")
        await page.goto("https://creator.douyin.com/creator-micro/data/stats/video")
        await asyncio.sleep(5)
        
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except:
            pass
        
        await asyncio.sleep(3)
        
        # 2. 如果指定了视频ID，访问详情页面
        if video_id:
            print(f"[+] 访问视频详情页面: {video_id}")
            detail_url = f"https://creator.douyin.com/creator-micro/work-management/work-detail/{video_id}"
            await page.goto(detail_url)
            await asyncio.sleep(3)
            
            # 点击分析按钮
            try:
                analysis_btn = page.locator('text=分析').first
                if await analysis_btn.count():
                    await analysis_btn.click()
                    print("[+] 已点击分析按钮")
                    await asyncio.sleep(5)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=15000)
                    except:
                        pass
            except Exception as e:
                print(f"[-] 点击分析按钮失败: {e}")
        else:
            # 如果没有指定视频ID，点击第一个视频的分析
            print("[+] 尝试点击第一个视频的分析...")
            try:
                # 等待表格加载
                await page.wait_for_selector('table', timeout=10000)
                rows = await page.locator('table tbody tr').all()
                if rows:
                    # 点击第一行
                    await rows[0].click()
                    await asyncio.sleep(3)
                    
                    # 点击分析按钮
                    analysis_btn = page.locator('text=分析').first
                    if await analysis_btn.count():
                        await analysis_btn.click()
                        await asyncio.sleep(5)
            except Exception as e:
                print(f"[-] 点击视频失败: {e}")
        
        await asyncio.sleep(3)
        
        # 更新 cookie
        await context.storage_state(path=COOKIE_FILE)
        await browser.close()
        
        return {
            "videos": list(video_detail.values()),
            "trends": trend_data
        }


def print_video_trends(data):
    """打印视频趋势数据"""
    videos = data.get("videos", [])
    trends = data.get("trends", {})
    
    if videos:
        print("\n" + "="*80)
        print("📊 视频基本信息")
        print("="*80)
        for video in videos:
            print(f"标题: {video.get('title', 'N/A')}")
            print(f"视频ID: {video.get('item_id', 'N/A')}")
            print(f"总播放量: {video.get('play_count', 'N/A')}")
            print(f"平均播放时长: {video.get('average_play_duration', 0):.1f}s")
            print(f"5s完播率: {video.get('completion_rate_5s', 0)*100:.1f}%")
            print(f"发布时间: {video.get('publish_time', 'N/A')}")
            print("-"*40)
    
    if trends:
        print("\n" + "="*80)
        print("📈 时间趋势数据")
        print("="*80)
        
        for metric_name, metric_data in trends.items():
            if not metric_data:
                continue
            
            metric_name_cn = {
                "view_count": "播放量",
                "like_count": "点赞数",
                "comment_count": "评论数",
                "share_count": "分享数",
                "subscribe_count": "新增粉丝",
            }.get(metric_name, metric_name)
            
            print(f"\n{metric_name_cn}趋势:")
            print("-"*50)
            
            # 计算总量
            total = sum(float(d.get("value", 0)) for d in metric_data)
            print(f"总计: {int(total)}")
            
            # 按天聚合数据
            daily_data = {}
            for point in metric_data:
                date_str = point.get("date_time", "")[:10]  # 取日期部分
                value = float(point.get("value", 0))
                if date_str not in daily_data:
                    daily_data[date_str] = 0
                daily_data[date_str] += value
            
            # 打印每日趋势
            print("\n每日趋势:")
            max_val = max(daily_data.values()) if daily_data else 1
            for date, val in sorted(daily_data.items()):
                bar_len = int(val / max_val * 30) if max_val > 0 else 0
                bar = '█' * bar_len
                print(f"  {date}: {int(val):>5} {bar}")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='获取抖音单视频详细数据')
    parser.add_argument('--video_id', '-v', type=str, help='视频ID，不提供则获取最新视频')
    args = parser.parse_args()
    
    print("[+] 开始获取抖音视频数据...")
    
    if not os.path.exists(COOKIE_FILE):
        print(f"[-] Cookie 文件不存在: {COOKIE_FILE}")
        return
    
    data = await get_single_video_stats(video_id=args.video_id)
    
    if data:
        print_video_trends(data)
        
        # 保存到文件
        output_file = os.path.join(os.path.dirname(__file__), "douyin_single_video_stats.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n[+] 数据已保存到: {output_file}")
    else:
        print("[-] 获取视频数据失败")


if __name__ == "__main__":
    asyncio.run(main())
