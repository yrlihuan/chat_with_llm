import os
import json
from abc import ABC, abstractmethod

from chat_with_llm import storage

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
        self.batch_size = params.get('batch_size', 10)

    def retrieve(self, url_or_id):
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
            try:
                fetch_results = self.fetch(url)
            except Exception as e:
                print(e)
                return None
            
            if fetch_results is None:
                return None
            
            redirect_url, metadata, raw = fetch_results
            parsed = self.parse(redirect_url, raw)

            metadata = metadata or {}
            if 'url' not in metadata:
                metadata['url'] = url

            if url != redirect_url and 'redirect_url' not in metadata:
                metadata['redirect_url'] = redirect_url

            if raw is None:
                raise RuntimeError(f'Failed to fetch {url}')

            if self.update_cache:
                self.save(site_id=site_id, metadata=metadata, raw=raw, parsed=parsed)

            return parsed
        else:
            if self.force_parse or not self.storage.has(key_parsed):
                metadata, raw = self.load_raw(site_id)
                redirect_url = metadata.get('redirect_url', url)
                parsed = self.parse(redirect_url, raw)
                if self.update_cache:
                    self.save(site_id=site_id, parsed=parsed)
                return parsed
            else:
                return self.load_parsed(site_id)
            
    def retrieve_many(self, urls_or_ids):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.batch_size) as executor:
            results = executor.map(self.retrieve, urls_or_ids)

        return results
    
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