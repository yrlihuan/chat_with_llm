# config 模块

文件: `chat_with_llm/config.py`

## 概述

配置管理模块, 从 YAML 文件加载项目配置和模型配置, 并将配置项注入环境变量.

## 类

### `Config`

YAML 配置文件的加载器.

```python
Config(config_name: str)
```

按优先级搜索配置文件:
1. `~/.chat_with_llm/{config_name}`
2. 项目根目录下的 `{config_name}`

找不到任何文件时抛出异常.

通过 `config['KEY']` 访问配置项, key 不存在时抛出 `ConfigNotFoundError`.

## 模块级接口

### `get(name, default=None) -> Any`

获取配置值. 查找顺序:
1. 环境变量 `os.environ[name]`
2. `config.yaml` 中的值

特殊处理: 如果 `name` 以 `_DIR` 结尾且值以 `~` 开头, 自动执行 `expanduser`.

`default=None` 时, key 不存在则抛出 `ConfigNotFoundError`; 否则返回 default.

### `get_model_configs() -> list[dict]`

返回 `models.yaml` 的深拷贝. 每个 dict 包含字段:
- `name`: 模型 ID (如 `gemini-2.5-pro-preview-05-06`)
- `alias`: 字符串或字符串列表, 用于简短引用模型
- `display`: 显示名
- `delay`: 两次请求之间的延迟(秒)
- `disabled`: 是否禁用

### `set_environ()`

将 `config.yaml` 中所有配置项写入 `os.environ`. 模块加载时自动调用.

## 模块初始化

模块导入时自动执行:
1. 加载 `config.yaml` → `_the_config`
2. 加载 `models.yaml` → `_the_models_config`
3. 调用 `set_environ()` 将配置注入环境变量 (Langfuse 等库依赖此行为)

## 配置项 (config.yaml)

| Key | 说明 |
|-----|------|
| `OPENAI_API_KEY` | OpenAI 兼容 API 密钥 |
| `OPENAI_API_BASE` | API 基地址 |
| `DOWNSUB_API_KEY` | DownSub 字幕下载服务密钥 |
| `ONLINE_CONTENT_WORKERS` | 并发抓取线程数 (默认 2) |
| `STORAGE_BASE_DIR` | 文件存储根目录 |
| `LANGFUSE_*` | Langfuse 追踪服务配置 |
| `LINKSEEK_BASE_URL` | LinkSeek 爬虫服务地址 |
| `LINKSEEK_PROXY` | LinkSeek 代理名称 |
