# llm 模块

文件: `chat_with_llm/llm.py`

## 概述

LLM 调用的核心模块, 封装了模型管理、API 调用、结果存储. 通过 OpenAI 兼容 API 支持多种模型后端.

## 模型管理

模块加载时从 `models.yaml` 初始化三个全局映射:
- `g_model_to_display_name`: model_id → 显示名 (所有模型, 含 disabled)
- `g_alias_to_model`: alias → model_id (仅 enabled 模型)
- `g_model_delays`: model_id → delay 秒数 (-1 表示 disabled)

### `list_models() -> list[str]`

返回所有启用的模型 ID 列表.

### `get_model(model_id_or_alias, fail_on_unknown=True) -> str`

将别名或模型 ID 解析为实际模型 ID.

特殊值:
- `'random'`: 从启用模型中随机选择
- 包含 `'*'` 的通配符: 使用 `fnmatch` 匹配后随机选择

异常:
- 未知模型且 `fail_on_unknown=True` 时抛出 `ValueError`
- 模型被禁用时抛出 `ValueError`

### `get_model_short_name(model_id) -> str`

返回模型的显示名. 优先级: display > 第一个 alias > model_id 本身.

### `get_model_save_name(model_id) -> str`

将 model_id 中的 `/` 和 `:` 替换为 `_`, 用于文件名.

### `get_model_from_save_name(save_name) -> str | None`

反向查找: 从 save_name 还原 model_id.

### `get_model_query_delay(model_id_or_alias) -> float`

返回模型的请求间隔 (秒), 用于限速.

## LLM 调用

### `chat(prompt, contents, model_id, **kwargs) -> str`

简化接口, 只返回 response 文本.

### `chat_impl(prompt, contents, model_id, ...) -> (response, reasoning, filename)`

完整实现, 使用 `@langfuse.observe()` 装饰器记录调用.

参数:
- `prompt`: 系统提示
- `contents`: 用户内容
- `model_id`: 模型 ID
- `use_case`: 存储子目录名 (默认 `'default'`)
- `save`: 是否保存结果 (默认 `True`)
- `save_date`: 自定义保存日期 (默认为当前时间)
- `sep`: prompt 和 contents 的分隔符 (默认 `'\n'`)
- `prompt_follow_contents`: prompt 放在 contents 之后 (默认 `False`)
- `retries`: 失败重试次数 (默认 0)
- `throw_ex`: 失败是否抛出异常 (默认 `True`)

实现细节:
- 使用 `langfuse.openai` 包装的 OpenAI 客户端, 自动追踪调用
- 将 prompt 和 contents 拼接为单条 user message 发送
- 支持提取 `reasoning_content` (deepseek 等模型的推理输出)
- 保存时生成两个文件: `.txt` (含 model/prompt/reasoning/response) 和 `.input.txt` (原始输入)
- 文件名冲突时通过 `@N` 后缀去重
- 重试间隔: `min(5 * retry_cnt, 60)` 秒

### `get_storage(use_case) -> StorageBase`

获取指定用途的 chat_history 存储实例, 内部缓存避免重复创建.

## `__main__` 模式

直接运行时执行模型连通性测试: 列出上游可用模型, 逐个发送 "OK" 测试请求.
