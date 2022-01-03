import logging
import re
from pymongo import results
import requests
from requests_html import HTMLSession
from datetime import datetime
from time import sleep
from urllib.parse import quote
import json
import random
from requests.exceptions import ProxyError
import asyncio
import aiohttp
from pprint import pprint
from datetime import datetime
from dotenv import load_dotenv
import pymongo
import os
import emoji
import pytz
from .dataClass import commentNode, sharedData
from . import logger
from .util import (
    get_comment_text,
    word_cloud,
    upload_on_aws,
    word_frequency
)

print(logging.getLevelName(logger.getEffectiveLevel()))

load_dotenv()
MONGO = pymongo.MongoClient(os.getenv('MONGOURI'))[os.getenv('MONGO_COLL')]['kol_ig']
BASE_URL = 'https://www.instagram.com'
STATUS = None
REFERER = None
API_PARAMS = '?__a=1' #!
PARENT_COMMENT_HASH = 'bc3296d1ce80a24b1b6e40b1e72903f5'
THREAD_COMMENT_HASH = '1ee91c32fc020d44158a3192eda98247'
HASH_JS = 'https://www.instagram.com/static/bundles/es6/ConsumerLibCommons.js/6d04e3c92d66.js' 
COMMENT_JS = 'https://www.instagram.com/static/bundles/es6/Consumer.js/20e41358f066.js'
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'


SHARED_DATA_REG = re.compile(r'window._sharedData = (\{.*\});')
USER_REG = re.compile(r'\(?@(.*?)\)? ')
UNAME_REG = re.compile(r'<meta property="og:title" content="@?(.*?) ')
HASH_REG = re.compile(r'threadedComments\.parentByPostId.get\(n\)\.pagination,queryId:"(.*?)"')
USERID_REG = re.compile(r'"instapp:owner_user_id" content="(\d+)"')  
USERID_REG1 = re.compile(r'"logging_page_id":"profilePage_(\d+)"')
HTAG_HTML_REG = re.compile(r'"instapp:hashtags" content="(.*?)"')
HTAG_HTML_REG1 = re.compile(r'[\s\n](#(?![\s|@]))')
TAG_CONTEXT_REG = re.compile(r'\s?(@(?![\s|@])(?!gmail)(?!yahoo)(?!outlook)(?!hotmail).*?)\s')
TAG_CONTEXT_REG1 = re.compile(r'(@(?![\s|@])\S*?)$')
URL_REG = re.compile(r'(https?://.*?) ')
XSRF = None


