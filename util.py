import requests
from requests_html import HTMLSession
import os
import json
from dotenv import load_dotenv

dir_path = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(dir_path, '.env')
load_dotenv(path)

def set_cookies(cookies_dict:dict=None, platform:str='ig'):
    if cookies_dict is None:
        
        try:
            if 'fb' in platform:
                f = open(os.getenv('COOKIES_FB'), 'r')
            if 'ig' in platform:
                f = open(os.getenv('COOKIES_IG'), 'r')

            cookies_dict = json.loads(f.read())
        except Exception as e:
            # print(e)
            raise Exception('Please input cookies via file or list object')

    jar = requests.cookies.RequestsCookieJar()
    for c in cookies_dict:
        try:
            jar.set(c['name'], c['value'], secure=c['secure'], domain=c['domain'], expires=c['expirationDate'])
        except KeyError:
            continue
    return jar


def test_session(cookies_jar):
    jar = set_cookies(cookies_jar)
    # session = requests.Session()
    session = HTMLSession()
    session.headers.update({'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0'})
    session.cookies.update(jar)
    session.proxy = {'http':'http://34.92.248.155', 'https':'https://34.92.248.155'}

    resp = session.get('https://m.facebook.com/normanismee/')
    with open('6tan.html', 'w') as f:
        f.write(resp.text)
    print(session.cookies.get('c_user'))



if __name__ == '__main__':
    with open('/home/eddielin/ad_spiders/ig_scraper/cookies0.txt', 'r') as f:
        cookies = json.loads(f.read())
        test_session(cookies)