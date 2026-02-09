from typing import Dict, List, Tuple

import datetime as dt
import hashlib
import json
import urllib

from lxml import etree

from chat_with_llm import config
from chat_with_llm import storage
from chat_with_llm.web import online_content
from chat_with_llm.web import utils as web_utils
from chat_with_llm.web import linkseek

# 利用LinkSeek服务爬取任意页面
class Crawl4AI(online_content.OnlineContent):
    NAME = 'crawl4ai'
    DESCRIPTION = '通用爬取器'

    def __init__(self, **params):
        params = {'name': Crawl4AI.NAME, 'description': Crawl4AI.DESCRIPTION, **params}
        super().__init__(**params)

        # cache expire in hours
        self.cache_expire = int(params.get('cache_expire', 24*7))
        self.time_base = dt.datetime.strptime('20250101', '%Y%m%d')

        self.opt_use_proxy = str(params.get('use_proxy', False)).lower() in ['true', '1', 'yes']
        self.opt_mobile_mode = str(params.get('mobile_mode', False)).lower() in ['true', '1', 'yes']

        self.opt_parser = params.get('parser', 'markdown')

        # link_extractor is like element_path [| text_sub_path] [| href_sub_path]
        # note | is a valid xpath separator, but we use it as a separator here.
        # please use 'or' where | is needed in xpath
        self.opt_link_extractor = params.get('link_extractor', None)

        # strip boilerplate content. lines contains mainly links are removed.
        # note that this is not for typical homepage, but for content pages
        self.opt_strip_boilerplate = str(params.get('strip_boilerplate', False)).lower() in ['true', '1', 'yes']

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
        # raw 已经是 LinkSeek 返回的 markdown, 直接做 strip_boilerplate 即可
        md = raw
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

        links = []

        # use lxml to extract links matching xpath link_extractor
        dom = etree.HTML(raw)
        for ele in dom.xpath(elem_xpath):
            texts = ele.xpath(text_xpath)
            hrefs = ele.xpath(href_xpath)

            if not texts or not hrefs or not texts[0].strip() or not hrefs[0].strip():
                print(f'Warning: skip element for empty text or href. {ele.text}')
                continue

            url_path = hrefs[0].strip()
            link_url = urllib.parse.urljoin(url, url_path)

            links.append({'url': link_url, 'text': texts[0].strip()})

        return json.dumps(links, indent=4, ensure_ascii=False)

    def fetch(self, url):
        if self.opt_parser == 'link_extractor':
            formats = ["html"]
        else:
            formats = ["markdown"]

        proxy = None
        if self.opt_use_proxy:
            proxy = config.get('LINKSEEK_PROXY', '') or None

        return linkseek.crawl(
            url=url,
            formats=formats,
            use_browser=True,
            proxy=proxy,
            mobile=self.opt_mobile_mode,
        )

online_content.add_online_retriever(Crawl4AI.NAME, Crawl4AI)
