import os
import json
from abc import ABC, abstractmethod

__all__ = ['OnlineContent', 'add_online_retriever', 'get_online_retriever', 'list_online_retrievers']

class OnlineContent(ABC):
    def __init__(self, name, description=None):
        self.name = name
        self.description = description
        self.storage = ContentStorage_File(self.storage_path())

    """
    url_or_id: url or site_id
    force_fetch: force fetch from the website
    force_parse: force parse the raw data
    update_cache: update the saved data
    """
    def retrieve(self, url_or_id, force_fetch=False, force_parse=False, update_cache=True):
        url, site_id = self.parse_url_id(url_or_id)
        key_raw = site_id + '.raw'

        if force_fetch or not self.storage.has(key_raw):
            url, site_id, metadata, raw = self.fetch(url_or_id)
            parsed = self.parse(raw)
            if update_cache:
                self.save(url=url, site_id=site_id, metadata=metadata, raw=raw, parsed=parsed)
            return parsed
        else:
            if force_parse:
                url, site_id, metadata, raw = self.load_raw(url_or_id)
                parsed = self.parse(raw)
                if update_cache:
                    self.save(url=url, site_id=site_id, parsed=parsed)
                return parsed
            else:
                return self.load_parsed(url_or_id)
            
    def list(self, n, **kwargs):
        return []
    
    @abstractmethod
    def url2id(self, url):
        pass

    @abstractmethod
    def id2url(self, site_id):
        pass
        
    @abstractmethod
    def fetch(self, url_or_id):
        # returns url, site_id, metadata, raw
        pass

    @abstractmethod
    def parse(self, raw):
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
    
    def storage_path(self):
        return os.path.join('web_cache', self.name)

    def load_raw(self, url_or_id):
        url, site_id = self.parse_url_id(url_or_id)

        raw = self.storage.load(site_id + '.raw')
        meta = json.loads(self.storage.load(site_id + '.meta'))

        return url, site_id, meta, raw

    def load_parsed(self, url_or_id):
        url, site_id = self.parse_url_id(url_or_id)

        return self.storage.load(site_id + '.parsed')

    def save(self, url=None, site_id=None, metadata=None, raw=None, parsed=None):
        if metadata is not None:
            if url and 'url' not in metadata:
                metadata['url'] = url

            self.storage.save(site_id + '.meta', json.dumps(metadata, indent=4))

        if raw is not None:
            self.storage.save(site_id + '.raw', raw)
        if parsed is not None:
            self.storage.save(site_id + '.parsed', parsed)

    def list_cache(self):
        return self.storage.list()

class ContentStorage_File():
    def __init__(self, storage_path):
        self.storage_path = storage_path
        if not os.path.exists(storage_path):
            os.makedirs(storage_path)

    def load(self, key):
        path = os.path.join(self.storage_path, key)
        if os.path.exists(path):
            return open(path, 'r').read()
        else:
            return None
    
    def save(self, key, value):
        return open(os.path.join(self.storage_path, key), 'w').write(value)
    
    def has(self, key):
        return os.path.exists(os.path.join(self.storage_path, key))
    
    def list(self):
        keys = []
        for f in os.listdir(self.storage_path):
            if f.endswith('.parsed'):
                keys.append(f[:-len('.parsed')])

        return keys
    
all_online_retrievers = {}
def add_online_retriever(retriever):
    assert isinstance(retriever, OnlineContent)
    assert retriever.name not in all_online_retrievers, f'{retriever.name} already exists'

    all_online_retrievers[retriever.name] = retriever

def get_online_retriever(name):
    return all_online_retrievers[name]

def list_online_retrievers():
    return list(all_online_retrievers.keys())