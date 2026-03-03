# storage 模块

文件: `chat_with_llm/storage.py`

## 概述

文件存储抽象层, 提供 key-value 式的持久化存储, 用于保存聊天记录、网页缓存、字幕缓存等.

## 类

### `StorageBase` (ABC)

存储后端的抽象基类.

```python
StorageBase(identifier: str)
```

抽象方法:
- `load(key) -> str | None`: 读取内容
- `save(key, value)`: 保存内容
- `has(key) -> bool`: 检查 key 是否存在
- `list() -> list[str]`: 列出所有 key

### `ContentStorage_File`

文件系统存储实现. 每个 key 对应一个文件.

```python
ContentStorage_File(storage_base: str, identifier: str)
```

存储路径: `{storage_base}/{identifier}/`. 目录不存在时自动创建.

实现细节:
- `load`: 读取文件内容, 文件不存在返回 `None`
- `save`: 写入文件 (覆盖模式)
- `has`: 检查文件是否存在
- `list`: 列出目录下所有文件名

## 模块级接口

### `get_storage(storage_type, identifier, storage_class='file') -> StorageBase`

工厂函数, 创建存储实例.

参数:
- `storage_type`: 存储类型, 必须为以下之一:
  - `chat_history`: LLM 对话记录
  - `web_cache`: 网页缓存
  - `subtitle_cache`: YouTube 字幕缓存
  - `video_summary`: 视频摘要
  - `browser_state`: 浏览器状态
- `identifier`: 子目录名, 用于区分不同用途 (如 `sum_hn`, `sum_xwlb`)
- `storage_class`: 目前仅支持 `'file'`

实际存储路径: `{STORAGE_BASE_DIR}/{storage_type}/{identifier}/`

## 文件命名约定

聊天记录 (`chat_history`) 中的文件遵循以下命名规则:
- `{YYYYMMDD}_{HHMMSS}_{model_save_name}.txt`: LLM 响应 (含 model/prompt/reasoning/response)
- `{YYYYMMDD}_{HHMMSS}_{model_save_name}.input.txt`: 发送给 LLM 的输入内容
- `{YYYYMMDD}_{HHMMSS}_{model_save_name}.summary.txt`: 对话摘要 (由 gen_summary_for_chat 生成)
- `{YYYYMMDD}_{HHMMSS}_{model_save_name}.plain.txt`: 纯文本版响应 (由 extract_markdown_response 生成)
- `{YYYYMMDD}_{HHMMSS}_{model_save_name}.mp3`: 语音版本 (由 generate_speech 生成)
