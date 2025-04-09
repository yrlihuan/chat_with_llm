import asyncio
import datetime as dt
import hashlib
import json
import urllib
import urllib.parse

import crawl4ai
from bs4 import BeautifulSoup
from lxml import etree

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

        self.opt_use_proxy = str(params.get('use_proxy', False)).lower() in ['true', '1', 'yes']
        self.opt_mobile_mode = str(params.get('mobile_mode', True)).lower() in ['true', '1', 'yes']
        self.opt_debug = str(params.get('debug', False)).lower() in ['true', '1', 'yes']

        params_rate_limit = params.get('rate_limit', '1,5,32')
        self.opt_rate_limit = [float(s) for s in params_rate_limit.split(',')] if isinstance(params_rate_limit, str) else params_rate_limit

        self.opt_parser = params.get('parser', 'markdown')

        # link_extractor is like element_path [| text_sub_path] [| href_sub_path]
        # note | is a valid xpath separator, but we use it as a separator here.
        # please use 'or' where | is needed in xpath
        self.opt_link_extractor = params.get('link_extractor', None)

        # strip boilerplate content. lines contains mainly links are removed.
        # note that this is not for typical homepage, but for content pages
        self.opt_strip_boilerplate = str(params.get('strip_boilerplate', False)).lower() in ['true', '1', 'yes']

        self.generator = crawl4ai.DefaultMarkdownGenerator()
        browser_params = {
            'headless': True,
        }

        if self.opt_use_proxy and config.get('OPTIONAL_PROXY'):
            browser_params['proxy'] = config.get('OPTIONAL_PROXY')
        
        if self.opt_debug:
            browser_params['headless'] = False

        if self.opt_mobile_mode:
            browser_params['viewport_width'] = 375
            browser_params['viewport_height'] = 667
            #browser_params['user_agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1.38'
            
        browser_params['user_agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
        self.browser_config = crawl4ai.BrowserConfig(**browser_params)

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
        if self.opt_parser == 'markdown':
            return self.parse_as_markdown(url, raw)
        elif self.opt_parser == 'link_extractor':
            if self.opt_link_extractor is None:
                raise RuntimeError('Need to specify link_extractor for link_extractor parser')
            
            return self.parse_as_links(url, raw, self.opt_link_extractor)
        else:
            return None
    
    def parse_as_markdown(self, url, raw):
        markdown_result = self.generator.generate_markdown(raw, base_url=url)

        md = markdown_result.raw_markdown
        if self.opt_strip_boilerplate:
            md = self.strip_boilerplate(md)

        return md
    
    def parse_as_links(self, url, raw, link_extractor):

        parts = link_extractor.split('|')
        text_xpath = None
        href_xpath = None
        if len(parts) == 1:
            elem_xpath = parts[0].strip()
        elif len(parts) == 2:
            elem_xpath = parts[0].strip()
            text_xpath = parts[1].strip()
        else:
            elem_xpath = parts[0].strip()
            text_xpath = parts[1].strip()
            href_xpath = parts[2].strip()
 
        text_xpath = '(.//text())[1]'
        href_xpath = '(.//@href)[1]'
        # print(link_extractor, text_xpath, href_xpath)

        links = []
    
        # use lxml to extract links matching xpath link_extractor
        dom = etree.HTML(raw)
        for ele in dom.xpath(elem_xpath):
            texts = ele.xpath(text_xpath)
            hrefs = ele.xpath(href_xpath)

            if not texts or not hrefs or not texts[0].strip() or not hrefs[0].strip():
                continue

            url_path = hrefs[0].strip()
            link_url = urllib.parse.urljoin(url, url_path)

            links.append({'url': link_url, 'text': texts[0].strip()})
        
        return json.dumps(links, indent=4, ensure_ascii=False)

    async def async_fetch(self, url):
        # since async_fetch_many is implemented, async_fetch is not used
        pass

    async def before_return_html(self, page, context, html, **kwargs):
        input('Press Enter to continue...')
        return page
    
    async def async_fetch_many(self, urls):
        run_config = crawl4ai.CrawlerRunConfig(cache_mode=crawl4ai.CacheMode.BYPASS)

        dispatcher = crawl4ai.async_dispatcher.SemaphoreDispatcher(
            max_session_permit=self.num_workers,
            rate_limiter=crawl4ai.RateLimiter(
                base_delay=self.opt_rate_limit[:2],
                max_delay=self.opt_rate_limit[2],
            ),   
            monitor=crawl4ai.CrawlerMonitor(
                max_visible_rows=15,
                display_mode=crawl4ai.DisplayMode.DETAILED
            )
        )

        rets = []

        async with crawl4ai.AsyncWebCrawler(config=self.browser_config) as crawler:
            if not self.opt_debug:
                # Get all results at once
                results = await crawler.arun_many(
                    urls=urls,
                    config=run_config,
                    dispatcher=dispatcher,
                )
            else:
                # 如果debug模式, 每次只获取一个结果
                crawler.crawler_strategy.set_hook('before_return_html', self.before_return_html)

                # 先运行一次, 确保打开浏览器
                results = []
                _ = await crawler.arun(
                    url='https://www.baidu.com/',
                    config=run_config,
                )

                for url in urls:
                    print(f'Fetching {url}...')
                    result = await crawler.arun(
                        url=url,
                        config=run_config
                    )
                    results.append(result)

            # Process all results after completion
            for result in results:
                if result.status_code == 200:
                    final_url = result.url
                    raw = result.html

                    rets.append((final_url, {}, raw))
                else:
                    print(f'Failed to fetch {result.url}, status_code: {result.status_code}')
                    rets.append(None)
            
        return rets
    
    def extract_links_from_markdown(self, s):
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
            links = self.extract_links_from_markdown(l)
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