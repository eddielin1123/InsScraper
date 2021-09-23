import re
from numpy import histogram_bin_edges
import requests
from requests_html import HTMLSession
from datetime import datetime
from time import sleep
from urllib.parse import urlencode, quote
import json
import random
from requests.exceptions import ProxyError
import asyncio
import aiohttp
from pprint import pprint
from datetime import datetime
from .utils.logger import Logger
from dotenv import load_dotenv
import pymongo
import os
import emoji
import pytz
from .dataClass import commentNode, sharedData
load_dotenv()
logger = Logger()

MONGO = pymongo.MongoClient(os.getenv('MONGOURI'))[os.getenv('MONGO_COLL')]['kol_ig']

BASE_URL = 'https://www.instagram.com'
STATUS = None
REFERER = None
API_PARAMS = '?__a=1' #!
PARENT_COMMENT_HASH = 'bc3296d1ce80a24b1b6e40b1e72903f5'
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
    def __init__(self, session=None, proxy=False):
        if session is None:
            session = HTMLSession()
        if proxy:
            session.proxies = self._rotate_proxy()
        
        self.session = session
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
            print(f'IG 登入成功: {status}')
            print(self.session.cookies)
        else:
            print(f'IG 登入失敗: {status}')

    def get(self, url:str, cookies:str=None, params:str=None) -> str:
        for i in range(10):
            try:
                port_digits = [str(i) for i in range(401)]
                port_digits = [(len(str(401))-len(digit))*'0'+digit for digit in port_digits]
                port = random.choice(port_digits)
                
                if self.proxy:
                    self.session.proxies = {'http':f'http://F3JZJYifgvqVCHbd:wifi;@23.109.55.164:9{port}', 'https':f'https://F3JZJYifgvqVCHbd:wifi;tw;@23.109.55.164:9{port}'}
                
                resp = self.session.get(url, params=params)
                status = resp.status_code
                html = resp.html.html
                
                if not cookies is None:
                    self.session.cookies = cookies
                
                if not 'Login • Instagram' in html and status == 200:
                    return html
                
            except ProxyError as e:
                continue
    
    def get_profile(self, postUrl:str):
        user = postUrl.split('com/')[1].split('/')[0]
        api_url = f'{BASE_URL}/{user}/{API_PARAMS}'
        # print(api_url)
        html = self.async_get(api_url)
        # print(html.encode)
        api_json = json.loads(html)
        try:
            followers = api_json['graphql']['user']['edge_followed_by']['count']
            self._update_db(postUrl, followers)

            logger.info(f'IG 訂閱數 更新成功:{followers} {postUrl}')
            print(f'IG 訂閱數 更新成功:{followers} {postUrl}')
            return {'subscribers':followers}
        except Exception:
            return None
        
    def post_info(self, postId:str):
        api_url = f'{BASE_URL}/p/{postId}/{API_PARAMS}'
        html = self.async_get(api_url)

        api_json = json.loads(html)
        post = self.post_json = api_json['graphql']['shortcode_media']

         # 讚數
        likes = int(post['edge_media_preview_like']['count'])
        
        # 留言數
        comments = int(post['edge_media_preview_comment']['count'])

        # 追蹤數
        followers = int(post['owner']['edge_followed_by']['count'])

        logger.info(f'IG 每日曲線 擷取成功:{postId}')
        print(f'IG 每日曲線 擷取成功:{postId}')

        return {'likes':likes,
                'comments':comments,
                'followers':followers}
                
    def get_post(self, postId:str) -> dict:
        
        # postId = url.split('/p/')[1].split('/')[0]
        url = f'{BASE_URL}/p/{postId}/'
        api_url = f'{BASE_URL}/p/{postId}/{API_PARAMS}'
        html = self.async_get(api_url)

        raw_html = self.async_get(url)
        with open('ig_debug.html', 'w', encoding='utf-8') as f:
            f.write(raw_html)
        
        api_json = json.loads(html)
        with open('ig_err', 'w', encoding='utf-8') as f:
            json.dump(api_json, f)
        html = self.html = self.async_get(url)
        post = self.post_json = api_json['graphql']['shortcode_media']
        hyperlinks_info = []
        
        # 貼文
        post_context = post['edge_media_to_caption']['edges'][0]['node']['text']
        pprint(post_context)
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
        
        # all links+tags
        hyperlinks = htags + tags + url_
        hyperlinks = list(hyperlinks)
        # print(hyperlinks)
        
        if len(tags) > 0:
            self._tag_request(tags, hyperlinks_info)
            # print(hyperlinks_info)
        
        logger.info(f'IG 文案 擷取成功:{postId}')
        print(f'IG 文案 擷取成功:{postId}')

        return {'context':post_context,
                'hyperlinks':hyperlinks,
                'hyperlinks_info':hyperlinks_info}
      
    def get_comments(self, postId):
        # postId = url.split('/p/')[1].split('/')[0]
        url = f'{BASE_URL}/p/{postId}/'
        first_page_url = url + '?__a=1'
        api_url = f'{BASE_URL}/graphql/query/'
        c_count = 0
        output_json = []
        
        # first page
        html = self.async_get(first_page_url)
        first_page_api = json.loads(html)
        first_page_api = sharedData(first_page_api)
        first_page, comment_count= self._comment_handler(first_page_api.comments)
        output_json.extend(first_page)
        c_count += comment_count

        html = self.async_get(url)
        shared_data = sharedData(self._shared_data(html))
        has_next_page = shared_data.has_next_page
        while has_next_page:
            params = {
                'query_hash':PARENT_COMMENT_HASH,
                'variables':f'{{"shortcode":"{postId}","first":50,"after":"{shared_data.end_cursor}"}}'
            }
            
            api_json = json.loads(self.async_get(api_url, params=params))
            shared_data = sharedData(api_json)
            comments, comment_count= self._comment_handler(shared_data.comments)
            has_next_page = shared_data.has_next_page

            output_json.extend(comments)
            c_count += comment_count

        print(f'IG 留言 擷取成功:{postId} 共有{c_count}筆')
        return output_json    
    
    def _comment_handler(self, comment_nodes):
        output_json = []
        c_count = 0
        for comment in comment_nodes:
            comment = commentNode(comment['node'])
            sub_comments = []
            
            if len(comment.sub_comments) > 0:
                for sc in comment.sub_comments:
                    try:
                        sc = commentNode(sc['node'])
                    except KeyError:
                        print(sc)
                    sub_comments.append({
                        'author':sc.author,
                        'thumbnail':sc.thumbnail,
                        'context':sc.context,
                        'likes':sc.likes,
                        'published_time':datetime.fromtimestamp(sc.timestamp),
                    })
                    c_count += 1
                
            output_json.append({
                        'author':comment.author,
                        'thumbnail':comment.thumbnail,
                        'context':comment.context,
                        'likes':comment.likes,
                        'published_time':datetime.fromtimestamp(comment.timestamp),
                        'replies':sub_comments
                    })
            c_count += 1

        return output_json, c_count

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
        '''為解決IG多空格會自動取代成一空格'''
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
            user_id = tag.split('@')[1]
            url = f'{BASE_URL}/{user_id}'
            html = self.async_get(url)
            shared_data = self._shared_data(html)
            full_name = shared_data['entry_data']['ProfilePage'][0]['graphql']['user']['full_name']
            # basic_info = self._basic_info(url, html)
            hyperlinks_info.append({'tag':tag, 'user_name':full_name})
    
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
                else:
                    # referer = BASE_URL
                    headers.update({'Referer':BASE_URL})
                    
                if XSRF:
                    headers.update({'x-csrftoken':XSRF})
                    
                # Start request
                async with aiohttp.ClientSession(trust_env=False, headers=headers) as session:
                    if not self.cs_cookies is None:
                        session.cookie_jar = self.cs_cookies
                    async with session.get(url, proxy=proxy, params=params) as response:
                        raw_html = await response.text()

                        if 'Login • Instagram' in raw_html: 
                            await asyncio.sleep(10)
                            return None
                        elif not response.status == 200:
                            STATUS = response.status
                            await asyncio.sleep(10)
                            return None

                        self.html = raw_html
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
        
        init_data_reg = re.compile(r'window.__additionalDataLoaded\(\'/p/{0}/\',(.*}}}}}}}})'.format(postId))
        init_data = init_data_reg.search(html).group(1)
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
        proxy = random.choice([f'F3JZJYifgvqVCHbd:wifi;@23.109.55.164:{n}'for n in range(9000, 9401)])
        proxies = {'http':f'http://{proxy}', 'https':f'https://{proxy}'}
        
        if async_access:
            proxies = f'http://{proxy}'
        
        return proxies
    
    @staticmethod
    def _update_db(url, sub_count):
        utc_now = datetime.now(tz=pytz.timezone('UTC')).astimezone(pytz.timezone('Asia/Taipei'))
        MONGO.update_many({'ig_url':url}, {'$set':{'subscribers':int(sub_count), 'updated_at':utc_now}})

        
# start = time()
# a = InsPostScraper(proxy=True)
# a.login('peng_2415316', 'wendy0519')
# from pprint import pprint

# pprint(a.get_post('https://www.instagram.com/p/CPI01MXFN3c/'))
# pprint(a.get_comments('https://www.instagram.com/p/CQWAecHJ8ZB/'))

# end = time() - start
# print(f'共花費{end}秒')