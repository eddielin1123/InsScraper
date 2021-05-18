import random
import asyncio
from time import time
from logging.handlers import TimedRotatingFileHandler
from playwright.async_api import async_playwright, TimeoutError


from .utils.login import check_login
from .utils.extractor import Comment
from .utils.logger import Logger

logger = Logger()

async def ig_context(page, postId):

    async def get_post_context(page, postId):
        '''取得文案'''

        page.set_default_navigation_timeout(60000)

        try:
            await page.goto(f"https://www.instagram.com/p/{postId}/")
            await page.wait_for_load_state('load')
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_load_state('networkidle')
            print('IG 已進入粉專')
        except TimeoutError as e:
            await page.screenshot(path='error1.png')
            logger.error(f'IG: {postId} 連線逾時(未進入粉專)')

        try:
            print('解析中')
            await page.wait_for_selector('//html/body/div[1]/section/main/div/div[1]/article/div[3]/div[1]/ul/div/li/div/div/div[2]/span')
            text = await page.inner_text('//html/body/div[1]/section/main/div/div[1]/article/div[3]/div[1]/ul/div/li/div/div/div[2]/span',timeout=0)
            logger.info(f'IG: {postId} IG 已取得文案 https://www.instagram.com/p/{postId}/')
        except TimeoutError as e:
            await page.screenshot(path='critical.png')
            text = ''
            logger.error(f'找不到標籤 請確認 IG 是否改版')

        return text
    loop = asyncio.get_running_loop()
    postData = loop.run_until_complete(get_post_context(page, postId))
    print(f'IG 已擷取文案 {postData}')
    return postData

async def extract_comments_full(page, postData):
    
    output_json = []
    postId = postData['postId']
    async def _get_post_comment(page, postId, output_json):

        page.set_default_navigation_timeout(70000)

        # 進入粉專頁面
        try:
            await page.goto(f"https://www.instagram.com/p/{postId}/")
            await page.wait_for_load_state('load')
            await page.wait_for_load_state('domcontentloaded')
            # await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(random.randint(4000,8000))
        except TimeoutError as e:
            await page.screenshot(path='/home/eddielin/ad_spiders/ig_scraper/kol_page_timeout.png')
            raise f'連線逾時: {e}'

        # 擷取留言及子留言
        return Comment(output_json, page)

    loop = asyncio.get_running_loop() #! 此處必須使用get_running_loop取得當下loop 使用new_event_loop會報錯
    loop.run_until_complete(_get_post_comment(page, postId, output_json))

    postData['comments'] = output_json
    
    return postData


