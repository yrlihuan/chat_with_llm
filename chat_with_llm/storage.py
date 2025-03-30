import os.path

from abc import ABC, abstractmethod

from chat_with_llm import config

class StorageBase(ABC):
    def __init__(self, identifier):
        self.identifier = identifier

    @abstractmethod
    def load(self, key):
        pass

    @abstractmethod
    def save(self, key, value):
        pass

    @abstractmethod
    def has(self, key):
        pass

    @abstractmethod
    def list(self):
        pass

class ContentStorage_File(StorageBase):
    def __init__(self, storage_base, identifier):
        storage_path = os.path.join(storage_base, identifier)
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
            keys.append(f)

        return keys
    
def get_storage(storage_type, identifier, storage_class='file'):
    if storage_class == 'file':
        if storage_type == 'web_cache':
            storage_base = config.get('WEB_CACHE_DIR')
            return ContentStorage_File(storage_base, identifier)
        elif storage_type == 'chat_history':
            storage_base = config.get('CHAT_HISTORY_DIR')
            return ContentStorage_File(storage_base, identifier)
        else:
            raise ValueError(f'Unknown storage type: {storage_type}')
    else:
        raise ValueError(f'Unknown storage class: {storage_class}')
    