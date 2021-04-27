import re
import requests
from datetime import datetime
from fake_useragent import UserAgent
import json
import random
from time import sleep
from proxy import get_random_proxy


ap = open('property.txt').read().splitlines()

class Utils:
    def __init__(self):
        time = int(datetime.now().timestamp())
        self.payload = {
                        'username': ap[0],
                        'enc_password': f'#PWD_INSTAGRAM_BROWSER:0:{time}:{ap[1]}',
                        'queryParams': {},
                        'optIntoOneTap': 'false'
                        }
        self.url = 'https://www.instagram.com/accounts/login/'
        self.login_url = 'https://www.instagram.com/accounts/login/ajax/'
        self.ua = UserAgent(verify_ssl=False).random
        self.s = requests.Session()
        # self.proxy_list = get_random_proxy()
        self.c_token = self._get_token()        
    
    def _retry(session, response, url):
        retry_time = 1
        status = 0
        res = ''
        while retry_time <= 3 and status != 200 :
            proxy = random.choice(self.proxy_list)
            print(f'訪問被拒 正在進行第{retry_time}次重試')
            res = session.get(url)#, proxies=proxy
            sleep(random.uniform(1.5, 4)) #降低訪問頻率 以避免被ban
            status = r.status_code
            retry_time += 1
        else:
            if not retry_time <= 10:
                print('成功重新訪問')
                return res
            else: #連線重試失敗
                print('重試次數已達上限 連線已關閉 請重新檢查代理池')
                return ''
                    
    
    def _get_token(self):
        # proxy = random.choice(self.proxy_list)
        r = self.s.get(self.url, headers={'User-Agent':self.ua})#, proxies={'http':proxy}
        sleep(random.uniform(2, 6))
        if r.status_code == 200:
            return r.cookies['csrftoken']
        elif r.status_code == 429 or r.status_code == 503:
            if not _retry(self.s, r, self.url) == '':
                return _retry(self.s, r, self.url).cookies['csrftoken']
            else:
                print('token抓取失敗')
                pass
        
    def login(self):
        c_token = self._get_token()
        r = self.s.post(self.login_url, data=self.payload, headers={'User-Agent':self.ua,"X-Requested-With":"XMLHttpRequest","Referer":"https://www.instagram.com/accounts/login/","x-csrftoken":c_token})
        if r.status_code == 200:
            print('登入成功')
            sleep(random.uniform(2, 6))
            return self.s
        else:
            print('登入失敗 爬蟲終止')
            pass
