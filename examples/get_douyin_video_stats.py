# -*- coding: utf-8 -*-
"""
获取抖音创作者中心视频数据（播放量、点赞数、评论数等）
"""
import asyncio
import json
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright
from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from utils.base_social_media import set_init_script


# Cookie 文件路径
COOKIE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                           "cookies", "douyin_uploader", "account.json")

# 设置为 True 以查看浏览器操作并保存API响应（调试时使用）
DEBUG_MODE = False


async def get_video_stats(page_num: int = 1, page_size: int = 20):
    """
    获取抖音创作者中心的视频数据
    
    Args:
        page_num: 页码，默认第1页
        page_size: 每页数量，默认20条
    
    Returns:
        视频数据列表
    """
    async with async_playwright() as playwright:
        # 启动浏览器 - 调试时使用非 headless 模式
        headless = False if DEBUG_MODE else LOCAL_CHROME_HEADLESS
        browser = await playwright.chromium.launch(
            headless=headless,
            executable_path=LOCAL_CHROME_PATH if LOCAL_CHROME_PATH else None
        )
        
        # 使用已保存的 cookie 创建上下文
        context = await browser.new_context(storage_state=COOKIE_FILE)
        context = await set_init_script(context)
        
        page = await context.new_page()
        
        # 存储API响应数据
        video_data = []
        all_responses = []  # 存储所有相关响应用于调试
        
        # 存储视频数据和性能数据
        performance_data = {}  # item_id -> 播放量等数据
        item_list_data = {}    # item_id -> 基本信息
        
        # 监听网络请求，捕获视频列表API响应
        async def handle_response(response):
            url = response.url
            content_type = response.headers.get("content-type", "")
            
            if "application/json" not in content_type:
                return
                
            try:
                data = await response.json()
                
                # 捕获 item_performance API - 包含播放量数据
                if "item_analysis/item_performance" in url:
                    all_responses.append({"url": url, "data": data})
                    print(f"[+] 捕获到视频性能数据API")
                    items = data.get("items", [])
                    for item in items:
                        item_id = item.get("item_id")
                        if item_id:
                            performance_data[item_id] = {
                                "play_count": item.get("play_count", "0"),
                                "title": item.get("title", ""),
                                "publish_time": item.get("publish_time", ""),
                                "cover": item.get("cover", {}).get("url_list", [""])[0] if item.get("cover") else "",
                                "average_play_duration": item.get("average_play_duration", 0),
                                "bounce_rate_2s": item.get("bounce_rate_2s", 0),
                                "completion_rate_5s": item.get("completion_rate_5s", 0),
                            }
                    print(f"[+] 发现 {len(items)} 条视频性能数据")
                
                # 捕获 item/list API - 包含基本信息
                elif "creator/item/list" in url or "item/list" in url:
                    all_responses.append({"url": url, "data": data})
                    print(f"[+] 捕获到视频列表API")
                    items = data.get("items", [])
                    for item in items:
                        item_id = item.get("id")
                        if item_id:
                            item_list_data[item_id] = {
                                "description": item.get("description", ""),
                                "create_time": item.get("create_time", ""),
                                "cover": item.get("cover", {}).get("url_list", [""])[0] if item.get("cover") else "",
                            }
                    print(f"[+] 发现 {len(items)} 条视频列表数据")
                
                # 捕获概览数据
                elif "item_analysis/overview" in url:
                    all_responses.append({"url": url, "data": data})
                    print(f"[+] 捕获到概览数据: 条均点赞 {data.get('average_like_count_per_video', {}).get('metric_value', 0)}, "
                          f"条均评论 {data.get('average_comment_count_per_video', {}).get('metric_value', 0)}")
                          
            except Exception as e:
                if DEBUG_MODE:
                    print(f"[-] 解析响应失败: {e}")
        
        page.on("response", handle_response)
        
        # 访问创作者中心 - 数据中心
        print("[+] 正在访问抖音创作者中心...")
        await page.goto("https://creator.douyin.com/creator-micro/data/stats/video")
        
        # 等待页面加载
        await asyncio.sleep(5)
        
        # 检查是否需要登录
        if await page.get_by_text('手机号登录').count() or await page.get_by_text('扫码登录').count():
            print("[-] Cookie 已失效，请重新登录")
            await browser.close()
            return None
        
        print("[+] Cookie 有效，正在获取数据...")
        
        # 等待页面完全加载
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)
        
        # 合并数据并生成结果
        results = []
        
        # 优先使用 performance_data（包含播放量）
        if performance_data:
            print(f"[+] 从性能数据中提取 {len(performance_data)} 条视频")
            for item_id, perf in performance_data.items():
                # 尝试从 item_list_data 获取额外信息
                list_info = item_list_data.get(item_id, {})
                
                # 解析播放量（可能是字符串）
                play_count = perf.get("play_count", "0")
                if isinstance(play_count, str):
                    play_count = int(play_count) if play_count.isdigit() else 0
                
                video_info = {
                    "video_id": str(item_id),
                    "title": perf.get("title", "") or list_info.get("description", ""),
                    "play_count": play_count,
                    "publish_time": perf.get("publish_time", ""),
                    "cover": perf.get("cover", "") or list_info.get("cover", ""),
                    "average_play_duration": round(perf.get("average_play_duration", 0), 2),
                    "bounce_rate_2s": round(perf.get("bounce_rate_2s", 0) * 100, 2),
                    "completion_rate_5s": round(perf.get("completion_rate_5s", 0) * 100, 2),
                    # 点赞/评论/分享数据在这个API中没有，设为N/A
                    "like_count": "N/A",
                    "comment_count": "N/A",
                    "share_count": "N/A",
                }
                results.append(video_info)
        
        # 如果没有性能数据，尝试使用列表数据
        elif item_list_data:
            print(f"[+] 从列表数据中提取 {len(item_list_data)} 条视频")
            for item_id, info in item_list_data.items():
                video_info = {
                    "video_id": str(item_id),
                    "title": info.get("description", ""),
                    "create_time": info.get("create_time", ""),
                    "cover": info.get("cover", ""),
                    "play_count": "N/A",
                    "like_count": "N/A",
                    "comment_count": "N/A",
                    "share_count": "N/A",
                }
                results.append(video_info)
        
        # 如果还是没有数据，尝试访问作品管理页面
        if not results:
            print("[+] 尝试访问作品管理页面...")
            await page.goto("https://creator.douyin.com/creator-micro/content/manage")
            await asyncio.sleep(5)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)
            
            # 再次检查捕获的数据
            if performance_data:
                for item_id, perf in performance_data.items():
                    list_info = item_list_data.get(item_id, {})
                    play_count = perf.get("play_count", "0")
                    if isinstance(play_count, str):
                        play_count = int(play_count) if play_count.isdigit() else 0
                    
                    video_info = {
                        "video_id": str(item_id),
                        "title": perf.get("title", "") or list_info.get("description", ""),
                        "play_count": play_count,
                        "publish_time": perf.get("publish_time", ""),
                        "cover": perf.get("cover", "") or list_info.get("cover", ""),
                        "average_play_duration": round(perf.get("average_play_duration", 0), 2),
                        "like_count": "N/A",
                        "comment_count": "N/A",
                        "share_count": "N/A",
                    }
                    results.append(video_info)
        
        # 保存调试信息
        if DEBUG_MODE and all_responses:
            debug_file = os.path.join(os.path.dirname(__file__), "douyin_api_debug.json")
            with open(debug_file, "w", encoding="utf-8") as f:
                json.dump(all_responses, f, ensure_ascii=False, indent=2)
            print(f"[DEBUG] API响应已保存到: {debug_file}")
        
        await context.storage_state(path=COOKIE_FILE)  # 更新 cookie
        await browser.close()
        
        return results


