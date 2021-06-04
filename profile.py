import random
from requests_html import HTMLSession
import re
import os
import time
import pymongo
from dotenv import load_dotenv
from .utils.logger import Logger
from requests_html import AsyncHTMLSession

load_dotenv()
logger = Logger()

class ProfileScraper:
    
    coll = pymongo.MongoClient(os.getenv('MONGOURI'))['NoxKol']['kol_ig']

    def __init__(self, session=None):
        if session is None:
            session = AsyncHTMLSession()
            session.headers.update({'Referer': os.getenv('BASE_URL'), 'user-agent': os.getenv('STORIES_UA')})
            port = random.randint(1,300)
            session.proxies = {'http':f'http://F3sqgQnqRoWA1xQD:wifi;tw;@proxy.soax.com:9{port}', 'https':f'https://F3sqgQnqRoWA1xQD:wifi;tw;@proxy.soax.com:9{port}'}
        self.session = session

    def subscribers(self, url):

        async def get_subcribers(url):
            
            resp = await self.session.get(url)
            html = resp.html.html

            # with open('ig.html','w',encoding='utf-8') as f:
            #     f.write(resp.html.html)
            
            try:
                print(f'IG 已收到更新訂閱數請求 {url}')

                subscribers = re.search(r'"edge_followed_by":{"count":(\d+)}', html).group(1)
                
                self.coll.update_one({'ig_url':url}, {'$set':{'subscribers':subscribers}})

                logger.info(f'IG {url}已更新訂閱數: {subscribers}')
                print(f'IG {url}已更新訂閱數: {subscribers}')

                return subscribers

            except AttributeError:
                
                print('IG 訂閱數擷取失敗 已記錄URl')
                logger.error(f'IG {url} 訂閱數擷取失敗 已記錄URl')
                return None

            except pymongo.errors.PyMongoError as e:

                print(f'kol_ig更新失敗: 該URL不存在於MongoDB {e}')
                logger.error(f'IG {url} kol_ig更新失敗: 該URL不存在於MongoDB {e}')
                return subscribers
            
            finally:

                await self.session.close()
                
        return self.session.run( lambda: get_subcribers(url))[0]