class InsPostScraper:
    '''
    抓取IG貼文
    '''
    
    default_headers = {
        'Accept-Language': 'en-US',
        'User-Agent': USER_AGENT,
        'Sec-Fetch-User': '?1',
        'sec-fetch-dest':'document'
    }
    
    def __init__(self, session=None, proxy=False):
        if session is None:
            self.session = HTMLSession()
        else:
            self.session = session
            
        if proxy:
            self.session.proxies = self._rotate_proxy()
            
        self.session.headers.update(self.default_headers)
        self.session.trust_env = False
        self.proxy = self.session.proxies
        self.params = None
        self.cs_cookies = None
        self.html = None
        self.post_json = None
        self.is_login = False
        # self.csrf_token = self._get_csrf()

    def login(self, username, password): #peng_2415316 #wendy0519
        login_url = 'https://www.instagram.com/accounts/login/ajax/'
        time = int(datetime.now().timestamp())
        payload = {
                    'username': f'{username}',
                    'enc_password': f'#PWD_INSTAGRAM_BROWSER:0:{time}:{password}',
                    'queryParams': {},
                    'optIntoOneTap': 'false'
                    }
        resp = self.session.post(login_url,
                            data=payload, 
                            headers={
                                "User-Agent": USER_AGENT,
                                "X-Requested-With": "XMLHttpRequest",
                                "Referer": "https://www.instagram.com/accounts/login/",
                                "x-csrftoken": self.csrf_token
                            })
        status = json.loads(resp.html.html)
        
        if status['authenticated'] is True and status.get('oneTapPrompt'):
            self.is_login = True
            logger.info(f'IG 登入成功: {status}')
        else:
            logger.error(f'IG 登入失敗: {status}')

    def get(self, url:str, cookies:str=None, params:str=None) -> str:
        for i in range(10):
            self.session.proxies = self._rotate_proxy()
            try:
                resp = self.session.get(url, params=params)
                status = resp.status_code
                html = resp.html.html
                
                if not cookies is None:
                    self.session.cookies = cookies
                
                if 'Login • Instagram' in html:
                    logger.warning(f'要求登入 | retry:{i}')
                    continue
                elif status != 200:
                    logger.debug(html)
                    logger.warning(f'訪問失敗 Status:{status} | retry:{i}')
                    continue
                else:
                    logger.debug(f'Request {url}')
                    return html                    
                
            except ProxyError as e:
                logger.exception(f'Proxy Error | retry:{i}')
                continue
    
    def get_profile(self, postUrl:str):
        user = postUrl.split('com/')[1].split('/')[0]
        api_url = f'{BASE_URL}/{user}/{API_PARAMS}'
        html = self.async_get(api_url)
        api_json = json.loads(html)
        
        page_description = api_json.get('description', None)
        if page_description:
            if 'You must be 13 years old' in page_description:
                logger.error('訪問錯誤: 該帳號有年齡訪問限制')
                return {'description':page_description}
        try:
            followers = api_json['graphql']['user']['edge_followed_by']['count']
            self._update_db(postUrl, followers)
            logger.info(f'IG 訂閱數 更新成功:{followers} {postUrl}')
            return {'subscribers':followers}
        except Exception:
            logger.exception('get_profile exception')
            return None
        
    def post_info(self, postId:str):
        api_url = f'{BASE_URL}/p/{postId}/{API_PARAMS}'
        html = self.get(api_url)
        with open('ig_basic_info.html', 'w', encoding='utf-8') as f:
            f.write(html)
        api_json = json.loads(html)
        post = self.post_json = api_json['graphql']['shortcode_media']

         # 讚數
        likes = int(post['edge_media_preview_like']['count'])
        
        # 留言數
        comments = int(post['edge_media_preview_comment']['count'])

        # 追蹤數
        followers = int(post['owner']['edge_followed_by']['count'])

        logger.info(f'likes:{likes} | comments:{comments} | followers:{followers}')
        logger.info(f'IG 每日曲線 擷取成功:{postId}')

        return {'likes':likes,
                'comments':comments,
                'followers':followers}
                
    def get_post(self, postId:str) -> dict:
        
        url = f'{BASE_URL}/p/{postId}/'
        api_url = f'{BASE_URL}/p/{postId}/{API_PARAMS}'
        html = self.get(api_url)
        api_json = json.loads(html)

        # html = self.html = self.get(url)
        post = self.post_json = api_json['graphql']['shortcode_media']
        hyperlinks_info = []

        # 貼文
        post_context = post['edge_media_to_caption']['edges'][0]['node']['text']
        post_context = self._strQ2B(post_context)
        post_context = self._htag_normalize(post_context)

        # #標籤
        # htags = ['#' + tag for tag in HTAG_HTML_REG.findall(html)]
        htags = self._extract_hash_tag(post_context)

        # @標記
        tags = TAG_CONTEXT_REG.findall(post_context)
        if TAG_CONTEXT_REG1.search(post_context):
            tag_end = TAG_CONTEXT_REG1.search(post_context).group(1)
            tags.append(tag_end)
        
        # 網址
        url_ = URL_REG.findall(post_context)
        
        # 讚數
        likes = int(post['edge_media_preview_like']['count'])
        
        # 留言數
        comments = int(post['edge_media_preview_comment']['count'])
        
        hyperlinks = htags + tags + url_
        hyperlinks = list(hyperlinks)
        
        if len(tags) > 0: # 訪問@帳號
            self._tag_request(tags, hyperlinks_info)
        
        logger.info(f'htag:{hyperlinks} | tag:{hyperlinks_info}')
        logger.info(f'IG 文案 擷取成功:{postId}')

        return {'context':post_context,
                'hyperlinks':hyperlinks,
                'hyperlinks_info':hyperlinks_info}
    
    def _comments_iter(self, postId:str, cursor:str=None):
        '''
        敘述: 留言換頁產生器
        
        Params:
            postId: IG文章編號
            cursor: 下一頁所需Cursor, 預設為None
        
        '''
        
        url = REFERER = f'{BASE_URL}/p/{postId}/'
        page = 1
        has_next_page = True
        
        end_cursor = cursor
        while has_next_page:
            params = {
                'query_hash':PARENT_COMMENT_HASH, # Hash為固定
                'variables':json.dumps({"shortcode":postId,"first":12,"after":end_cursor})
            }
            if page > 1:
                url = f'{BASE_URL}/graphql/query/'
                response = self.get(url, params=params)
            else:
                response = self.get(url) # 第一頁無須帶Params
            
            with open(f'./ig_page{page}.html', 'w', encoding='utf-8') as f:
                f.write(response)
                
            try:
                api_json = json.loads(response) # 預設response為json，若為HTML則進入Exception另外萃取
                shared_data = sharedData(api_json)
                
            except Exception:
                init_json = self._init_data(postId, response)
                shared_data = sharedData(init_json)

            if not len(shared_data.comments) > 1:
                break
            
            for i, comment in enumerate(shared_data.comments): # 確認子留言存在 並while迭代取出
                try:
                    end_cursor = comment['node']['edge_threaded_comments']['page_info']['end_cursor']
                except KeyError:
                    end_cursor = None
                
                while end_cursor: # 子留言換頁
                    params = {
                                'query_hash':THREAD_COMMENT_HASH, # Hash為固定
                                'variables':json.dumps({"comment_id":comment['node']['id'], "first":6, "after":end_cursor})
                            }
                    url = f'{BASE_URL}/graphql/query/'
                    response = self.get(url, params=params)
                    try:
                        replies_data = sharedData(json.loads(response))
                    except Exception:
                        replies_data = sharedData(self._init_data(postId, response))

                    replies = replies_data.comments
                    shared_data.comments[i]['node']['edge_threaded_comments']['edges'].extend(replies) # 將子留言node回存至母留言的json
                    
                    end_cursor = replies_data.end_cursor
            
            yield shared_data.comments # -> List

            next_cursor = shared_data.end_cursor # 下一頁cursor
            logger.debug(f'next_cursor: {next_cursor}')
            
            if next_cursor == end_cursor: # 避免IG重複翻頁顯示相同內容
                logger.warning('end_cursor重複 換頁終止')
                break

            end_cursor = next_cursor
            has_next_page = shared_data.has_next_page

            logger.debug(f'page: {page} done')
            page += 1
            sleep(random.uniform(2, 3))

    
    def _comment_content(self, comment:commentNode):
        '''
        敘述: 回傳單筆留言內容
        
        Params:
            comment: dataClass.py內的commentNode物件
        '''
        return {
                    'author':comment.author,
                    'thumbnail':comment.thumbnail,
                    'context':comment.context,
                    'likes':comment.likes,
                    'published_time':datetime.fromtimestamp(comment.timestamp)
                }
            
    def get_comments(self, postId:str):
        '''
        敘述: 取得文章所有留言的主方法
        
        Params:
            postId: IG文章編號
        '''
        global REFERER                
        c_count = 0
        output_json = []
        
        self._is_login() # 確認登入
        
        for comments in self._comments_iter(postId): # 呼叫換頁產生器
            for comment in comments: # 迭代所有留言
                comment_ = commentNode(comment['node'])
                comment_dict = self._comment_content(comment_)
                replies = []
                if len(comment_.sub_comments) > 1: # 確認子留言存在
                    for reply in comment_.sub_comments:
                        reply_node = commentNode(reply['node'])
                        reply = self._comment_content(reply_node)
                        replies.append(reply)
                        c_count += 1
                comment_dict.update({'replies':replies})
                output_json.append(comment_dict)
                c_count += 1
        all_text = get_comment_text(output_json)
        print(all_text)
        ranked_freq, origin_freq = word_frequency(all_text)
        image_path = word_cloud(origin_freq, file_name='word_cloud.png')
        wd_url = upload_on_aws(origin_url=postId, local_file=image_path) if all_text else None
        
        logger.info(f'IG 留言 擷取成功:{postId} 共有{c_count}筆')
        return {
            'comments':output_json,
            'wordcloud_url':wd_url,
            'word_frequency':ranked_freq
            }

    def find_all_posts(self, url):
        #! 傳入網址只能是Profile page
        #TODO 一段時間的全部貼文 待開發
        
        postId = url.split('/p/')[1].split('/')[0]
        url = BASE_URL + '/p/' + postId
        # html = self.get(url)
        html = self.async_get(url)
        # with open("ig_debug.html", "w") as f:
        #     f.write(html)
            
        basic_info = self._basic_info(postId, html)
        user = basic_info['user']
        user_name = basic_info['user_name']
        user_id = basic_info['user_id']
        print(user, user_name, user_id)
        
        html = self.get(HASH_JS)
        hash = HASH_REG.search(html).group(1)
        
        # print(hash)
        variable = f'{{"id":"{user_id}","first":12}}'
        variable = quote(variable)
        # print(variable)
        json_url = f'https://www.instagram.com/graphql/query/?query_hash={hash}&variables={variable}'
        # html = self.get(json_url)
        html = self.async_get(json_url)
        # with open("ig_debug2.html", "w") as f:
        #     f.write(html)
        all_post_json = json.loads(self.get(json_url))
        pass            
    
    def _find_post(self, all_post_json, json_url, postId):
        #* 不斷訪問下一頁 直到找到該指定貼文
        
        page = 0
        post_json = None
        page = all_post_json['data']['user']['edge_owner_to_timeline_media']
        posts = page['edges']
        has_next_page = page['page_info']['has_next_page'] # Booling
        
        while True:
            for post in posts:
                if post['node']['shortcode'] == postId:
                    post_json = post['node']
                    return post_json
            
            if has_next_page and post_json is None:
                print('Found next page')
                end_curosr = page['page_info']['end_cursor']
                next_url = json_url + f'&end_cursor={end_curosr}'
                html = self.async_get(next_url)
                post_json = json.loads(html)
                for post in posts:
                    if post['node']['shortcode'] == postId:
                        post_json = post['node']
                        return post_json
    
    def _htag_normalize(self, text):
        '''解決IG多空格會自動取代成一空格'''
        def sub_repl_rule(match):
            text = match.group(1)
            text = re.sub(r' +', ' ', text)
            return text

        regex = re.compile(r'(#(?![\s|@])\S+\s{0,})')
        return  re.sub(regex, sub_repl_rule, text)

    def _extract_hash_tag(self, text):
        htags = []
        text = emoji.demojize(text, delimiters=(" ;;", ";;")) # remove emoji
        text_groups = re.split(r'\\n|\s|\\|"', text) # split with space or break line or some shit
        for t in text_groups:
            regex = re.compile(r'([#＃](?![\s|@])\w+(?![\\"#]))')
            results = regex.findall(t)
            if len(results) > 0:
                htags.extend(results)
        return htags

    def _tag_request(self, tags:str, hyperlinks_info:list) -> dict:
        
        for tag in tags:
            try:
                user_id = tag.split('@')[1]
                url = f'{BASE_URL}/{user_id}/'
                html = self.get(url)
                shared_data = self._shared_data(html)
                full_name = shared_data['entry_data']['ProfilePage'][0]['graphql']['user']['full_name']
                # basic_info = self._basic_info(url, html)
                hyperlinks_info.append({'tag':tag, 'user_name':full_name})
            except TypeError:
                continue
            except AttributeError:
                continue
            
    def _basic_info(self, postId:str, html:str) -> dict:
        #! not in use for now
        user = None
        user_name = None
        user_id = None
        
        if self.is_login:
            print('IG 已登入')
            init_json = self._init_data(postId, html)
            user_id = init_json['graphql']['shortcode_media']['owner']['id']
            user_name = init_json['graphql']['shortcode_media']['owner']['username']
        else:
            print('IG 未登入')
            user = USER_REG.search(html).group(1)
            user_name = UNAME_REG.search(html).group(1)
            
            for user_id in [USERID_REG, USERID_REG1]:
                try:
                    user_id = user_id.search(html).group(1)
                    break
                except AttributeError:
                    continue
            
            basic_info = {'user':user, 'user_name':user_name, 'user_id':user_id}
            
        return basic_info
    
    def async_get(self, url:str, params=None) -> str: #html 
        #* Async scraper for subscribers count

        async def main(url):
            global BASE_URL, REFERER, XSRF
            headers = {'User-Agent':USER_AGENT}
            
            try:
                # Random proxy port
                proxy = self._rotate_proxy(async_access=True)
                
                if not REFERER is None:
                    # referer = REFERER
                    headers.update({'Referer':REFERER})
                    print(REFERER)
                else:
                    # referer = BASE_URL
                    headers.update({'Referer':BASE_URL})
                    
                if XSRF:
                    headers.update({'x-csrftoken':XSRF})
                    
                # Start request
                async with aiohttp.ClientSession(trust_env=False, headers=headers) as session:
                    # if not self.cs_cookies is None:
                    #     session.cookie_jar = self.cs_cookies
                    async with session.get(url, proxy=proxy, params=params) as response:
                        raw_html = await response.text()
                        if 'Login • Instagram' in raw_html or '登入 • Instagram' in raw_html: 
                            logger.debug('async_get: 要求登入頁面')
                            await asyncio.sleep(10)
                            return None
                        elif not response.status == 200:
                            STATUS = response.status
                            logger.debug(f'Error Status: {STATUS}')
                            await asyncio.sleep(10)
                            return None

                        self.html = raw_html
                        logger.debug(f'Request: {url}')
                        # self.cs_cookies = session.cookie_jar.filter_cookies("https://www.instagram.com")
                        return 'Done'

            except Exception:
                await asyncio.sleep(10)
                return None
            

        async def task_manager():
            #* Cancel others tasks when first task completed 

            tasks = [main(url) for i in range(20)]
            while tasks:
                finished, unfinished = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for x in finished:
                    result = x.result()
                    # print(f"Finished task produced {result!r}")
                    if result:
                        # print(f"Cancelling {len(unfinished)} remaining tasks")
                        for task in unfinished:
                            task.cancel()
                        await asyncio.wait(unfinished)
                        return result

                tasks = unfinished

        loop = asyncio.get_event_loop()
        loop.run_until_complete(task_manager())

        return self.html
    
    def _is_login(self):
        res = self.session.get('https://www.instagram.com/accounts/edit/')
        html = res.html.html
        
        if 'ds_user_id' not in self.session.cookies:
            logger.info('IG 登入cookies遺失')
        if 'Login • Instagram' in html:
            logger.info(f'IG 尚未登入')

    @staticmethod
    def _strQ2B(text):
        """轉換全形htag/tag"""
        text = text.replace('＠', '@')
        text = text.replace('＃', '#')
        return text

    @staticmethod              
    def _get_csrf():
        link = 'https://www.instagram.com/accounts/login/'
        resp = requests.get(link, headers={'User-Agent':'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36'})
        csrf = re.findall(r'csrf_token":"(.*?)"', resp.text)[0]
        return csrf
    
    @staticmethod
    def _init_data(postId, html):
        #* page data with login mode
        #TODO 含有貼文相關資訊 之後可視情況應用
        
        init_data_reg_0 = re.compile(r'window.__additionalDataLoaded\(\'/p/{0}/\',(.*}}}}}}}})'.format(postId))
        init_data_reg_1 = re.compile(r'window\._sharedData = (\{.*\});<\/script>')
        
        result_0 = init_data_reg_0.search(html)
        result_1 = init_data_reg_1.search(html)
        result = result_0 or result_1
                
        init_data = result.group(1)
        init_json = json.loads(init_data)
        assert isinstance(init_json, dict)
        return init_json
    
    
    
    @staticmethod
    def _shared_data(html):
        #* profile page
        #TODO other information inside might be useful
        
        shared_data = SHARED_DATA_REG.search(html).group(1)
        shared_json = json.loads(shared_data)
        
        assert isinstance(shared_json, dict)
        return shared_json
    
    @staticmethod
    def _rotate_proxy(async_access=False):
        proxy = random.choice([f'F3JZJYifgvqVCHbd:wifi;@proxy.soax.com:{n}'for n in range(9000, 9401)])
        proxies = {'http':f'http://{proxy}', 'https':f'https://{proxy}'}
        
        if async_access:
            proxies = f'http://{proxy}'
        logger.debug(f'Using proxy: {proxy}')
        return proxies
    
    @staticmethod
    def _update_db(url, sub_count):
        utc_now = datetime.now(tz=pytz.timezone('UTC')).astimezone(pytz.timezone('Asia/Taipei'))
        MONGO.update_many({'ig_url':url}, {'$set':{'subscribers':int(sub_count), 'updated_at':utc_now}})

