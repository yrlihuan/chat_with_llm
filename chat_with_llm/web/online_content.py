import asyncio
import os
import json
from abc import ABC, abstractmethod

from chat_with_llm import storage
from chat_with_llm import config

__all__ = ['OnlineContent', 'add_online_retriever', 'get_online_retriever', 'list_online_retrievers']

class OnlineContent(ABC):
    def __init__(self, name, description, **params):
        self.name = name
        self.description = description
        self.storage = storage.get_storage('web_cache', name)
        self.params = params

        self.force_fetch = params.get('force_fetch', False)
        self.force_parse = params.get('force_parse', False)
        self.update_cache = params.get('update_cache', True)
        self.num_workers = params.get('num_workers', config.get('ONLINE_CONTENT_WORKERS', 2))

    def retrieve(self, url_or_id):
        return self.retrieve_many([url_or_id])[0]
            
    def retrieve_many(self, urls_or_ids):
        to_be_fetched = []
        rets = []
        for ind, url_or_id in enumerate(urls_or_ids):
            url, site_id = self.parse_url_id(url_or_id)
            key_raw = site_id + '.raw'
            key_parsed = site_id + '.parsed'

            if url is None:
                if self.storage.has(key_raw):
                    metadata, raw = self.load_raw(site_id)
                    url = metadata.get('url', None)
                else:
                    raise RuntimeError(f'Cannot decide url from {url_or_id} and no cache found.')

            if self.force_fetch or not self.storage.has(key_raw):
                to_be_fetched.append((ind, url))
                rets.append(None) # placeholder
            else:
                if self.force_parse or not self.storage.has(key_parsed):
                    metadata, raw = self.load_raw(site_id)
                    redirect_url = metadata.get('redirect_url', url)
                    parsed = self.parse(redirect_url, raw)
                    if self.update_cache:
                        self.save(site_id=site_id, parsed=parsed)
                    rets.append(parsed)
                else:
                    rets.append(self.load_parsed(site_id))

        if to_be_fetched:
            fetch_results = self.fetch_many([url for _, url in to_be_fetched])
            for (ind, url), r in zip(to_be_fetched, fetch_results):
                if r is None:
                    rets[ind] = None
                    continue
                
                redirect_url, metadata, raw = r
                parsed = self.safe_parse(redirect_url, raw)

                if not parsed:
                    rets[ind] = None
                    continue

                metadata = metadata or {}
                if 'url' not in metadata:
                    metadata['url'] = url

                if url != redirect_url and 'redirect_url' not in metadata:
                    metadata['redirect_url'] = redirect_url

                if self.update_cache:
                    self.save(site_id=site_id, metadata=metadata, raw=raw, parsed=parsed)

                rets[ind] = parsed
        
        return rets

    def fetch_many(self, urls_or_ids):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            results = executor.map(self.fetch_safe, urls_or_ids)

        return list(results)
    
    def safe_fetch(self, url_or_id):
        try:
            return self.fetch(url_or_id)
        except Exception as e:
            print(e)
            return None
        
    def safe_parse(self, redirect_url, raw):
        try:
            return self.parse(redirect_url, raw)
        except Exception as e:
            print(e)
            return None
    
    @abstractmethod
    def url2id(self, url):
        pass

    @abstractmethod
    def id2url(self, site_id):
        pass
            
    @abstractmethod
    def list(self, n):
        pass
        
    @abstractmethod
    def fetch(self, url):
        # returns redirect_url, metadata, raw
        pass

    @abstractmethod
    def parse(self, url, raw):
        # returns parsed
        pass

    def parse_url_id(self, url_or_id):
        if url_or_id.startswith('http'):
            url = url_or_id
            site_id = self.url2id(url)
        else:
            site_id = url_or_id
            url = self.id2url(site_id)

        return url, site_id

    def load_raw(self, site_id):
        raw = self.storage.load(site_id + '.raw')
        meta = json.loads(self.storage.load(site_id + '.meta'))

        return meta, raw

    def load_parsed(self, site_id):
        return self.storage.load(site_id + '.parsed')

    def save(self, site_id, metadata=None, raw=None, parsed=None):
        if metadata is not None:
            self.storage.save(site_id + '.meta', json.dumps(metadata, indent=4))

        if raw is not None:
            self.storage.save(site_id + '.raw', raw)

        if parsed is not None:
            self.storage.save(site_id + '.parsed', parsed)

class AsyncOnlineContent(OnlineContent):
    def __init__(self, name, description, **params):
        super().__init__(name, description, **params)
        self.loop = params.get('loop', None)

    def fetch_many(self, urls):
        return asyncio.run(self.async_fetch_many(urls))

    # by default, use async io.Semaphore to limit the number of concurrent requests
    # subclass can override this to use other methods
    async def async_fetch_many(self, urls_or_ids):
        asyncio.Semaphore(self.num_workers)
        tasks = [self.async_fetch(url) for url in urls_or_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        ret = []
        for r in results:
            if not isinstance(r, Exception):
                ret.append(r)
            else:
                print(r)
                ret.append(None)

        return ret
    
    def fetch(self, url):
        raise RuntimeError('fetch() is not supported in async mode. Use async_fetch() instead.')
    
    @abstractmethod
    async def async_fetch(self, url):
        pass
    
all_online_retrievers = {}
def add_online_retriever(name, retriever_class):
    assert issubclass(retriever_class, OnlineContent)
    assert name not in all_online_retrievers, f'{name} already exists'

    all_online_retrievers[name] = retriever_class

def get_online_retriever(name, **params):
    if name not in all_online_retrievers:
        raise RuntimeError(f'Unknown online retriever: {name}')
    
    return all_online_retrievers[name](**params)

def list_online_retrievers():
    return list(all_online_retrievers.keys())
