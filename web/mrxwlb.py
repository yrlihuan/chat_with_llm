from bs4 import BeautifulSoup
import requests

from . import online_content

# 每日新闻联播
# 网址: https://cn.govopendata.com/xinwenlianbo/20180331/
class MRXWLB(online_content.OnlineContent):
    BASE_URL = 'https://cn.govopendata.com/xinwenlianbo/'

    def __init__(self):
        super().__init__('mrxwlb')

    def url2id(self, url):
        if not url.startswith(MRXWLB.BASE_URL):
            raise RuntimeError(f'Expect url to start with {MRXWLB.BASE_URL}, got {url}')
        
        url_parts = url.split('/')
        if url_parts[-1] == '':
            return url_parts[-2]
        else:
            return url_parts[-1]

    def id2url(self, site_id):
        if len(site_id) != 8 and site_id.isdigit():
            raise RuntimeError('Expect site_id to be of format YYYYMMDD, got %s' % site_id)
        
        return f'{MRXWLB.BASE_URL}{site_id}/'

    def fetch(self, url_or_id):
        url, site_id = self.parse_url_id(url_or_id)
        
        print(url)
        response = requests.get(url)
        raw = response.text

        return url, site_id, {}, raw

    def parse(self, raw):
        soup = BeautifulSoup(raw, 'html.parser')
        base_node = soup.find('main', class_='news-content')
        if not base_node:
            return ''
        
        return base_node.text

online_content.add_online_retriever(MRXWLB())