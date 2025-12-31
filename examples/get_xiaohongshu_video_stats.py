# -*- coding: utf-8 -*-
"""
获取小红书创作者中心视频/笔记数据（浏览量、点赞数、评论数、收藏数等）
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
                           "cookies", "xiaohongshu_uploader", "account.json")

# 设置为 True 以查看浏览器操作并保存API响应（调试时使用）
DEBUG_MODE = True


async def get_note_stats():
    """
    获取小红书创作者中心的笔记数据
    
    Returns:
        笔记数据列表
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
        note_data = []
        all_responses = []  # 存储所有相关响应用于调试
        
        # 存储时间维度数据
        account_stats = {}  # 账号概览数据（7天/30天）
        
        # 监听网络请求，捕获笔记列表API响应
        async def handle_response(response):
            url = response.url
            content_type = response.headers.get("content-type", "")
            
            # 小红书可能使用不同的 content-type
            if "json" not in content_type and "text" not in content_type:
                return
            
            # 只关注小红书域名的请求
            if "xiaohongshu.com" not in url:
                return
                
            try:
                data = await response.json()
                
                # 扩展匹配模式 - 捕获所有可能包含笔记数据的 API
                api_patterns = [
                    "note", "notes", "creator", "data", "list", 
                    "work", "content", "publish", "manage", "overview",
                    "analysis", "stat", "insight"
                ]
                
                if any(pattern in url.lower() for pattern in api_patterns):
                    all_responses.append({"url": url, "data": data})
                    if DEBUG_MODE:
                        print(f"[+] 捕获API: {url[:80]}...")
                    
                    # 捕获账号概览数据（7天/30天统计）
                    if "datacenter/account/base" in url and isinstance(data, dict):
                        d = data.get("data", {})
                        if "seven" in d:
                            account_stats["seven"] = d.get("seven", {})
                            print(f"[+] 捕获到7天账号概览数据")
                        if "thirty" in d:
                            account_stats["thirty"] = d.get("thirty", {})
                            print(f"[+] 捕获到30天账号概览数据")
                    
                    # 尝试从各种可能的路径提取笔记列表
                    if isinstance(data, dict):
                        notes = (
                            data.get("data", {}).get("notes") or
                            data.get("data", {}).get("note_list") or
                            data.get("data", {}).get("list") or
                            data.get("data", {}).get("items") or
                            data.get("data", {}).get("works") or
                            data.get("notes") or
                            data.get("note_list") or
                            data.get("list") or
                            data.get("items") or
                            []
                        )
                        if notes and isinstance(notes, list) and len(notes) > 0:
                            note_data.extend(notes)
                            print(f"[+] 发现 {len(notes)} 条数据")
                          
            except Exception as e:
                if DEBUG_MODE:
                    print(f"[-] 解析响应失败: {url[:50]}... - {e}")
        
        page.on("response", handle_response)
        
        # 访问创作者中心
        print("[+] 正在访问小红书创作者中心...")
        await page.goto("https://creator.xiaohongshu.com/publish/publish?source=official")
        
        # 等待页面加载
        await asyncio.sleep(5)
        
        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except:
            print("[-] 页面加载超时，继续尝试...")
        
        # 检查是否需要登录
        if await page.locator('input[placeholder*="手机号"]').count():
            print("[-] Cookie 已失效，请重新登录")
            await browser.close()
            return None
        
        print("[+] Cookie 有效，正在获取数据...")
        
        # 截图保存
        if DEBUG_MODE:
            screenshot_path = os.path.join(os.path.dirname(__file__), "xiaohongshu_screenshot.png")
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"[DEBUG] 截图已保存到: {screenshot_path}")
        
        await asyncio.sleep(3)
        
        # 尝试点击笔记管理菜单
        print("[+] 尝试访问笔记管理...")
        try:
            note_manage_btn = page.locator('text=笔记管理').first
            if await note_manage_btn.count():
                await note_manage_btn.click()
                await asyncio.sleep(5)
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except:
                    pass
        except Exception as e:
            print(f"[-] 点击笔记管理失败: {e}")
        
        await asyncio.sleep(3)
        
        # 尝试访问账号概览页面（获取时间维度数据）
        print("[+] 尝试访问账号概览页面...")
        try:
            overview_btn = page.locator('text=账号概览').first
            if await overview_btn.count():
                await overview_btn.click()
                await asyncio.sleep(5)
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except:
                    pass
                
                if DEBUG_MODE:
                    screenshot_path = os.path.join(os.path.dirname(__file__), "xiaohongshu_overview.png")
                    await page.screenshot(path=screenshot_path, full_page=True)
                    print(f"[DEBUG] 账号概览截图已保存到: {screenshot_path}")
        except Exception as e:
            print(f"[-] 访问账号概览失败: {e}")
        
        await asyncio.sleep(3)
        
        # 尝试访问内容分析页面
        print("[+] 尝试访问内容分析页面...")
        try:
            content_btn = page.locator('text=内容分析').first
            if await content_btn.count():
                await content_btn.click()
                await asyncio.sleep(5)
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except:
                    pass
                
                if DEBUG_MODE:
                    screenshot_path = os.path.join(os.path.dirname(__file__), "xiaohongshu_content_analysis.png")
                    await page.screenshot(path=screenshot_path, full_page=True)
                    print(f"[DEBUG] 内容分析截图已保存到: {screenshot_path}")
        except Exception as e:
            print(f"[-] 访问内容分析失败: {e}")
        
        # 合并数据并生成结果
        results = []
        seen_ids = set()  # 去重
        
        for note in note_data:
            note_id = (
                note.get("note_id") or
                note.get("id") or
                note.get("noteId") or
                ""
            )
            if not note_id or note_id in seen_ids:
                continue
            seen_ids.add(note_id)
            
            # 提取笔记信息
            title = (
                note.get("title") or
                note.get("display_title") or
                note.get("desc") or
                ""
            )
            
            # 统计数据可能在 statistics 或 interact_info 中
            stats = note.get("statistics", {}) or note.get("interact_info", {}) or {}
            
            view_count = (
                note.get("view_count") or
                note.get("read_count") or
                stats.get("view_count") or
                stats.get("read_count") or
                note.get("views") or
                0
            )
            like_count = (
                note.get("like_count") or
                note.get("liked_count") or
                stats.get("like_count") or
                stats.get("liked_count") or
                note.get("likes") or
                0
            )
            comment_count = (
                note.get("comment_count") or
                stats.get("comment_count") or
                note.get("comments") or
                0
            )
            collect_count = (
                note.get("collect_count") or
                note.get("collected_count") or
                stats.get("collect_count") or
                stats.get("collected_count") or
                note.get("collects") or
                0
            )
            share_count = (
                note.get("share_count") or
                stats.get("share_count") or
                note.get("shares") or
                0
            )
            
            # 发布时间
            publish_time = (
                note.get("time") or
                note.get("create_time") or
                note.get("publish_time") or
                ""
            )
            
            # 封面
            cover = (
                note.get("cover", {}).get("url") if isinstance(note.get("cover"), dict) else note.get("cover") or
                note.get("image_list", [{}])[0].get("url") if note.get("image_list") else "" or
                ""
            )
            
            # 笔记类型
            note_type = "视频" if note.get("type") == "video" or note.get("is_video") else "图文"
            
            note_info = {
                "note_id": str(note_id),
                "title": title,
                "type": note_type,
                "view_count": int(view_count) if str(view_count).isdigit() else view_count,
                "like_count": int(like_count) if str(like_count).isdigit() else like_count,
                "comment_count": int(comment_count) if str(comment_count).isdigit() else comment_count,
                "collect_count": int(collect_count) if str(collect_count).isdigit() else collect_count,
                "share_count": int(share_count) if str(share_count).isdigit() else share_count,
                "publish_time": str(publish_time),
                "cover": cover,
            }
            results.append(note_info)
        
        # 如果还是没有数据，尝试从页面元素中提取
        if not results:
            print("[+] 尝试从页面元素中提取数据...")
            # 尝试访问内容管理页面
            await page.goto("https://creator.xiaohongshu.com/publish/publish")
            await asyncio.sleep(5)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)
            
            # 重新检查 note_data
            for note in note_data:
                note_id = note.get("note_id") or note.get("id") or ""
                if not note_id or note_id in seen_ids:
                    continue
                seen_ids.add(note_id)
                
                stats = note.get("statistics", {}) or note.get("interact_info", {}) or {}
                note_info = {
                    "note_id": str(note_id),
                    "title": note.get("title", "") or note.get("display_title", ""),
                    "type": "视频" if note.get("type") == "video" else "图文",
                    "view_count": stats.get("view_count", 0) or note.get("view_count", 0),
                    "like_count": stats.get("like_count", 0) or note.get("like_count", 0),
                    "comment_count": stats.get("comment_count", 0) or note.get("comment_count", 0),
                    "collect_count": stats.get("collect_count", 0) or note.get("collect_count", 0),
                    "share_count": stats.get("share_count", 0) or note.get("share_count", 0),
                    "publish_time": note.get("time", "") or note.get("create_time", ""),
                    "cover": "",
                }
                results.append(note_info)
        
        # 保存调试信息
        if DEBUG_MODE and all_responses:
            debug_file = os.path.join(os.path.dirname(__file__), "xiaohongshu_api_debug.json")
            with open(debug_file, "w", encoding="utf-8") as f:
                json.dump(all_responses, f, ensure_ascii=False, indent=2)
            print(f"[DEBUG] API响应已保存到: {debug_file}")
        
        await context.storage_state(path=COOKIE_FILE)  # 更新 cookie
        await browser.close()
        
        return {
            "notes": results,
            "account_stats": account_stats
        }


