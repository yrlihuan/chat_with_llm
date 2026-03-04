import os.path
import sqlite3

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
    def load_bytes(self, key):
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

    @abstractmethod
    def delete(self, key):
        pass

    @abstractmethod
    def base_path(self):
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

    def load_bytes(self, key):
        path = os.path.join(self.storage_path, key)
        if os.path.exists(path):
            return open(path, 'rb').read()
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

    def delete(self, key):
        path = os.path.join(self.storage_path, key)
        if os.path.exists(path):
            os.remove(path)

    def base_path(self):
        return self.storage_path

class ContentStorage_Sqlite(StorageBase):
    def __init__(self, storage_base, identifier):
        super().__init__(identifier)

        if not os.path.exists(storage_base):
            os.makedirs(storage_base)

        db_path = os.path.join(storage_base, 'storage.db')
        self.db_path = db_path
        self.table = identifier or '_default'

        conn = self._conn()
        conn.execute(
            f'CREATE TABLE IF NOT EXISTS [{self.table}] '
            f'(key TEXT PRIMARY KEY, value BLOB)'
        )
        conn.commit()
        conn.close()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def load(self, key):
        conn = self._conn()
        row = conn.execute(
            f'SELECT value FROM [{self.table}] WHERE key = ?', (key,)
        ).fetchone()
        conn.close()
        if row is None:
            return None
        data = row[0]
        if isinstance(data, bytes):
            return data.decode('utf-8')
        return data

    def load_bytes(self, key):
        conn = self._conn()
        row = conn.execute(
            f'SELECT value FROM [{self.table}] WHERE key = ?', (key,)
        ).fetchone()
        conn.close()
        if row is None:
            return None
        data = row[0]
        if isinstance(data, str):
            return data.encode('utf-8')
        return data

    def save(self, key, value):
        if isinstance(value, str):
            value = value.encode('utf-8')
        conn = self._conn()
        conn.execute(
            f'INSERT OR REPLACE INTO [{self.table}] (key, value) VALUES (?, ?)',
            (key, value)
        )
        conn.commit()
        conn.close()

    def has(self, key):
        conn = self._conn()
        row = conn.execute(
            f'SELECT 1 FROM [{self.table}] WHERE key = ?', (key,)
        ).fetchone()
        conn.close()
        return row is not None

    def list(self):
        conn = self._conn()
        rows = conn.execute(
            f'SELECT key FROM [{self.table}] ORDER BY key'
        ).fetchall()
        conn.close()
        return [row[0] for row in rows]

    def delete(self, key):
        conn = self._conn()
        conn.execute(
            f'DELETE FROM [{self.table}] WHERE key = ?', (key,)
        )
        conn.commit()
        conn.close()

    def base_path(self):
        return os.path.dirname(self.db_path)

def get_storage(storage_type, identifier, storage_class='file'):
    storage_base = config.get('STORAGE_BASE_DIR')
    assert storage_type in ['chat_history', 'web_cache', 'subtitle_cache', 'video_summary', 'browser_state'], f'Unknown storage type: {storage_type}'

    if storage_class == 'file':
        return ContentStorage_File(os.path.join(storage_base, storage_type), identifier)
    elif storage_class == 'sqlite':
        return ContentStorage_Sqlite(os.path.join(storage_base, storage_type), identifier)
    else:
        raise ValueError(f'Unknown storage class: {storage_class}')
    