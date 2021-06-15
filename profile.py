import random
import asyncio
from requests_html import HTMLSession
import re
import os
import time
import pymongo
from dotenv import load_dotenv
from .utils.logger import Logger
from playwright.async_api import TimeoutError

# from logging import Logger
# logger = Logger(__name__)

from requests_html import AsyncHTMLSession
from requests import Session
from requests.auth import HTTPProxyAuth

load_dotenv()
logger = Logger()

class ProfileScraper:
    
    coll = pymongo.MongoClient(os.getenv('MONGOURI'))['NoxKol']['kol_ig']

    def __init__(self, session=None):
        if session is None:
            session = AsyncHTMLSession()
        
        self.session = session
        # self.session.headers.update({'Referer': os.getenv('BASE_URL'), 'user-agent': os.getenv('STORIES_UA')})
        self.session.headers.update({'user-agent': os.getenv('STORIES_UA')})

        
        # port_digits = [str(i) for i in range(301)]
        # self.port_digits = [(len(str(301))-len(digit))*'0'+digit for digit in port_digits]
        # self.port = random.choice(self.port_digits)
        
        # session.proxies = {'http':f'http://F3sqgQnqRoWA1xQD:wifi;us;at&t+u-verse;@proxy.soax.com:9{self.port}', 'https':f'https://F3sqgQnqRoWA1xQD:wifi;us;at&t+u-verse;@proxy.soax.com:9{self.port}'}

        # print(f'Request with proxy: {self.port}')

    def subscribers(self, url):

        async def get_subcribers(url):
            
            for i in range(15):
                
                try:
                    port_digits = [str(i) for i in range(301)]
                    port_digits = [(len(str(301))-len(digit))*'0'+digit for digit in port_digits]
                    port = random.choice(port_digits)
                    
                    self.session.proxies = {'http':f'http://F3sqgQnqRoWA1xQD:wifi;us;at&t+u-verse;@proxy.soax.com:9{port}', 'https':f'https://F3sqgQnqRoWA1xQD:wifi;us;at&t+u-verse;@proxy.soax.com:9{port}'}


                    resp = await self.session.get(url)
                    html = resp.html.html

                    if 'Login • Instagram' in html:
                        # old_port = self.port
                        # self.port = random.choice(self.port_digits)
                        # print(f'Change proxy {old_port} to {self.port }')
                        # self.session.proxies = {'http':f'http://F3sqgQnqRoWA1xQD:wifi;us;at&t+u-verse;@proxy.soax.com:9{self.port}', 'https':f'https://F3sqgQnqRoWA1xQD:wifi;us;at&t+u-verse;@proxy.soax.com:9{self.port}'}
                        
                        logger.info(f'IG 被導至登入畫面 重新嘗試第{i+1}次: {url}')
                        print(f'IG 被導至登入畫面 重新嘗試第{i+1}次: {url}')
                        time.sleep(1)
                        continue

                    subscribers = re.search(r'"edge_followed_by":{"count":(\d+)}', html).group(1)
                    
                    self.coll.update_one({'ig_url':url}, {'$set':{'subscribers':int(subscribers)}})

                    logger.info(f'IG {url}已更新訂閱數: {subscribers}')
                    print(f'IG {url}已更新訂閱數: {subscribers}')

                    return subscribers

                except pymongo.errors.PyMongoError as e:

                    print(f'kol_ig更新失敗: 該URL不存在於MongoDB {e}')
                    logger.error(f'IG {url} kol_ig更新失敗: 該URL不存在於MongoDB {e}')
                    return subscribers

                except AttributeError:
                    
                    print('IG 訂閱數擷取失敗 已記錄URl')
                    logger.error(f'IG {url} 訂閱數擷取失敗 已記錄URl')
                    
                    with open('ig_sub_error.html','w',encoding='utf-8') as f:
                        f.write(html)

                    return None
                
                finally:

                    await self.session.close()
                
        return self.session.run( lambda: get_subcribers(url))[0]

async def subscribers(page, url):

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

                return subscribers

            except TimeoutError as e:
                await page.screenshot(path='IG_sub_TimeoutError1.png')
                print(f'IG: {url} 連線逾時(未進入粉專) 嘗試第{i}次')
                logger.error(f'IG: {url} 連線逾時(未進入粉專) 嘗試第{i}次')
                time.sleep(1)

                continue

            except pymongo.errors.PyMongoError as e:
                logger.error(f'kol_ig更新失敗: 該URL不存在於MongoDB: {url}')
                print(f'kol_ig更新失敗: 該URL不存在於MongoDB {e}')
                return subscribers
            
    loop = asyncio.get_event_loop()
    subscribers = loop.run_until_complete(get_subcribers(page, url))

    return int(subscribers)

# a = ProfileScraper()
# a.subscribers('https://www.instagram.com/taidean/')