def print_note_stats(notes):
    """打印笔记数据"""
    if not notes:
        print("[-] 未获取到笔记数据")
        return
    
    print("\n" + "="*110)
    print(f"{'序号':<4}{'标题':<35}{'类型':<6}{'浏览':<10}{'点赞':<8}{'评论':<8}{'收藏':<8}{'分享':<8}")
    print("="*110)
    
    total_views = 0
    total_likes = 0
    total_comments = 0
    total_collects = 0
    
    for i, note in enumerate(notes, 1):
        title = note['title'][:30] + "..." if len(note['title']) > 30 else note['title']
        view_count = note.get('view_count', 'N/A')
        like_count = note.get('like_count', 'N/A')
        comment_count = note.get('comment_count', 'N/A')
        collect_count = note.get('collect_count', 'N/A')
        share_count = note.get('share_count', 'N/A')
        note_type = note.get('type', '未知')
        
        print(f"{i:<4}{title:<35}{note_type:<6}{str(view_count):<10}{str(like_count):<8}"
              f"{str(comment_count):<8}{str(collect_count):<8}{str(share_count):<8}")
        
        if isinstance(view_count, int):
            total_views += view_count
        if isinstance(like_count, int):
            total_likes += like_count
        if isinstance(comment_count, int):
            total_comments += comment_count
        if isinstance(collect_count, int):
            total_collects += collect_count
    
    print("="*110)
    print(f"共 {len(notes)} 条笔记，总浏览: {total_views}，总点赞: {total_likes}，"
          f"总评论: {total_comments}，总收藏: {total_collects}")


