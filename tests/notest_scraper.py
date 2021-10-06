import pytest
import asyncio
import random
import nest_asyncio
from threading import Thread
from ig_scraper.post import ig_context, extract_comments_full, get_post_context
from playwright.async_api import async_playwright

page1 = None
my_browser = None
loop = asyncio.new_event_loop()

async def spider_browser():
    global page1
    global my_browser
    try:
        print('IG瀏覽器 啟動中')
        playwright = await async_playwright().start()        
        browser = await playwright.firefox.launch(headless=True, proxy={'server':'proxy.soax.com:9010','username':'F3sqgQnqRoWA1xQD','password':'wifi;tw;chunghwa+telecom'}) # IG只能用firefox (chromium會被拒絕訪問)
        # browser = await playwright.firefox.launch(headless=True) # IG只能用firefox (chromium會被拒絕訪問)
        my_browser = await browser.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36')
        page = await my_browser.new_page()
        # page.set_default_navigation_timeout(70000)
        await page.goto('https://www.instagram.com')
        await page.fill("input[name='username']", "hakapower1002") # 輸入帳密 eddielin1234
        await page.wait_for_timeout(random.randint(2000,4000))
        await page.fill('input[name="password"]', 'zdtb0626')
        await page.wait_for_timeout(random.randint(2000,4000))
        await page.click("button[type='submit']")
        await page.wait_for_load_state('load')
        # await page.wait_for_load_state('domcontentloaded') #按下登入後等待載入
        # await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(random.randint(3000,5000))
        await page.screenshot(path='/home/eddielin/ad_spiders/ig_scraper/check_login.png')
        
        # if await page.is_visible('[data-testid="login-error-message"]'):# 登入被拒絕
        #     login_err = await page.inner_text('[data-testid="login-error-message"]')
        #     print('IG 登入被拒絕: '+login_err)
        #     await page.screenshot(path='/home/eddielin/ad_spiders/ig_scraper/login_error.png')
        # else:
        #     url = page.url
        #     print(f'IG 登入成功: {url}')
            
    except TimeoutError as e:
        print(f'IG 登入失敗 連線逾時: : {e}')
        await page.screenshot(path='/home/eddielin/ad_spiders/ig_scraper/login_error.png')
    
    finally:
        page1 = page
        print('IG瀏覽器 啟動完成')

    # return (page, my_browser)

def _start_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

@pytest.fixture(autouse=True)
def start_ig_browser():

    global loop

    loop.run_until_complete(spider_browser())
    t = Thread(target=_start_background_loop, args=(loop,), daemon=True)
    t.start()


@pytest.mark.asyncio
def test_post_context():
    global page1, my_browser, loop
    nest_asyncio.apply()

    postIds = ['CQISu82DL7U']
    
    for postId in postIds:
        context, a_list = loop.run_until_complete(get_post_context(page1, postId))
        
        print(context)

        try:
            print('Tasks count: ', len(asyncio.all_tasks()))
            print('Running Task ',asyncio.current_task())
        except RuntimeError:
            print('Tasks all done')   
        

        if postId == 'CQISu82DL7U':
            assert '今晚8點！' in context
            assert a_list == ['@louisvuitton', '#LVCRUISE', '#louisvuitton']


@pytest.mark.comments
def test_comments():
    global page1, my_browser, loop
    nest_asyncio.apply()

    postData = {'postId':'CQISu82DL7U'}

    postData['comments'] = loop.run_until_complete(extract_comments_full(page1, postData))
    if postData.get('comments'):
        c_len = len(postData['comments'])
        print(f'IG 成功擷取留言 {c_len}筆')
        assert c_len > 10