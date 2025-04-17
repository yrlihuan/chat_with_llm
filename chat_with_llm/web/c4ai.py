from typing import Dict, List, Tuple

import asyncio
import collections
import datetime as dt
import hashlib
import json
import random
import time
import urllib

import crawl4ai
from lxml import etree

from chat_with_llm import config
from chat_with_llm import storage
from chat_with_llm.web import online_content
from chat_with_llm.web import utils as web_utils

class DomainState:
    def __init__(self):
        self.last_request_time = 0.0

# crawl4ai (ver 0.5.0.post4)内置的RateLimiter存在一个bug, 当使用arun_many调用时, 多个爬取线程会
# 在同一时间调用wait_if_needed并计算出wait_time, 导致实际上并没有让不同的线程等待.
class CustomRateLimiter:
    def __init__(
        self,
        base_delay: Tuple[float, float] = (1.0, 3.0),
    ):
        self.base_delay = base_delay
        self.domains: Dict[str, DomainState] = collections.defaultdict(DomainState)

    def get_domain(self, url: str) -> str:
        return urllib.parse.urlparse(url).netloc

    async def wait_if_needed(self, url: str) -> None:
        domain = self.get_domain(url)
        state = self.domains[domain]

        wait_time = random.uniform(*self.base_delay) - (time.time() - state.last_request_time)
        while wait_time > 0:
            await asyncio.sleep(wait_time)
            wait_time = random.uniform(*self.base_delay) - (time.time() - state.last_request_time)

        state.last_request_time = time.time()

    # ignore rate limit status code
    def update_delay(self, url: str, status_code: int) -> bool:
        return True

# 利用crawl4ai爬取任意页面
class Crawl4AI(online_content.AsyncOnlineContent):
    NAME = 'crawl4ai'
    DESCRIPTION = '通用爬取器'

    def __init__(self, **params):
        params = {'name': Crawl4AI.NAME, 'description': Crawl4AI.DESCRIPTION, **params}
        super().__init__(**params)

        # cache expire in hours
        self.cache_expire = int(params.get('cache_expire', 24*7))
        self.time_base = dt.datetime.strptime('20250101', '%Y%m%d')

        self.opt_use_proxy = str(params.get('use_proxy', False)).lower() in ['true', '1', 'yes']
        self.opt_mobile_mode = str(params.get('mobile_mode', True)).lower() in ['true', '1', 'yes']
        self.opt_debug = str(params.get('debug', False)).lower() in ['true', '1', 'yes']
        self.opt_login = params.get('login', None)
        self.opt_storage_state_id = params.get('storage_state_id', None)

        self.opt_mean_delay = float(params.get('mean_delay', 1))

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

        if self.opt_login:
            browser_params['headless'] = False
            if not self.opt_storage_state_id:
                site_id = web_utils.url_to_site(self.opt_login)
                print(f'storage_state_id is not specified. Will use login url\'s site id {site_id} as storage_state_id')
                self.opt_storage_state_id = site_id

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
            md = web_utils.strip_boilerplate(md)

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

    async def before_return_html_wait_for_user(self, page, context, html, **kwargs):
        input('Press Enter to continue...')
        return page
    
    async def on_browser_created_handle_login(self, browser, context):
        # use browser.contexts[0] instead of param context
        #context = browser.contexts[0]

        page = await context.new_page()
        await page.goto(self.opt_login)

        input('Press Enter after login finished...')

#        print(context.storage_state())
        if len(browser.contexts) > 0:
            storage_state = await browser.contexts[0].storage_state()
            
            # save storage state
            storage_obj = storage.get_storage('browser_state', None)
            storage_obj.save(self.opt_storage_state_id, json.dumps(storage_state, indent=4, ensure_ascii=False))
        else:
            print('No context found. Do not close browser.')

        await page.close()

    
    async def async_fetch_many(self, urls):
        run_config = crawl4ai.CrawlerRunConfig(
            cache_mode=crawl4ai.CacheMode.BYPASS,
        )

        dispatcher = crawl4ai.async_dispatcher.SemaphoreDispatcher(
            semaphore_count=self.num_workers,
            # NOTE: rate_limiter is not working in multi threadded mode
            rate_limiter=CustomRateLimiter(
                base_delay=[self.opt_mean_delay*0.5, self.opt_mean_delay*1.5],
            ),   
            monitor=crawl4ai.CrawlerMonitor(
                display_mode=crawl4ai.DisplayMode.DETAILED
            )
        )

        rets = []

        if self.opt_login:
            try:
                # NOTE: 当前的实现通过crawl4ai的hook获取browser实例. 不算是最优雅的实现
                login_browser = None
                login_browser = crawl4ai.AsyncWebCrawler(config=self.browser_config)
                login_browser.crawler_strategy.set_hook('on_browser_created', self.on_browser_created_handle_login)

                await login_browser.start()
                
            finally:
                if login_browser:
                    await login_browser.close()

        if self.opt_storage_state_id:
            try:
                # load storage state
                storage_obj = storage.get_storage('browser_state', None)
                storage_state = json.loads(storage_obj.load(self.opt_storage_state_id))
                self.browser_config.storage_state = storage_state
            except Exception as e:
                print(f'Failed to load storage state: {e}')

        async with crawl4ai.AsyncWebCrawler(config=self.browser_config) as crawler:
            if self.opt_debug:
                crawler.crawler_strategy.set_hook('before_return_html', self.before_return_html_wait_for_user)
                # 先运行一次, 确保打开浏览器
                results = []
                _ = await crawler.arun(
                    url='https://www.baidu.com/',
                    config=run_config,
                )

                # 如果debug模式, 每次只获取一个结果
                for url in urls:
                    print(f'Fetching {url}...')
                    result = await crawler.arun(
                        url=url,
                        config=run_config
                    )
                    results.append(result)

            else:
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
                    raw = result.html

                    rets.append((final_url, {}, raw))
                else:
                    print(f'Failed to fetch {result.url}, status_code: {result.status_code}')
                    rets.append(None)
            
        return rets
    
online_content.add_online_retriever(Crawl4AI.NAME, Crawl4AI)