import asyncio
import datetime as dt
import hashlib

import crawl4ai

from chat_with_llm import config
from chat_with_llm.web import online_content

# 利用crawl4ai爬取任意页面
class Crawl4AI(online_content.AsyncOnlineContent):
    NAME = 'crawl4ai'
    DESCRIPTION = '通用爬取器'

    def __init__(self, **params):
        super().__init__(Crawl4AI.NAME, Crawl4AI.DESCRIPTION, **params)

        # cache expire in hours
        self.cache_expire = int(params.get('cache_expire', 24*7))
        self.time_base = dt.datetime.strptime('20250101', '%Y%m%d')

        # strip boilerplate content
        self.opt_strip_boilerplate = params.get('strip_boilerplate', False)

        self.opt_use_proxy = params.get('use_proxy', False)

        self.generator = crawl4ai.DefaultMarkdownGenerator()
        if self.opt_use_proxy:
            self.browser_config = crawl4ai.BrowserConfig(
                headless=True,
                proxy=config.get('OPTIONAL_PROXY'),
            )
        else:
            self.browser_config = crawl4ai.BrowserConfig(
                headless=True,
            )

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

    def parse(self, url, raw):
        #print(url, len(raw))
        markdown_result = self.generator.generate_markdown(raw, base_url=url)

        md = markdown_result.raw_markdown
        if self.opt_strip_boilerplate:
            md = self.strip_boilerplate(md)

        return md

    async def async_fetch(self, url):
        # since async_fetch_many is implemented, async_fetch is not used
        pass
    
    async def async_fetch_many(self, urls):
        run_config = crawl4ai.CrawlerRunConfig(cache_mode=crawl4ai.CacheMode.BYPASS)

        dispatcher = crawl4ai.async_dispatcher.SemaphoreDispatcher(
            max_session_permit=self.num_workers,
            rate_limiter=crawl4ai.RateLimiter(
                base_delay=(0.1, 0.2),
                max_delay=10.0
            ),   
            monitor=crawl4ai.CrawlerMonitor()
        )

        rets = []
        async with crawl4ai.AsyncWebCrawler(config=self.browser_config) as crawler:
            # Get all results at once
            results = await crawler.arun_many(
                urls=urls,
                config=run_config,
                dispatcher=dispatcher,
            )

            # Process all results after completion
            for result in results:
                if result.status_code == 200:
                    final_url = result.url
                    raw = result.cleaned_html

                    rets.append((final_url, {}, raw))
                else:
                    print(f'Failed to fetch {result.url}, status_code: {result.status_code}')
                    rets.append(None)
            
        return rets
    
    def extract_links(self, s):
        sb_lvl = 0 # square bracket level
        rb_lvl = 0 # round bracket level
        links = []

        link_start = None
        link_end = None
        link_text = None
        for p, c in enumerate(s):
            if c == '[':
                sb_lvl += 1
                if sb_lvl == 1:
                    link_start = p
            elif c == ']':
                sb_lvl = max(0, sb_lvl - 1)
                if sb_lvl == 0 and link_start is not None:
                    link_text = s[link_start+1:p]
            elif c == '(' and sb_lvl == 0 and rb_lvl == 0 and link_start is not None:
                rb_lvl += 1
            elif c == ')' and sb_lvl == 0 and rb_lvl == 1:
                link_end = p + 1
                links.append((link_start, link_end, link_text))
                link_start = None
                link_end = None
                link_text = None
                rb_lvl = 0

        return links

    def strip_boilerplate(self, contents):
        # 网页中包含大量的链接. 在这里我们尝试去掉这些链接

        outputs = []
        lines = contents.split('\n')
        for l in lines:
            links = self.extract_links(l)
            link_length = sum([e-s for s, e, _ in links])
            if link_length > 0.9 * len(l):
                continue

            l2 = ''
            p = 0
            for s, e, t in links:
                l2 += l[p:s]
                l2 += t
                p = e
                
            l2 += l[p:]

            outputs.append(l2)

        return '\n'.join(outputs)

online_content.add_online_retriever(Crawl4AI.NAME, Crawl4AI)