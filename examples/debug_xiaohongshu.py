import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

from conf import BASE_DIR, LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from utils.base_social_media import set_init_script

async def debug_page():
    account_file = Path(BASE_DIR / "cookies" / "xiaohongshu_uploader" / "account.json")
    
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=False,
            executable_path=LOCAL_CHROME_PATH if LOCAL_CHROME_PATH else None
        )
        context = await browser.new_context(
            viewport={"width": 1600, "height": 900},
            storage_state=str(account_file)
        )
        context = await set_init_script(context)
        page = await context.new_page()
        
        # 打开发布页面
        await page.goto("https://creator.xiaohongshu.com/publish/publish?from=homepage&target=video")
        await page.wait_for_url("https://creator.xiaohongshu.com/publish/publish?from=homepage&target=video")
        
        # 上传视频文件
        video_file = Path(BASE_DIR / "videos" / "2025_12_13_14_48_36_highlight_0_multikill_1586-1610.mp4")
        print(f"\n正在上传视频: {video_file}")
        await page.locator("div[class^='upload-content'] input[class='upload-input']").set_input_files(str(video_file))
        
        # 等待上传完成
        print("等待视频上传完成...")
        for i in range(60):
            try:
                upload_input = await page.wait_for_selector('input.upload-input', timeout=3000)
                preview_new = await upload_input.query_selector('xpath=following-sibling::div[contains(@class, "preview-new")]')
                if preview_new:
                    stage_elements = await preview_new.query_selector_all('div.stage')
                    for stage in stage_elements:
                        text_content = await page.evaluate('(element) => element.textContent', stage)
                        if '上传成功' in text_content:
                            print("视频上传成功!")
                            break
                    else:
                        await asyncio.sleep(1)
                        continue
                    break
            except:
                await asyncio.sleep(1)
        
        await asyncio.sleep(2)
        print("\n页面已加载，正在分析页面结构...")
        
        # 先点击编辑器并输入话题
        print("\n=== 测试话题输入 ===")
        editor = page.locator(".tiptap.ProseMirror")
        if await editor.count() > 0:
            await editor.click()
            await asyncio.sleep(0.5)
            await page.keyboard.type("#游戏")
            print("已输入 #游戏，等待话题建议弹出...")
            await asyncio.sleep(2)
        
        # 查找话题建议相关元素
        print("\n=== 查找话题建议下拉列表 ===")
        
        # 查找所有弹出层/下拉框
        print("\n--- 查找弹出层元素 ---")
        popup_selectors = [
            '[class*="popover"]',
            '[class*="popup"]',
            '[class*="dropdown"]',
            '[class*="menu"]',
            '[class*="list"]',
            '[role="listbox"]',
            '[role="menu"]',
        ]
        for sel in popup_selectors:
            count = await page.locator(sel).count()
            if count > 0:
                print(f"\u2713 {sel}: {count}个")
                for i in range(min(count, 3)):
                    elem = page.locator(sel).nth(i)
                    cls = await elem.get_attribute('class') or ''
                    visible = await elem.is_visible()
                    text = (await elem.text_content() or '')[:50]
                    if visible and '游戏' in text:
                        print(f"    [{i}] ★可见且包含游戏: class='{cls[:40]}' text='{text}'")
                        html = await elem.evaluate('el => el.outerHTML')
                        print(f"        HTML: {html[:300]}")
                    elif visible:
                        print(f"    [{i}] 可见: class='{cls[:40]}' text='{text}'")
        
        print("\n--- 查找包含'游戏'的可点击元素 ---")
        game_elements = await page.locator('text=游戏').all()
        for i, elem in enumerate(game_elements[:8]):
            visible = await elem.is_visible()
            if visible:
                tag_name = await elem.evaluate('el => el.tagName')
                class_name = await elem.get_attribute('class') or ''
                parent_class = await elem.evaluate('el => el.parentElement?.className || ""')
                print(f"[{i}] tag={tag_name} class='{class_name[:40]}' parent='{parent_class[:40]}'")
        
        # 查找可能的输入框
        print("\n=== 查找文本输入相关元素 ===")
        
        selectors_to_check = [
            ".ql-editor",
            "[contenteditable='true']",
            "textarea",
            ".editor",
            ".content-editor",
            "[class*='editor']",
            "[class*='input']",
            "[class*='desc']",
            "[class*='content']",
            ".c-input_inner",
            "[data-placeholder]",
        ]
        
        for selector in selectors_to_check:
            try:
                count = await page.locator(selector).count()
                if count > 0:
                    print(f"✓ {selector}: 找到 {count} 个元素")
                    # 获取第一个元素的更多信息
                    for i in range(min(count, 3)):
                        elem = page.locator(selector).nth(i)
                        class_name = await elem.get_attribute("class") or ""
                        placeholder = await elem.get_attribute("placeholder") or await elem.get_attribute("data-placeholder") or ""
                        print(f"    [{i}] class='{class_name[:50]}...' placeholder='{placeholder}'")
            except Exception as e:
                pass
        
        print("\n=== 暂停浏览器，请手动检查页面 ===")
        print("在浏览器开发者工具中检查话题输入框的选择器")
        print("完成后在终端按 Ctrl+C 退出\n")
        
        # 暂停让用户检查
        await page.pause()
        
        await context.close()
        await browser.close()

if __name__ == '__main__':
    asyncio.run(debug_page())