async def get_video_stats_via_api(page):
    """
    直接调用抖音API获取视频数据（备用方案）
    """
    # 可以添加直接调用API的逻辑
    pass


def print_video_stats(videos):
    """打印视频数据"""
    if not videos:
        print("[-] 未获取到视频数据")
        return
    
    print("\n" + "="*100)
    print(f"{'序号':<4}{'标题':<35}{'播放量':<10}{'平均播放(s)':<12}{'5s完播率':<10}{'发布时间':<18}")
    print("="*100)
    
    total_plays = 0
    for i, video in enumerate(videos, 1):
        title = video['title'][:30] + "..." if len(video['title']) > 30 else video['title']
        play_count = video.get('play_count', 'N/A')
        avg_duration = video.get('average_play_duration', 'N/A')
        completion = video.get('completion_rate_5s', 'N/A')
        publish_time = video.get('publish_time', video.get('create_time', 'N/A'))
        
        # 格式化完播率
        if isinstance(completion, (int, float)):
            completion = f"{completion:.1f}%"
        
        print(f"{i:<4}{title:<35}{str(play_count):<10}{str(avg_duration):<12}{str(completion):<10}{str(publish_time):<18}")
        
        if isinstance(play_count, int):
            total_plays += play_count
    
    print("="*100)
    print(f"共 {len(videos)} 个视频，总播放量: {total_plays}")


async def main():
    print("[+] 开始获取抖音视频数据...")
    
    # 检查 cookie 文件是否存在
    if not os.path.exists(COOKIE_FILE):
        print(f"[-] Cookie 文件不存在: {COOKIE_FILE}")
        print("[*] 请先运行 get_douyin_cookie.py 登录")
        return
    
    videos = await get_video_stats()
    
    if videos:
        print_video_stats(videos)
        
        # 保存到 JSON 文件
        output_file = os.path.join(os.path.dirname(__file__), "douyin_video_stats.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(videos, f, ensure_ascii=False, indent=2)
        print(f"\n[+] 数据已保存到: {output_file}")
    else:
        print("[-] 获取视频数据失败")


if __name__ == "__main__":
    asyncio.run(main())
