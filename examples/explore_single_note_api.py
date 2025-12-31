# -*- coding: utf-8 -*-
"""
探索小红书单个笔记详情页的 API，查找时间维度数据 (24H/7D/30D)
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright
from conf import LOCAL_CHROME_PATH

COOKIE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                           "cookies", "xiaohongshu_uploader", "account.json")


async def explore_single_note_api():
    """探索单笔记详情 API"""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=False,
            executable_path=LOCAL_CHROME_PATH if LOCAL_CHROME_PATH else None
        )
        
        context = await browser.new_context(storage_state=COOKIE_FILE)
        page = await context.new_page()
        
        all_responses = []
        
        async def handle_response(response):
            url = response.url
            content_type = response.headers.get("content-type", "")
            
            if "json" not in content_type and "text" not in content_type:
                return
            
            if "xiaohongshu.com" not in url:
                return
                
            try:
                data = await response.json()
                # 捕获所有可能相关的 API
                keywords = ["note", "data", "detail", "stat", "analysis", 
                           "trend", "performance", "insight", "daily", "hour"]
                if any(k in url.lower() for k in keywords):
                    all_responses.append({"url": url, "data": data})
                    print(f"[+] 捕获: {url[:100]}...")
                    
                    # 如果包含时间序列数据，特别标记
                    data_str = json.dumps(data)
                    if any(k in data_str.lower() for k in ["24h", "7d", "30d", "daily", "hourly", "trend", "list"]):
                        print(f"    ★ 可能包含时间维度数据!")
                        
            except Exception as e:
                pass
        
        page.on("response", handle_response)
        
        # 1. 先访问创作者中心主页
        print("[+] 访问创作者中心...")
        await page.goto("https://creator.xiaohongshu.com/publish/publish")
        await asyncio.sleep(5)
        
        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except:
            pass
        
        # 截图
        await page.screenshot(path="examples/xhs_main.png", full_page=True)
        print("[+] 截图已保存: xhs_main.png")
        
        # 2. 点击内容分析菜单
        print("[+] 点击内容分析菜单...")
        try:
            content_btn = page.locator('text=内容分析').first
            if await content_btn.count():
                await content_btn.click()
                await asyncio.sleep(5)
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except:
                    pass
                await page.screenshot(path="examples/xhs_content_analysis.png", full_page=True)
                print("[+] 内容分析截图已保存: xhs_content_analysis.png")
        except Exception as e:
            print(f"[-] 点击内容分析失败: {e}")
        
        await asyncio.sleep(3)
        
        # 3. 点击"详情数据"链接查看单笔记详情
        print("[+] 点击'详情数据'链接...")
        try:
            # 尝试多种选择器
            selectors = [
                'text=详情数据',
                'span:has-text("详情数据")',
                'a:has-text("详情数据")',
                'div:has-text("详情数据")',
            ]
            detail_links = None
            for sel in selectors:
                links = page.locator(sel)
                count = await links.count()
                if count > 0:
                    detail_links = links
                    print(f"[+] 使用选择器 '{sel}' 找到 {count} 个元素")
                    break
            
            if detail_links is None:
                count = 0
            else:
                count = await detail_links.count()
            
            if count > 0:
                # 获取第一个链接的href
                href = await detail_links.first.get_attribute('href')
                print(f"[+] 链接地址: {href}")
                
                # 监听新页面的请求
                new_page_responses = []
                
                async def handle_new_page(new_page):
                    async def handle_resp(response):
                        url = response.url
                        if "xiaohongshu.com" in url:
                            try:
                                ct = response.headers.get("content-type", "")
                                if "json" in ct:
                                    data = await response.json()
                                    new_page_responses.append({"url": url, "data": data})
                                    print(f"[+] 新页面捕获: {url[:70]}...")
                            except:
                                pass
                    new_page.on("response", handle_resp)
                
                context.on("page", handle_new_page)
                
                # 点击链接（可能会打开新窗口）
                await detail_links.first.click()
                print("[+] 已点击链接")
                await asyncio.sleep(8)
                
                # 检查是否有新页面打开
                pages = context.pages
                print(f"[+] 当前打开的页面数: {len(pages)}")
                
                if len(pages) > 1:
                    # 切换到新页面
                    new_page = pages[-1]
                    await new_page.wait_for_load_state("networkidle", timeout=15000)
                    await asyncio.sleep(3)
                    
                    # 截图新页面
                    await new_page.screenshot(path="examples/xhs_note_detail_page.png", full_page=True)
                    print(f"[+] 新页面URL: {new_page.url}")
                    print("[+] 新页面截图已保存: xhs_note_detail_page.png")
                    
                    # 等待更多数据加载
                    await asyncio.sleep(5)
                    
                    # 尝试点击时间维度切换按钮
                    for text in ["7天", "30天", "24小时", "近7天", "近30天"]:
                        btn = new_page.locator(f'text={text}').first
                        if await btn.count():
                            print(f"[+] 找到 '{text}' 按钮，点击它")
                            await btn.click()
                            await asyncio.sleep(3)
                    
                    # 保存新页面的API响应
                    if new_page_responses:
                        all_responses.extend(new_page_responses)
                else:
                    # 没有新页面，可能是在当前页面内跳转
                    await page.screenshot(path="examples/xhs_note_detail.png", full_page=True)
                    print(f"[+] 当前URL: {page.url}")
            else:
                print("[-] 未找到'详情数据'链接")
        except Exception as e:
            print(f"[-] 点击详情数据失败: {e}")
        
        # 4. 等待更多 API 响应
        print("[+] 等待更多 API 响应...")
        await asyncio.sleep(5)
        
        # 保存所有捕获的 API
        output_file = "examples/xhs_single_note_api_explore.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_responses, f, ensure_ascii=False, indent=2)
        print(f"[+] API 响应已保存到: {output_file}")
        
        print(f"\n[+] 共捕获 {len(all_responses)} 个 API")
        
        # 分析可能有用的 API
        print("\n" + "="*60)
        print("可能包含时间维度数据的 API:")
        print("="*60)
        for resp in all_responses:
            url = resp["url"]
            data_str = json.dumps(resp["data"])
            if any(k in data_str.lower() for k in ["trend", "daily", "hourly", "list", "24", "7d", "30d"]):
                print(f"\n★ {url[:80]}")
                # 打印数据结构的 keys
                if isinstance(resp["data"], dict):
                    print(f"  Keys: {list(resp['data'].keys())[:10]}")
                    if "data" in resp["data"]:
                        d = resp["data"]["data"]
                        if isinstance(d, dict):
                            print(f"  data Keys: {list(d.keys())[:10]}")
        
        input("\n按 Enter 键关闭浏览器...")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(explore_single_note_api())
