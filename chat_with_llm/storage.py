import os.path

from abc import ABC, abstractmethod

from chat_with_llm import config

class StorageBase(ABC):
    """
    Base class for storage backends.
    params:
        identifier: The identifier for the data. It can be None if all the data is under the same category.
    """
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
        super().__init__(identifier)

        if identifier:
            storage_path = os.path.join(storage_base, identifier)
        else:
            storage_path = storage_base

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
        storage_base = config.get('STORAGE_BASE_DIR')
        assert storage_type in ['chat_history', 'web_cache', 'subtitle_cache', 'video_summary', 'browser_state'], f'Unknown storage type: {storage_type}'
        return ContentStorage_File(os.path.join(storage_base, storage_type), identifier)
    else:
        raise ValueError(f'Unknown storage class: {storage_class}')
    