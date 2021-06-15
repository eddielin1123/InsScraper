import asyncio
import random
import nest_asyncio
from .logger import Logger
import os
logger = Logger()

nest_asyncio.apply()


def Comment(output_json, page):
    #* 執行協程 (_get_comments)
    
    asyncio.run(_get_comments(output_json, page))


async def _get_comments(output_json, page):
    #* 包裝協程任務
    
    # 點擊更多留言    
    await press_more_comments(page)
    
    # 所有留言選擇器
    print('開始擷取留言')
    comments = await page.query_selector_all('//html/body/div[1]/section/main/div/div[1]/article/div[3]/div[1]/ul/ul') # -> List
    if not comments == []:
        cmts_idx = [(i, c) for i, c in enumerate(comments)] 

        # 點開所有子留言
        for c in comments:
            more_replies_button = await c.query_selector('//li/ul/li/div/button/span')
            if more_replies_button:
                c_qs = await c.query_selector('//div/li/div/div[1]/div[2]/span')
                comment = await c_qs.inner_text()
                # print(f'{comment} 有子留言')

                # 點擊 顯示更多留言
                await _press_more_replies(more_replies_button, c, page) 

    elif len(comments) == 1:
        cmts_idx = [(i, c) for i,c in enumerate(list(comments))] 

        # 點開所有子留言
        for c in comments:
            more_replies_button = await c.query_selector('//li/ul/li/div/button/span')
            if more_replies_button:
                c_qs = await c.query_selector('//div/li/div/div[1]/div[2]/span')
                comment = await c_qs.inner_text()
                # print(f'{comment} 有子留言')

                # 點擊 顯示更多留言
                await _press_more_replies(more_replies_button, c, page) 
    else:
        await page.screenshot(path='IG_comment_not_found.png')
        print('找不到主留言')
        return comments
        

    async def __handler(output_json, page, i, c):
        #* 巢狀協程任務
        
        # 留言資料選擇器
        c_qs = await c.query_selector('//div/li/div/div[1]/div[2]/span')
        ca_qs = await c.query_selector('//div/li/div/div[1]/div[2]/h3/div[1]/span/a')
        time_qs = await c.query_selector('//div/li/div/div[1]/div[2]/div/div/a/time')
        l_qs = await c.query_selector('//div/li/div/div[1]/div[2]/div/div/button[1]')

        # 選擇器轉換文字
        comment = await c_qs.inner_text() # 留言
        time_s = await time_qs.inner_text() # 時間
        likes = await l_qs.inner_text() # 讚數
        comment_author = await ca_qs.inner_text() # 作者 
        thumbnail = await page.get_attribute(f'//html/body/div[1]/section/main/div/div[1]/article/div[3]/div[1]/ul/ul[{str(i+1)}]/div/li/div/div[1]/div[1]/div/a/img','src') # 頭像
        likes = int(likes.replace('likes', '').replace('like', '').strip()) if not 'Reply' in likes else 0

        # 取得子留言
        more_replies_button = await c.query_selector('//li/ul/li/div/button/span')
        if more_replies_button:
            replies = await _get_replies(page, i, c)
        else:
            replies = []

        # 將 留言 及 子留言 存入List 以便後續轉Json
        output_json.append(
            {
                'author':comment_author,
                'thumbnail':thumbnail,
                'context':comment,
                'likes':likes,
                'published_time':time_s,
                'replies':replies
                
            })
        
    tasks = [__handler(output_json, page, i, c) for i, c in cmts_idx]
    await asyncio.gather(*tasks)


async def _get_replies(page, i, c):
    #* 擷取子留言
    
    replies =[]
        
    # TODO 將以下 迴圈 優化成 協程
    replies_selector = await c.query_selector_all('//li/ul/div') 
    for idx, r in enumerate(replies_selector):
        
        rtext = await r.query_selector('//li/div/div[1]/div[2]/span')
        rauthor = await r.query_selector('//li/div/div[1]/div[2]/h3/div[1]/span/a')
        rlikes = await r.query_selector('//li/div/div[1]/div[2]/div/div/button[1]')
        rtime = await r.query_selector('//li/div/div[1]/div[2]/div/div/a/time')
        
        reply_author = await rauthor.inner_text()
        reply_thumbnail = await page.get_attribute(f'//html/body/div[1]/section/main/div/div[1]/article/div[3]/div[1]/ul/ul[{str(i+1)}]/li/ul/div[{str(idx+1)}]/li/div/div[1]/div[1]/div//img','src')
        reply_text = await rtext.inner_text()
        reply_likes = await rlikes.inner_text()
        reply_likes = int(reply_likes.replace('likes', '').replace('like', '').strip()) if not 'Reply' in reply_likes else '0'
        reply_time = await rtime.inner_text()
        
        # 存入 list
        replies.append(
            {
                'author':reply_author,
                'thumbnail':reply_thumbnail,
                'context':reply_text,
                'likes':reply_likes,
                'published_time':reply_time
                })

    return replies if not replies == [] else None

async def _press_more_replies(more_replies_button, c, page): 
    #* 點擊 顯示更多子留言 

    t = await more_replies_button.inner_text()

    while 'View replies' in t:  
        more_replies_button = await c.query_selector('//li/ul/li/div/button/span')

        if more_replies_button:
            await more_replies_button.click()
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(random.randint(2000,3000))
            t = await more_replies_button.inner_text()
        else:
            print('找不到 顯示更多子留言 按鈕')
            logger.error('找不到 顯示更多子留言 按鈕')

    #! 此處不可寫page.wait_for_load_state('load')
    

async def press_more_comments(page):
    #* 點擊 顯示更多留言 
    
    last_c = () 

    while await page.is_visible('//html/body/div[1]/section/main/div/div[1]/article/div[3]/div[1]/ul/li/div/button'):
        await page.click('//html/body/div[1]/section/main/div/div[1]/article/div[3]/div[1]/ul/li/div/button')
        await page.wait_for_timeout(random.randint(2000,3000))
        last_comment = await page.inner_text('//html/body/div[1]/section/main/div/div[1]/article/div[3]/div[1]/ul/ul[last()]/div/li/div/div[1]/div[2]/span')
        last_c += (last_comment,)
        
        if len(last_c) > 1 and last_c[-1] == last_c[-2]:
            break
    await page.wait_for_load_state('load')