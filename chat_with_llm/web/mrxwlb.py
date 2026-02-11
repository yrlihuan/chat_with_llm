import datetime as dt

from chat_with_llm.web import online_content
from chat_with_llm.web import linkseek

# 每日新闻联播
# 网址: https://cn.govopendata.com/xinwenlianbo/20180331/
class MRXWLB(online_content.OnlineContent):
    NAME = 'mrxwlb'
    DESCRIPTION = '每日新闻联播'
    BASE_URL = 'https://cn.govopendata.com/xinwenlianbo/'

    def __init__(self, **params):
        params = {'name': MRXWLB.NAME, 'description': MRXWLB.DESCRIPTION, **params}
        super().__init__(**params)

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

    def list(self, n):
        t = dt.datetime.now() - dt.timedelta(hours=20)
        date_end = self.params.get('date_end', t.strftime('%Y%m%d'))

        d1 = dt.datetime.strptime(date_end, '%Y%m%d')
        d0 = d1 - dt.timedelta(days=n-1)

        urls = []
        for d in range((d1 - d0).days + 1):
            site_id = (d0 + dt.timedelta(days=d)).strftime('%Y%m%d')
            urls.append(self.id2url(site_id))

            if n and len(urls) > n:
                break

        return urls

    def fetch(self, url):
        return linkseek.crawl(
            url=url,
            formats=["markdown"],
            use_browser=True,
        )

    def parse(self, url, raw):
        return raw

online_content.add_online_retriever(MRXWLB.NAME, MRXWLB)
