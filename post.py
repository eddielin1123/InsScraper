import re
import random
import asyncio
from time import time, sleep
from logging.handlers import TimedRotatingFileHandler
from playwright.async_api import async_playwright, TimeoutError


from .utils.login import check_login
from .utils.extractor import Comment, press_more_comments
from .utils.logger import Logger

logger = Logger()

async def ig_context(page, postId):

    async def get_post_context(page, postId):
        '''取得文案'''

        page.set_default_navigation_timeout(60000)
        for i in range(5):
            try:
                await page.goto(f"https://www.instagram.com/p/{postId}/")
                await page.wait_for_load_state('load')
                # await page.wait_for_load_state('domcontentloaded')
                # await page.wait_for_load_state('networkidle')
                print('IG 已進入粉專')
                break
            except TimeoutError as e:
                await page.screenshot(path='IG_TimeoutError1.png')
                print(f'IG: {postId} 連線逾時(未進入粉專) 嘗試第{i}次')
                logger.error(f'IG: {postId} 連線逾時(未進入粉專) 嘗試第{i}次')
                sleep(3)
                continue

        try:
            print('解析中')
            a_list = []
            await page.wait_for_selector('//html/body/div[1]/section/main/div/div[1]/article/div[3]/div[1]/ul/div/li/div/div/div[2]/span')
            all_a_text = await page.query_selector_all('//html/body/div[1]/section/main/div/div[1]/article/div[3]/div[1]/ul/div/li/div/div/div[2]/span/a')
            text = await page.inner_text('//html/body/div[1]/section/main/div/div[1]/article/div[3]/div[1]/ul/div/li/div/div/div[2]/span',timeout=0)
            
            for a in all_a_text:
                a = await a.inner_text()
                a_list.append(a)

            logger.info(f'IG: {postId} IG 已取得文案 https://www.instagram.com/p/{postId}/')
            return text, a_list

        except TimeoutError as e:
            await page.screenshot(path='IG_TimeoutError2.png')
            text = ''
            logger.error(f'IG 文案找不到標籤 請確認 IG 是否改版')

        finally:
            await page.close()
        # try:
        #     likes = await page.inner_text('//html/body/div[1]/section/main/div/div[1]/article/div[3]/section[2]/div/div[2]/a/span')
        #     likes = int(likes)
        # except TimeoutError:
        #     likes = 0
        #     logger.error(f'IG 文案讚數找不到標籤 請確認 IG 是否改版')

        
        

    loop = asyncio.get_event_loop()
    context, a_list = loop.run_until_complete(get_post_context(page, postId))
    print('IG 已擷取文案：')
    print('='*30)
    print(context)
    print('='*30)

    return context, a_list

async def extract_comments_full(page, postData):
    
    output_json = []
    postId = postData['postId']

    async def _get_post_comment(page, postId, output_json):

        page.set_default_navigation_timeout(70000)

        # 進入粉專頁面
        for i in range(5):
            try:
                await page.goto(f"https://www.instagram.com/p/{postId}/")
                await page.wait_for_load_state('load')
                await page.wait_for_timeout(random.randint(4000,8000))
                break
            except TimeoutError as e:
                await page.screenshot(path='IG_kol_page_timeout.png')
                print(f'IG 連線逾時: 重新嘗試第{i}次')
                logger.error(f'IG 連線逾時: 重新嘗試第{i}次 {e}')
                sleep(3)
                # raise f'連線逾時: {e}'
                continue

        # 擷取留言及子留言
        return Comment(output_json, page)

    loop = asyncio.get_event_loop() 
    loop.run_until_complete(_get_post_comment(page, postId, output_json))
    
    postData['comments'] = output_json
    
    return postData

async def basic_count(page, postId):

    async def get_basic_count(page, postId):

        for i in range(5):
            try:
                await page.goto(f"https://www.instagram.com/p/{postId}/")
                await page.wait_for_load_state('load')
                await page.wait_for_timeout(random.randint(4000,8000))
                break
            except TimeoutError as e:
                await page.screenshot(path='IG_kol_page_timeout.png')
                print(f'IG 連線逾時: 重新嘗試第{i}次')
                logger.error(f'IG 連線逾時: 重新嘗試第{i}次 {e}')
                sleep(3)
                # raise f'連線逾時: {e}'
        
        likes = await page.inner_text('//html/body/div[1]/section/main/div/div[1]/article/div[3]/section[2]/div/div/a/span')
        likes = int(likes)

        await press_more_comments(page)

        comments = await page.query_selector_all('//html/body/div[1]/section/main/div/div[1]/article/div[3]/div[1]/ul/ul')
        comment_count = 0

        if not comments == []:

            for c in comments:
                comment_count += 1
                more_replies_button = await c.query_selector('//li/ul/li/div/button/span')

                if more_replies_button:
                    button_text = await more_replies_button.inner_text()
                    replies_count = re.search(r'(\d+)', button_text).group(1)
                    comment_count += int(replies_count) 
        
        print(f'IG Comment_count:{comment_count} Likes:{likes}')

        return (likes, comment_count)
    
    loop = asyncio.get_event_loop()
    likes, comment_count = loop.run_until_complete(get_basic_count(page, postId))

    return (likes, comment_count)

async def get_post_context(page, postId):
    '''取得文案'''

    page.set_default_navigation_timeout(30000)
    for i in range(5):
        try:
            await page.goto(f"https://www.instagram.com/p/{postId}/")
            await page.wait_for_load_state('load')
            # await page.wait_for_load_state('domcontentloaded')
            # await page.wait_for_load_state('networkidle')
            print('IG 已進入粉專')
            break
        except TimeoutError as e:
            await page.screenshot(path='IG_TimeoutError1.png')
            print(f'IG: {postId} 連線逾時(未進入粉專) 嘗試第{i}次')
            logger.error(f'IG: {postId} 連線逾時(未進入粉專) 嘗試第{i}次')
            sleep(3)
            continue

    try:
        print('解析中')
        a_list = []
        await page.wait_for_selector('//html/body/div[1]/section/main/div/div[1]/article/div[3]/div[1]/ul/div/li/div/div/div[2]/span')
        all_a_text = await page.query_selector_all('//html/body/div[1]/section/main/div/div[1]/article/div[3]/div[1]/ul/div/li/div/div/div[2]/span/a')
        text = await page.inner_text('//html/body/div[1]/section/main/div/div[1]/article/div[3]/div[1]/ul/div/li/div/div/div[2]/span',timeout=0)
        
        for a in all_a_text:
            a = await a.inner_text()
            a_list.append(a)

        logger.info(f'IG: {postId} IG 已取得文案 https://www.instagram.com/p/{postId}/')
        return text, a_list

    except TimeoutError as e:
        await page.screenshot(path='IG_TimeoutError2.png')
        text = ''
        logger.error(f'IG 文案找不到標籤 請確認 IG 是否改版')
        return(None, None)
    
    finally:
        await page.close()