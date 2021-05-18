from Proxy_List_Scrapper import Scrapper, Proxy, ScrapperException
import random

data = Scrapper(category='ALL', print_err_trace=False).getProxies()

proxy_list = []
for item in data.proxies:
    row = f'{item.ip}:{item.port}'
    proxy_list.append(row)
# print(proxy_list)
proxy = random.sample(proxy_list, 2)
print(proxy)