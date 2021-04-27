import inspect
import os
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)

from utils import Utils
import re
import asyncio
import random
from time import sleep, time
from mongo import get_ig_id_url

class Parser:
    '''
    取得以下資訊並更新至MongoDB:
        - 追蹤數
    '''
    def __init__(self):
        self.s = Utils().login()
        self.ig_list = get_ig_id_urls()
        
    async def _follow_extract(self,html):
        '''找到追蹤數的正則式'''
        regex0 = re.compile(r'"userInteractionCount":"(\d+)"')
        regex1 = re.compile(r'"edge_followed_by":{"count":(\d+)}')
        s_0 = regex0.search(html)
        s_1 = regex1.search(html)
        if not s_0 == None:
            return s_0.group(1)
        elif not s_1 == None:
            return s_1.group(1)
        else:
            return 'none'
    
    async def _followrs_task(self,i, asyncio_semaphore):
        '''
        使用異步取得追蹤數
        
        input: i:tuple, asyncio_semaphore:any
        output: None
        '''
        async with asyncio_semaphore:
            user_id = i[1]
            url = i[0]
            
            html = self.s.get(url).text
            follow_count = await self._follow_extract(html)
            name = url.split('com/')[1].replace('/','')
            print(f'{name} has {follow_count} followers')
            
            sleep(random.uniform(2,7))
            
    
    async def _f_bounded(self, mongo_info):
        asyncio_semaphore = asyncio.BoundedSemaphore(2)
        jobs = []
        for i in mongo_info:
            jobs.append(asyncio.ensure_future(self._followrs_task(i, asyncio_semaphore)))
        await asyncio.gather(*jobs)

    def folower(self,mongo_info):
        loop = asyncio.get_event_loop()
        loop.set_debug(True)
        loop.run_until_complete(self._f_bounded(mongo_info))
        
if __name__ == '__main__':
    mongo_info = [i for i in get_ig_id_url()] # (id, url)
    Parser().folower(mongo_info)