def print_account_stats(account_stats):
    """打印账号概览数据（7天/30天）"""
    if not account_stats:
        return
    
    from datetime import datetime
    
    def format_date(ts):
        if ts:
            return datetime.fromtimestamp(ts/1000).strftime('%m-%d')
        return ''
    
    # 打印7天数据
    seven = account_stats.get("seven", {})
    if seven:
        print("\n" + "="*80)
        print("📊 最近7天数据概览")
        print("="*80)
        
        # 曝光数
        impl_list = seven.get("impl_count_list", [])
        view_list = seven.get("view_list", [])
        
        if impl_list:
            total_impl = sum(item.get("count", 0) for item in impl_list)
            print(f"总曝光数: {total_impl}")
            
            print("\n每日曝光趋势:")
            print("-"*50)
            for item in sorted(impl_list, key=lambda x: x.get("date", 0)):
                date_str = format_date(item.get("date"))
                count = item.get("count", 0)
                bar = '█' * (count // 10) if count > 0 else ''
                print(f"  {date_str}: {count:>5} {bar}")
        
        if view_list:
            total_view = sum(item.get("count", 0) for item in view_list)
            print(f"\n总观看数: {total_view}")
            
            print("\n每日观看趋势:")
            print("-"*50)
            for item in sorted(view_list, key=lambda x: x.get("date", 0)):
                date_str = format_date(item.get("date"))
                count = item.get("count", 0)
                bar = '█' * count if count > 0 else ''
                print(f"  {date_str}: {count:>5} {bar}")
        
        # 其他统计数据
        print("\n其他指标:")
        print("-"*50)
        if "home_view_count" in seven:
            print(f"  主页访问数: {seven.get('home_view_count', 0)}")
        if "cover_click_cycle_rate" in seven:
            rate = seven.get('cover_click_cycle_rate', 0)
            print(f"  封面点击率环比: {'+' if rate >= 0 else ''}{rate}%")
        print("="*80)


async def main():
    print("[+] 开始获取小红书笔记数据...")
    
    # 检查 cookie 文件是否存在
    if not os.path.exists(COOKIE_FILE):
        print(f"[-] Cookie 文件不存在: {COOKIE_FILE}")
        print("[*] 请先运行登录脚本生成 cookie")
        return
    
    result = await get_note_stats()
    
    if result:
        notes = result.get("notes", [])
        account_stats = result.get("account_stats", {})
        
        # 打印账号概览数据（7天趋势）
        if account_stats:
            print_account_stats(account_stats)
        
        # 打印笔记列表
        if notes:
            print_note_stats(notes)
        
        # 保存到 JSON 文件
        output_file = os.path.join(os.path.dirname(__file__), "xiaohongshu_note_stats.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n[+] 数据已保存到: {output_file}")
    else:
        print("[-] 获取笔记数据失败")


if __name__ == "__main__":
    asyncio.run(main())
