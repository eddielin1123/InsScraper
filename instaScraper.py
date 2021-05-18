from instascrape import *

sessionid = '47188717345%3AD9mVOFiSd0C7Bk%3A22'
headers = {'user-agent':'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Mobile Safari/537.36 Edg/87.0.664.57',
          'cookie':f'sessionid=47188717345%3A3ns6UxeIFExEjA%3A18'}


url = 'https://www.instagram.com/6tan/'

six_tan = Profile(url)
six_tan_comment = Post('https://www.instagram.com/p/CNsLJs9gzro/')

six_tan.scrape(headers=headers)
six_tan_comment.scrape(headers=headers)
print(six_tan.followers)
print(six_tan_comment.comments)