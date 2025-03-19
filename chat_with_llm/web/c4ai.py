import asyncio
import datetime as dt
import hashlib

import crawl4ai

from chat_with_llm import config
from chat_with_llm.web import online_content

# 利用crawl4ai爬取任意页面
class Crawl4AI(online_content.OnlineContent):
    NAME = 'crawl4ai'
    DESCRIPTION = '通用爬取器'

    def __init__(self, **params):
        super().__init__(Crawl4AI.NAME, Crawl4AI.DESCRIPTION, **params)

        if params.get('use_proxy', False):
            self.brower_cfg = crawl4ai.BrowserConfig(
                headless=True,
                proxy=config.get('OPTIONAL_PROXY'),
            )
        else:
            self.brower_cfg = crawl4ai.BrowserConfig(
                headless=True,
            )

        self.generator = crawl4ai.DefaultMarkdownGenerator()

        # cache expire in hours
        self.cache_expire = int(params.get('cache_expire', 24*7))

        self.time_base = dt.datetime.strptime('20250101', '%Y%m%d')

    def url2id(self, url):
        parts = url.replace('https://', '').replace('http://', '').split('/')

        domain = parts[0]
        domain_parts = domain.split('.')
        if domain_parts[0] == 'www':
            domain_parts = domain_parts[1:]
        if domain_parts[-1] == 'com':
            domain_parts = domain_parts[:-1]

        domain_reverse = '_'.join(domain_parts[::-1])
        path = '/'.join(parts[1:])
        path_hash = hashlib.md5(path.encode()).hexdigest()[:8]

        delta = dt.datetime.now() - self.time_base
        hours = int(delta.total_seconds() / 3600) // self.cache_expire * self.cache_expire
        tag_time = self.time_base + dt.timedelta(hours=hours)
        time_tag = tag_time.strftime('%Y%m%d%H')

        return domain_reverse + '_' + path_hash + '_' + time_tag

    def id2url(self, site_id):
        return None
    
    def list(self, n):
        return []

    def fetch(self, url):
        return asyncio.run(self.async_fetch(url))

    def parse(self, url, raw):
        #print(url, len(raw))
        markdown_result = self.generator.generate_markdown(raw, base_url=url)
        return markdown_result.raw_markdown

    async def async_fetch(self, url):
        async with crawl4ai.AsyncWebCrawler(config=self.brower_cfg) as crawler:
            result = await crawler.arun(
                url=url,
            )

        if result.status_code != 200:
            raise RuntimeError(f'Failed to fetch {url}, status_code: {result.status_code}')
        
        final_url = result.url
        raw = result.cleaned_html

        return final_url, {}, raw

online_content.add_online_retriever(Crawl4AI.NAME, Crawl4AI)