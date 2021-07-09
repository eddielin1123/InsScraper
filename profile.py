# -*- coding: utf-8 -*-：
from logging import exception
import random
import asyncio
import aiohttp
from requests_html import HTMLSession
from requests_html import AsyncHTMLSession
from requests import Session
from requests.auth import HTTPProxyAuth
import re
import os
import time
import pytz
import datetime
import pymongo
from dotenv import load_dotenv
from .utils.logger import Logger
from playwright.async_api import TimeoutError
from user_agent import generate_user_agent, generate_navigator, generate_navigator_js

#? For testing
# from logging import Logger
# logger = Logger(__name__)

load_dotenv()
logger = Logger()


class ProfileScraper:
    
    coll = pymongo.MongoClient(os.getenv('MONGOURI'))['NoxKol']['kol_ig']
    utc_now = datetime.datetime.now(tz=pytz.timezone('UTC')).astimezone(pytz.timezone('Asia/Taipei'))

    def __init__(self, session=None):
        # if session is None:
        #     session = HTMLSession()
        
        # self.session = session
        # self.session.headers.update({'Referer': os.getenv('BASE_URL'), 'user-agent': os.getenv('STORIES_UA')})
        # self.session.headers.update({'user-agent': os.getenv('STORIES_UA')})
        
        self.sub_count= None
        self.html = ''

    def subscribers(self, url):
        #* Async scraper for subscribers count

        async def main(self, url):
            try:
                # Random proxy port
                port_digits = [str(i) for i in range(301)]
                port_digits = [(len(str(301))-len(digit))*'0'+digit for digit in port_digits]
                port = random.choice(port_digits)
                proxy = f'http://F3JZJYifgvqVCHbd:wifi;@proxy.soax.com:9{port}'

                # Random Hearders
                # headers = generate_navigator()
                user_agent = generate_user_agent()
                # headers.update({'User-Agent':user_agent})


                # Start request
                async with aiohttp.ClientSession(headers={'User-Agent':user_agent}) as session:
                    async with session.get(url, proxy=proxy, allow_redirects=False) as response:
                        html = await response.text()

                        if 'Login • Instagram' in html: 
                            await asyncio.sleep(5)
                            return None

                        # with open('ig_sub.html','w',encoding='utf-8') as f:
                        #     f.write(html)
                        
                        # Get subscribers count 
                        self.sub_count = re.search(r'"edge_followed_by":{"count":(\d+)}', html).group(1)
                        self.sub_count = int(self.sub_count)
                        # Update subscriers count in MongoDB
                        # self.coll.update_one({'ig_url':url}, {'$set':{'subscribers':int(self.sub_count)}})

                        return int(self.sub_count)

            except AttributeError as e:
                await asyncio.sleep(10)
                return None

            except TypeError as e:
                await asyncio.sleep(10)
                return None

            except Exception:
                return None

        async def task_manager():
            #* Cancel others tasks when first task completed 

            tasks = [main(self, url) for i in range(10)]
            while tasks:
                finished, unfinished = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for x in finished:
                    result = x.result()
                    print(f"Finished task produced {result!r}")
                    if result:
                        print(f"Cancelling {len(unfinished)} remaining tasks")
                        for task in unfinished:
                            task.cancel()
                        await asyncio.wait(unfinished)
                        return result

                tasks = unfinished

        # tasks = [main(self, url) for i in range(10)]
        # loop.run_until_complete(asyncio.wait(tasks))
        loop = asyncio.get_event_loop()
        loop.run_until_complete(task_manager())

        if self.sub_count is None:
            print('IG 訂閱數擷取失敗 已記錄URl')
            logger.error(f'IG {url} 訂閱數擷取失敗')
        else:
            self.coll.update_one({'ig_url':url}, {'$set':{'subscribers':int(self.sub_count), 'updated_at':self.utc_now}})
            logger.info(f'IG {url}已更新訂閱數: {self.sub_count}')
            print(f'IG {url}已更新訂閱數: {self.sub_count}')

        return self.sub_count
    



async def subscribers(page, url):
    #* get subscribers count with browser

    async def get_subcribers(page, url):
        '''取得訂閱數'''

        page.set_default_navigation_timeout(30000)
        for i in range(5):
            try:
                await page.goto(url)
                await page.wait_for_load_state('load')
                # await page.wait_for_load_state('domcontentloaded')
                # await page.wait_for_load_state('networkidle')
                
                html = await page.content()
                subscribers = re.search(r'"edge_followed_by":{"count":(\d+)}', html).group(1)
                
                coll = pymongo.MongoClient(os.getenv('MONGOURI'))['NoxKol']['kol_ig']
                coll.update_one({'ig_url':url}, {'$set':{'subscribers':int(subscribers)}})

                logger.info(f'IG {url}已更新訂閱數: {subscribers}')
                print(f'IG {url}已更新訂閱數: {subscribers}')

                await page.wait_for_timeout(random.randint(2000,4000))

                return subscribers

            except TimeoutError as e:
                await page.screenshot(path='IG_sub_TimeoutError1.png')
                print(f'IG: {url} 連線逾時(未進入粉專) 嘗試第{i}次')
                logger.error(f'IG: {url} 連線逾時(未進入粉專) 嘗試第{i}次')
                time.sleep(1)
                continue

            except AttributeError as e:
                await page.screenshot(path='IG_sub_Error.png')
                print(f'IG: {url} 擷取訂閱數失敗 嘗試第{i}次')
                logger.error(f'IG: {url} 擷取訂閱數失敗 嘗試第{i}次')
                with open('ig_sub_error.html','w',encoding='utf-8') as f:
                    f.write(html)

            except pymongo.errors.PyMongoError as e:
                logger.error(f'kol_ig更新失敗: 該URL不存在於MongoDB: {url}')
                print(f'kol_ig更新失敗: 該URL不存在於MongoDB {e}')
                return subscribers
            
    loop = asyncio.get_event_loop()
    subscribers = loop.run_until_complete(get_subcribers(page, url))

    return int(subscribers)

# a = ProfileScraper()
# a.subscribers('https://www.instagram.com/taidean/')