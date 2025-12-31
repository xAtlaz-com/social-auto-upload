# -*- coding: utf-8 -*-
"""
获取小红书单个笔记的详细数据
"""
import asyncio
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright
from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from utils.base_social_media import set_init_script

COOKIE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                           "cookies", "xiaohongshu_uploader", "account.json")

# 设置为 True 以查看浏览器操作
DEBUG_MODE = False


async def get_single_note_stats(note_id: str = None):
    """
    获取单个笔记的详细统计数据
    
    Args:
        note_id: 笔记ID，如果不提供则获取第一个笔记的数据
    """
    async with async_playwright() as playwright:
        headless = False if DEBUG_MODE else LOCAL_CHROME_HEADLESS
        browser = await playwright.chromium.launch(
            headless=headless,
            executable_path=LOCAL_CHROME_PATH if LOCAL_CHROME_PATH else None
        )
        
        context = await browser.new_context(storage_state=COOKIE_FILE)
        context = await set_init_script(context)
        page = await context.new_page()
        
        # 存储捕获的数据
        note_list = []
        note_detail = {}
        all_api_responses = []
        
        async def handle_response(response):
            url = response.url
            content_type = response.headers.get("content-type", "")
            
            if "json" not in content_type and "text" not in content_type:
                return
            
            if "xiaohongshu.com" not in url:
                return
                
            try:
                data = await response.json()
                
                # 捕获笔记列表
                if "note/analyze/list" in url:
                    notes = data.get("data", {}).get("note_infos", [])
                    note_list.extend(notes)
                    print(f"[+] 获取到 {len(notes)} 条笔记")
                
                # 捕获单笔记详情数据
                if any(k in url for k in ["note/base", "note/analysis", "note/trend", "note/audience"]):
                    all_api_responses.append({"url": url, "data": data})
                    print(f"[+] 捕获单笔记API: {url.split('?')[0].split('/')[-1]}")
                    
                    # 提取具体数据
                    d = data.get("data", {})
                    if d:
                        note_detail.update(d)
                        
            except Exception as e:
                if DEBUG_MODE:
                    print(f"[-] 解析响应失败: {e}")
        
        page.on("response", handle_response)
        
        # 1. 访问内容分析页面获取笔记列表
        print("[+] 访问内容分析页面...")
        await page.goto("https://creator.xiaohongshu.com/publish/publish")
        await asyncio.sleep(3)
        
        # 点击内容分析菜单
        try:
            content_btn = page.locator('text=内容分析').first
            if await content_btn.count():
                await content_btn.click()
                await asyncio.sleep(5)
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except:
                    pass
        except Exception as e:
            print(f"[-] 点击内容分析失败: {e}")
        
        await asyncio.sleep(3)
        
        # 2. 点击"详情数据"进入单笔记详情
        print("[+] 点击详情数据进入单笔记分析...")
        
        # 为新页面设置监听器
        detail_page = None
        new_page_data = []
        
        async def handle_new_page(new_page):
            nonlocal detail_page
            detail_page = new_page
            
            async def handle_new_response(response):
                url = response.url
                if "xiaohongshu.com" in url:
                    try:
                        ct = response.headers.get("content-type", "")
                        if "json" in ct:
                            data = await response.json()
                            new_page_data.append({"url": url, "data": data})
                            
                            # 特别关注时间趋势数据
                            if any(k in url for k in ["trend", "daily", "hourly", "time"]):
                                print(f"[+] 发现时间维度API: {url[:60]}...")
                    except:
                        pass
            
            new_page.on("response", handle_new_response)
        
        context.on("page", handle_new_page)
        
        try:
            # 如果指定了笔记ID，找到对应的行
            detail_links = page.locator('text=详情数据')
            count = await detail_links.count()
            print(f"[+] 找到 {count} 个详情数据链接")
            
            if count > 0:
                # 点击第一个（或指定的）详情链接
                target_index = 0
                if note_id and note_list:
                    for i, note in enumerate(note_list):
                        if note.get("id") == note_id:
                            target_index = i
                            break
                
                await detail_links.nth(target_index).click()
                print(f"[+] 已点击第 {target_index + 1} 个详情链接")
                
                # 等待新页面加载
                await asyncio.sleep(8)
                
                # 检查是否有新页面
                pages = context.pages
                print(f"[+] 当前页面数: {len(pages)}")
                
                if len(pages) > 1:
                    detail_page = pages[-1]
                    print(f"[+] 新页面URL: {detail_page.url}")
                    
                    try:
                        await detail_page.wait_for_load_state("networkidle", timeout=15000)
                    except:
                        pass
                    
                    await asyncio.sleep(3)
                    
                    # 截图
                    if DEBUG_MODE:
                        await detail_page.screenshot(path="examples/xhs_note_detail_page.png", full_page=True)
                        print("[+] 新页面截图已保存")
                    
                    # 尝试点击时间维度切换
                    for text in ["7天", "30天", "近7天", "近30天"]:
                        btn = detail_page.locator(f'text={text}').first
                        if await btn.count():
                            print(f"[+] 找到 '{text}' 按钮，点击它")
                            await btn.click()
                            await asyncio.sleep(3)
                            break
                    
                    # 再等待一会儿收集更多数据
                    await asyncio.sleep(3)
                    
        except Exception as e:
            print(f"[-] 获取单笔记数据失败: {e}")
        
        # 合并所有API响应
        all_api_responses.extend(new_page_data)
        
        # 更新 cookie
        await context.storage_state(path=COOKIE_FILE)
        await browser.close()
        
        # 整理返回数据
        result = {
            "notes": note_list[:10],  # 最多返回10条
            "detail": note_detail,
            "api_responses": all_api_responses if DEBUG_MODE else [],
        }
        
        return result


