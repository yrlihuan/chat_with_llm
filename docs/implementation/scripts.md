# scripts 脚本集

目录: `scripts/`

## 概述

一系列命令行脚本, 实现 "抓取内容 → LLM 摘要 → 保存结果" 的自动化工作流. 所有脚本共享一套统一的模式: prompt 版本管理、模型可选、结果持久化.

---

## sum_hackernews.py

**功能**: 抓取 HN 首页文章并用 LLM 生成热点摘要.

**流程**:
1. 用 `crawl4ai` 抓取 HN 首页 markdown
2. `extract_articles()` 解析出文章列表 (标题、链接、评论数、HN ID)
3. 过滤评论数 < `min_comments` 的文章
4. 去重: 检查最近 `dedup_n` 次历史的 `.input.txt`, 排除已处理文章
5. 用 `crawl4ai` 批量抓取文章原文
6. 按评论数降序排列, 拼接内容 (用 `---` 分隔), 交给 LLM 总结

**关键参数**: `-m` 模型, `-p` prompt 版本 (v1~v5), `-c` 最小评论数 (默认30), `-d` 去重回溯次数

**extract_articles()**: 通过正则和 `|` 分隔符解析 HN 首页 markdown 中的文章序号、标题、链接、HN ID、评论数.

---

## sum_hn_comments.py

**功能**: 抓取 HN 热门帖子的文章原文 + 评论, 用 LLM 总结各方观点.

**流程**:
1. 通过 `hn_comments` retriever 获取热门帖子 URL 列表
2. 批量抓取评论
3. 从评论中提取文章 URL, 用 `crawl4ai` 抓取原文
4. 拼接: 文章链接 + 评论链接 + 文章原文 + `===` 分隔 + 评论
5. 逐篇调用 LLM 总结

**特性**:
- `--skip_processed`: 检查最近 24h 的历史, 跳过已处理 URL
- 失败时自动用 `model_alt` 备用模型重试一次
- 评论按评论数少到多的顺序处理, 最新结果显示在前

---

## sum_reuters.py

**功能**: 抓取 Reuters Business 新闻并生成摘要.

**流程**:
1. `crawl4ai` (link_extractor 模式) 从首页提取文章链接
2. 过滤标题长度 < 25 的短链接
3. 批量抓取文章内容
4. `remove_duplicated_lines()` 去除跨文章的重复行 (样板内容)
5. LLM 生成中文摘要

---

## sum_yahoo_finance.py

**功能**: 抓取 Yahoo Finance 新闻并生成摘要. 流程与 sum_reuters.py 基本一致.

**差异**: XPath 使用 `//*[self::div and contains(@class, "content")]` 提取链接.

---

## sum_xwlb.py

**功能**: 获取新闻联播内容并用 LLM 总结 (排除政治内容).

**流程**:
1. 用 `mrxwlb` retriever 获取指定日期范围的新闻联播 URL
2. 逐日抓取内容, 调用 LLM 总结
3. 支持 `save_date` 将保存日期设为新闻日期 (而非当前日期)

**关键参数**: `-d` 结束日期, `-n` 天数, `-s` 间隔 (每 n 天取一天)

---

## sum_youtube.py

**功能**: 下载 YouTube 视频字幕, 用 LLM 生成内容摘要.

**流程**:
1. 通过 `downsub` API 下载字幕 (支持中/英/日/韩/法, 含自动生成字幕)
2. 字幕缓存到 `subtitle_cache` (key 为视频 ID 的 MD5 前 8 位)
3. 按优先级选择字幕语言: 中文 > 英文 > 自动生成 > 日/韩/法
4. SRT 格式用 `youtube_subtitle_smart_convert()` 转为分段文本
5. LLM 生成摘要
6. 从摘要最后一行提取视频标题, 保存到 `video_summary`

**youtube_subtitle_smart_convert()**: 用时间间隔判断分段 — 两句话间隔 > 2 秒则换行.

---

## gen_summary_for_chat.py

**功能**: 批量为已有的 LLM 对话记录生成标题和概况.

**流程**: 扫描 chat_history 中没有 `.summary.txt` 的对话文件, 用 LLM 生成 (标题 + 80~120 字概况). 支持主模型失败后用备用模型重试.

---

## extract_markdown_response.py

**功能**: 将 chat_history 中的 markdown 格式响应转换为纯文本.

**转换规则**:
- `[text](url)` → `text`
- `**bold**` / `*italic*` / `` `code` `` → 去除标记
- `# Header` → 去除 `#` 前缀
- `---` → 两个空行
- `- ` 无序列表 → 编号列表

输出文件: `.plain.txt`, 作为 TTS 语音生成的输入.

---

## generate_speech.py

**功能**: 将 `.plain.txt` 文件转换为 MP3 语音.

**实现**:
- 调用 TTS API (`POST {api_url}/tts`)
- 进程锁 (`ProcessLock`) 确保单实例运行
- 自动跳过已有 `.mp3` 的文件
- 支持 dry-run 预览模式

---

## downsub.py

**功能**: YouTube 字幕下载.

### `retrive_metadata(url) -> dict`

调用 DownSub API 获取视频元数据 (含字幕列表).

### `retrive_subtitles(metadata) -> list[(lang, format, content)]`

从元数据中下载支持的字幕文件. 支持 txt 和 srt 格式.

语言映射: `chinese (simplified)` → `chinese`, `english (auto-generated)` → `english_auto` 等.

---

## run_web_retriever.py

**功能**: 通用的 retriever 调试/测试工具.

子命令:
- `help`: 列出所有注册的 retriever
- `list <retriever> -n N`: 列出 retriever 的 URL
- `retrieve <retriever> <url_or_id>`: 抓取并显示单个 URL 内容
- `retrieve_many <retriever> -n N`: 批量抓取
