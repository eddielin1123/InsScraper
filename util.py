import os
import re
import uuid
import json
import datetime
from pathlib import Path

import cld3
import boto3
import emoji
import pytz
import jieba
import requests
import pymongo
import numpy as np 
from wordcloud import WordCloud 
from dotenv import load_dotenv
from botocore.config import Config
from requests_html import HTMLSession
from botocore.exceptions import NoCredentialsError

from . import logger

dir_path = Path(__file__).parent
load_dotenv(Path(__file__).parent.joinpath('.env'))

ACCESS_KEY = 'AKIAQNYWUZX56IQUYDVO'
SECRET_KEY = '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'
BUCKET = 'private.adpost.com.tw'
MONGO = pymongo.MongoClient(os.getenv('MONGOURI'))[os.getenv('MONGO_COLL')]['word_cloud']

def _check_language(text:str, lang:'str'=None) -> bool:
    #* 確認是否出現 中文/英文/lang 以外的語言
    #! 注意：判斷用的模型並非 100% 正確
    
    # 預設可接受語言
    allow_language = ['zh', 'en']
    # not_allow_language = ['th']
    if lang: # 
        allow_language.append(lang)
    
    result = cld3.get_frequent_languages(text, num_langs=3)
    
    if result:
        languages = [l.language for l in result]
    else:
        return True
    
    # 判斷「結果語言」是否與「預期語言」相符
    if not set(languages) & set(allow_language):
        logger.warning(f'Found illegal text: {text}')
        print(languages)
        return False
    
    return True

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

def word_frequency(words:str) -> dict:
    try:
        counting = {}
        for word in words:
            counting[word] = counting.get(word,0) + 1

        rank = sorted(counting.items(), key=lambda item: item[1], reverse=True)
        return dict(rank[:5]), counting
    except Exception:
        logger.exception('word_frequency_exception')
        return None
    
def get_comment_text(comments:list) -> str:
    text = ''
    if not comments:
        logger.error('Comments list is empty')
        return None
    
    for comment in comments:
        
        # 跳過無留言資料
        if not comment.get('context'):
            continue
        
        # 跳過空留言
        if not comment['context']:
            continue
        
        comment_text = comment['context'].lower()
        comment_text = emoji.get_emoji_regexp().sub(r'', comment_text)
        check_language = _check_language(text=comment_text)
        if check_language is True:
            text += comment_text
        
        # 不含子留言則繼續迴圈
        if not comment.get('replies'):
            continue
        
        for r in comment['replies']:
            if not r['context']:
                continue
            replies_text = r['context'].lower()
            check_language = _check_language(text=replies_text)
            if check_language is True:
                text += replies_text
    
    # 去除非文字字串
    text = re.sub(r'\W*', "", text)
    with open(os.path.join(dir_path, 'stop_words.txt'), 'r', encoding='utf-8') as f:
        stop_words = f.read().splitlines()
    
    # 結巴斷詞
    jieba.load_userdict(str(dir_path /'dict.txt'))
    words = jieba.cut(text, cut_all=False, HMM=True)
    
    # 去除停用字
    word_list = []
    for word in words:
        if word not in stop_words:
            word_list.append(word)
    print(word_list)
    return word_list

def word_cloud(text, file_name):
    try:
        if not text:
            raise Exception('input text is empty')
            
        x, y = np.ogrid[:300, :300] #快速產生一對陣列 產生一個以(150,150)為圓心,半徑為130的圓形mask 
        mask = (x - 150) ** 2 + (y - 150) ** 2 > 130 ** 2 #此時mask是bool型 
        mask = 255 * mask.astype(int) #變數型別轉換為int型 
        
        wc = WordCloud(
            font_path=os.path.join(dir_path, 'pingfun.ttf'),
            background_color="white", #背景顏色為“白色” 
            repeat=True, #單詞可以重複 
            mask=mask #指定形狀，就是剛剛生成的圓形 
        ) 
        
        if type(text) is str:
            wc.generate(text) #從文字生成wordcloud 
        if type(text) is dict:
            wc.generate_from_frequencies(frequencies=text)
            
        path = dir_path / 'images' / file_name
        wc.to_file(path)
        return str(path)
    except Exception:
        logger.exception('word_cloud_exception')
        return None

def upload_on_aws(local_file:str, origin_url:str):
    s3 = boto3.client('s3', 
                      aws_access_key_id=ACCESS_KEY,
                      aws_secret_access_key=SECRET_KEY,
                      config=Config(proxies={'http': 'F3JZJYifgvqVCHbd:wifi;;;;@proxy.soax.com:9000'})
                      )
    unique_id = uuid.uuid3(uuid.NAMESPACE_DNS, origin_url)
    
    image_url = f'https://s3.ap-northeast-1.amazonaws.com/private.adpost.com.tw/wordcloud/{str(unique_id)}.png'
    utc_now = datetime.datetime.now(tz=pytz.timezone('UTC')).astimezone(pytz.timezone('Asia/Taipei'))
    MONGO.update_one(
        {
        'id':str(unique_id)
        },
        {
        '$set':{
        'id':str(unique_id),
        'resource':origin_url,
        'wordcloud_url':image_url,
        'update_time':utc_now
        }}, upsert=True)
    
    
    try:
        s3.upload_file(str(local_file), 
                       BUCKET, 
                       f'wordcloud/{str(unique_id)}.png', 
                       ExtraArgs={
                           'ACL': 'public-read',
                           'ContentType':'image/jpeg'
                                  }
                       )
        logger.info("S3 Upload Successful")
        return image_url
    except FileNotFoundError:
        logger.warning("The file was not found")
        return None
    except NoCredentialsError:
        logger.warning("Credentials not available")
        return None

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