def print_note_stats(data):
    """打印笔记统计数据"""
    notes = data.get("notes", [])
    detail = data.get("detail", {})
    
    print("\n" + "="*80)
    print("📊 笔记列表数据")
    print("="*80)
    
    if notes:
        print(f"{'序号':<4}{'标题':<30}{'曝光':<8}{'观看':<8}{'点击率':<10}{'点赞':<6}{'评论':<6}{'收藏':<6}")
        print("-"*80)
        
        for i, note in enumerate(notes[:10], 1):
            title = note.get("title", "")[:25]
            imp = note.get("imp_count", 0)
            view = note.get("read_count", 0)
            click_rate = note.get("coverClickRate", 0)
            like = note.get("like_count", 0)
            comment = note.get("comment_count", 0)
            fav = note.get("fav_count", 0)
            
            print(f"{i:<4}{title:<30}{imp:<8}{view:<8}{click_rate*100:.1f}%{' '*5}{like:<6}{comment:<6}{fav:<6}")
    
    if detail:
        print("\n" + "="*80)
        print("📈 单笔记详细数据")
        print("="*80)
        for key, value in detail.items():
            if isinstance(value, (int, float, str)):
                print(f"  {key}: {value}")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='获取小红书单笔记详细数据')
    parser.add_argument('--note_id', '-n', type=str, help='笔记ID')
    parser.add_argument('--debug', '-d', action='store_true', help='调试模式')
    args = parser.parse_args()
    
    global DEBUG_MODE
    DEBUG_MODE = args.debug
    
    print("[+] 开始获取小红书笔记数据...")
    
    if not os.path.exists(COOKIE_FILE):
        print(f"[-] Cookie 文件不存在: {COOKIE_FILE}")
        return
    
    data = await get_single_note_stats(note_id=args.note_id)
    
    if data:
        print_note_stats(data)
        
        # 保存到文件
        output_file = os.path.join(os.path.dirname(__file__), "xiaohongshu_single_note_stats.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n[+] 数据已保存到: {output_file}")
    else:
        print("[-] 获取笔记数据失败")


if __name__ == "__main__":
    asyncio.run(main())
