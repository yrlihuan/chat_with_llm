import datetime as dt

from bs4 import BeautifulSoup
import requests

from . import online_content

# 每日新闻联播
# 网址: https://cn.govopendata.com/xinwenlianbo/20180331/
class MRXWLB(online_content.OnlineContent):
    BASE_URL = 'https://cn.govopendata.com/xinwenlianbo/'

    def __init__(self):
        super().__init__('mrxwlb', '新闻联播')

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
    
    def list(self, n, **kwargs):
        date_start = kwargs.get('date_start', '20200101')

        t = dt.datetime.today()
        if t.hour < 20:
            t = t - dt.timedelta(days=1)
        date_end = kwargs.get('date_end', t.strftime('%Y%m%d'))

        d0 = dt.datetime.strptime(date_start, '%Y%m%d')
        d1 = dt.datetime.strptime(date_end, '%Y%m%d')

        if (d1 - d0).days > n:
            d0 = d1 - dt.timedelta(days=n-1)

        urls = []
        for d in range((d1 - d0).days + 1):
            site_id = (d0 + dt.timedelta(days=d)).strftime('%Y%m%d')
            urls.append(self.id2url(site_id))

            if n and len(urls) > n:
                break

        return urls

    def fetch(self, url_or_id):
        url, site_id = self.parse_url_id(url_or_id)
        
        print('fetch start')
        response = requests.get(url)
        print('fetch end')
        metadata = {
            'url': url,
        }
        if response.headers['Last-Modified']:
            metadata['last-modified'] = response.headers['Last-Modified']

        raw = response.text

        return url, site_id, metadata, raw

    def parse(self, raw):
        soup = BeautifulSoup(raw, 'html.parser')
        base_node = soup.find('main', class_='news-content')
        if not base_node:
            return ''
        
        return base_node.text

online_content.add_online_retriever(MRXWLB())