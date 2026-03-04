import os.path
import sqlite3

from abc import ABC, abstractmethod

from chat_with_llm import config

class StorageBase(ABC):
    """
    Base class for storage backends.
    params:
        identifier: The identifier for the data. It can be None if all the data is under the same category.
        readonly: If True, open in read-only mode (save/delete operations will raise exception)
    """
    def __init__(self, identifier, readonly=False):
        self.identifier = identifier
        self.readonly = readonly

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

    def close(self):
        pass

class ContentStorage_File(StorageBase):
    def __init__(self, storage_base, identifier, readonly=False):
        super().__init__(identifier, readonly)

        storage_base = os.path.expanduser(storage_base)
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
        if self.readonly:
            raise RuntimeError('Storage is in readonly mode')
        return open(os.path.join(self.storage_path, key), 'w').write(value)
    
    def has(self, key):
        return os.path.exists(os.path.join(self.storage_path, key))
    
    def list(self):
        keys = []
        for f in os.listdir(self.storage_path):
            if f == 'storage.db' or f.endswith('-journal') or f.endswith('-wal') or f.endswith('-shm'):
                continue
            keys.append(f)

        return keys

    def delete(self, key):
        if self.readonly:
            raise RuntimeError('Storage is in readonly mode')
        path = os.path.join(self.storage_path, key)
        if os.path.exists(path):
            os.remove(path)

    def base_path(self):
        return self.storage_path

class ContentStorage_Sqlite(StorageBase):
    def __init__(self, storage_base, identifier, readonly=False):
        super().__init__(identifier, readonly)

        storage_base = os.path.expanduser(storage_base)
        if identifier:
            storage_path = os.path.join(storage_base, identifier)
        else:
            storage_path = storage_base

        self.storage_path = storage_path
        self.table = identifier or '_default'

        db_path = os.path.join(storage_path, 'storage.db')
        self.db_path = db_path

        if readonly:
            # Only connect if database file exists (read-only mode cannot create new database)
            # Use immutable_uri to prevent any write attempts
            if os.path.exists(db_path):
                self.conn = sqlite3.connect(f'file:{db_path}?mode=ro&immutable=1', uri=True)
            else:
                self.conn = None
        else:
            if not os.path.exists(storage_path):
                os.makedirs(storage_path)
            self.conn = sqlite3.connect(self.db_path)
            self.conn.execute(
                f'CREATE TABLE IF NOT EXISTS [{self.table}] '
                f'(key TEXT PRIMARY KEY, value BLOB)'
            )
            self.conn.commit()

    def load(self, key):
        if self.conn is None:
            return None
        row = self.conn.execute(
            f'SELECT value FROM [{self.table}] WHERE key = ?', (key,)
        ).fetchone()
        if row is None:
            return None
        data = row[0]
        if isinstance(data, bytes):
            return data.decode('utf-8')
        return data

    def load_bytes(self, key):
        if self.conn is None:
            return None
        row = self.conn.execute(
            f'SELECT value FROM [{self.table}] WHERE key = ?', (key,)
        ).fetchone()
        if row is None:
            return None
        data = row[0]
        if isinstance(data, str):
            return data.encode('utf-8')
        return data

    def save(self, key, value):
        if self.readonly:
            raise RuntimeError('Storage is in readonly mode')
        if isinstance(value, str):
            value = value.encode('utf-8')
        self.conn.execute(
            f'INSERT OR REPLACE INTO [{self.table}] (key, value) VALUES (?, ?)',
            (key, value)
        )
        self.conn.commit()

    def has(self, key):
        if self.conn is None:
            return False
        row = self.conn.execute(
            f'SELECT 1 FROM [{self.table}] WHERE key = ?', (key,)
        ).fetchone()
        return row is not None

    def list(self):
        if self.conn is None:
            return []
        rows = self.conn.execute(
            f'SELECT key FROM [{self.table}] ORDER BY key'
        ).fetchall()
        return [row[0] for row in rows]

    def delete(self, key):
        if self.readonly:
            raise RuntimeError('Storage is in readonly mode')
        self.conn.execute(
            f'DELETE FROM [{self.table}] WHERE key = ?', (key,)
        )
        self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def base_path(self):
        return self.storage_path

class ContentStorage_Combined(StorageBase):
    """组合 file 和 sqlite storage. save 写入 sqlite, load 优先 file."""
    def __init__(self, storage_base, identifier, readonly=False):
        super().__init__(identifier, readonly)
        self.file_storage = ContentStorage_File(storage_base, identifier, readonly)
        self.sqlite_storage = ContentStorage_Sqlite(storage_base, identifier, readonly)

    def load(self, key):
        result = self.file_storage.load(key)
        if result is None:
            result = self.sqlite_storage.load(key)
        return result

    def load_bytes(self, key):
        result = self.file_storage.load_bytes(key)
        if result is None:
            result = self.sqlite_storage.load_bytes(key)
        return result

    def save(self, key, value):
        self.sqlite_storage.save(key, value)

    def has(self, key):
        return self.file_storage.has(key) or self.sqlite_storage.has(key)

    def list(self):
        file_keys = set(self.file_storage.list())
        sqlite_keys = set(self.sqlite_storage.list())
        return sorted(file_keys | sqlite_keys)

    def delete(self, key):
        self.file_storage.delete(key)
        self.sqlite_storage.delete(key)

    def base_path(self):
        return self.file_storage.base_path()

    def close(self):
        self.sqlite_storage.close()

def get_storage(storage_type, identifier, storage_class='file', readonly=False):
    storage_base = config.get('STORAGE_BASE_DIR')
    assert storage_type in ['chat_history', 'web_cache', 'subtitle_cache', 'video_summary', 'browser_state'], f'Unknown storage type: {storage_type}'

    if storage_class == 'file':
        return ContentStorage_File(os.path.join(storage_base, storage_type), identifier, readonly)
    elif storage_class == 'sqlite':
        return ContentStorage_Sqlite(os.path.join(storage_base, storage_type), identifier, readonly)
    elif storage_class == 'combined':
        return ContentStorage_Combined(os.path.join(storage_base, storage_type), identifier, readonly)
    else:
        raise ValueError(f'Unknown storage class: {storage_class}')
    
