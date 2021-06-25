import random
import asyncio
from playwright.async_api import TimeoutError
from .logger import Logger
logger = Logger()

async def check_login(page, postId):
    '''登入頁面'''
    await _enter_accinfo(page, postId)
    await _enter_later(page)

async def _enter_accinfo(page, postId):
    try:
        await page.goto('https://www.instagram.com/')
        await page.wait_for_load_state('load')
        await page.fill("input[name='username']", "hakapower1002") # 輸入帳密
        await page.wait_for_timeout(random.randint(4000,7000))
        await page.fill('input[name="password"]', 'zdtb0626')
        await page.wait_for_timeout(random.randint(4000,7000))
        await page.click("button[type='submit']")
        await page.wait_for_load_state('load')
        await page.wait_for_load_state('domcontentloaded') #按下登入後等待載入
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(random.randint(5000,8000))
        
        if await page.is_visible('[data-testid="login-error-message"]'):# 登入被拒絕
            login_err = await page.inner_text('[data-testid="login-error-message"]')
            logger.critical('IG 登入被拒絕: '+login_err)
            await page.screenshot(path='IG_login_error1.png')
        elif 'accounts/onetap/?next' in page.url:
            print(f'登入成功: {page.url}')
            logger.info('IG 登入成功')
        else:
            print(f'登入失敗: {page.url}')
            logger.info('IG 登入失敗')
            
    except TimeoutError as e:
        logger.error(f'登入失敗 連線逾時: {postId} : {e}')
        await page.screenshot(path='IG_login_error2.png')
        pass


async def _enter_later(page):
    
    if await page.is_visible('//html/body/div[1]/section/main/div/div/div/div/button'):# 不儲存登入資訊 點擊“稍後再說“
                await page.click('//html/body/div[1]/section/main/div/div/div/div/button') 
                
    if await page.is_visible('//html/body/div[4]/div/div/div/div[3]/button[2]'):# 彈出開啟通知視窗 點擊“稍後再說”
        await page.click('//html/body/div[4]/div/div/div/div[3]/button[2]') 
    