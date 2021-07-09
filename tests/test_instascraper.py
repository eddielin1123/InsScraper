import pytest
import asyncio
from ig_scraper.InsScraper import InsPostScraper
import datetime
import sys
sys.path.insert(0, '../ig_scraper')
sys.path.append('../ig_scraper')

@pytest.mark.post
def test_post():
    postIds = ['CQISu82DL7U', 'COurBrCBWvd']
    for postId in postIds:
        ins = InsPostScraper(proxy=True)
        output = ins.get_post(postId)
        print(output)
        if  postId == 'CQISu82DL7U':
            excepted_context = '今晚8點！\nLouis Vuitton Cruise Show 2022 tonight 8pm. Watch @louisvuitton #LVCRUISE #louisvuitton'
            excepted_links = ['#louisvuitton', '@louisvuitton', '#lvcruise']
            excepted_links_info = [{'tag': '@louisvuitton', 'user_name': 'Louis Vuitton'}]
            assert output['context'] == excepted_context
            assert len(output['hyperlinks']) == 3
            assert output['hyperlinks_info'] == excepted_links_info

        elif postId == 'COurBrCBWvd':
            excepted_context = '## emjoi 測試\n久違的網紅觀察室又要👏🏻來跟大家聊聊媒🤕️體觀察\n這次比🦠較特別是受邀到台南❤️替門薩演講（一個都是高智商的組織）\n這次講題中我嘗試用反面的角度來論證2020年至今台灣的Youtuber所面臨的困境，除了很多人講過的過度飽和與難以捉摸的演算法外，我也聊到了過去佔據領先地位的大網紅們也都開始慢慢用資本築起高牆，慢慢也成為另🧊一種形式的傳統媒體，而過去的傳統🔥媒體也正在進化成新媒體，除了既定市場的競爭，Youtuber們也要面臨到明星藝人的降維打擊，各種困境聽完，如果你覺得都不是問題，那恭喜你，一起來當Youtuber吧！歡迎來當同行！\n\n🌀城市遊俠🌀\n不鏽鋼錶殼材質，精細的鏤空設計，結合精湛製錶工藝，不只前衛時尚還具備了質感，真的是讓人越看越喜歡。穿上襯衫帶上這隻錶就是不敗行頭。\nhttps://reurl.cc/NXoNgn\n\n------------------------\n\n## tag 生效條件\nInstagram & Facebook 通用\n@howoha \n@ 預期不會生效\n\n#### 各平台對於 tag 的呈現方式\n - Youtube 沒有 tag\n - Instagram 的 tag 生效後會轉為帳號，而非 tag 的字樣（暫時不處理這個問題）\n - Facebook 的 tag 生效後，小老鼠會消失\n \n------------------------\n\n## hashtag 測試\n三個平台通用\n#預期會生效\n# 預期不會生效\n\n------------------------\n\n## 超連結在各平台的生效條件\n- Facebook\n\u3000連結生效\n\u3000\u3000文字 https://yahoo.com.tw\n\u3000\u3000文字`https://yahoo.com.tw\n\u3000\u3000文字＞https://yahoo.com.tw\n\u3000連結未生效\n\u3000\u3000文字ahttps://yahoo.com.tw\n\u3000\u3000文字1https://yahoo.com.tw\n\n- Youtube：都會生效\n- Instagram：都不生效\n\n------------------------'
            excepted_links = ['#預期會生效', '@howoha']
            excepted_links_info = [{'tag': '@howoha', 'user_name': '預期會生效'}]
            assert output['context'] == excepted_context
            assert len(output['hyperlinks']) == 2
            assert output['hyperlinks_info'] == excepted_links_info

@pytest.mark.comments
def test_comments():
    postIds = ['COurBrCBWvd', 'CQWAecHJ8ZB']
    for postId in postIds:
        ins = InsPostScraper(proxy=True)
        output = ins.get_comments(postId)
        for comment in output:
            assert isinstance(comment['author'], str)
            assert 'https://' in comment['thumbnail']
            assert isinstance(comment['context'], str)
            assert isinstance(comment['likes'], int)
            assert isinstance(comment['published_time'], datetime.datetime)

            for rcomment in comment['replies']:
                assert isinstance(rcomment['author'], str)
                assert 'https://' in rcomment['thumbnail']
                assert isinstance(rcomment['context'], str)
                assert isinstance(rcomment['likes'], int)
                assert isinstance(rcomment['published_time'], datetime.datetime)

@pytest.mark.followers
def test_followers():
    urls = [
        'https://www.instagram.com/kaohsiungfood',
        # 'https://instagram.com/chelsea_cheek/', # no page
        'https://www.instagram.com/lovebabytwins_sinsin/',
        'https://instagram.com/sanyuan_japan/',
        'https://www.instagram.com/bibinene0212/'
                ]
    for postUrl in urls:
        output = InsPostScraper(proxy=True).get_profile(postUrl)
        assert isinstance(output['subscribers'], int)
        assert not output['subscribers'] == 0

@pytest.mark.post_info
def test_post_info():
    ids = [
        'COurBrCBWvd',
        'CN22WpWASfq'
        ]

    for postId in ids:
        output = InsPostScraper(proxy=True).post_info(postId)
        values = [type(v) is int for v in output.values()]
        assert all(values) is True