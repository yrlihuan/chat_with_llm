# 该脚本从youtube下下载字幕文件，然后通过LLM服务进行摘要生成

import os
import sys
import json
import yaml
import hashlib

import downsub

import argparse

from chat_with_llm import llm
from chat_with_llm import storage
from chat_with_llm import logutils

import re

def srt_time_to_seconds(time_str):
    """
    将 SRT 时间格式 (00:00:01,333) 转换为秒数 (float)
    """
    hours, minutes, seconds_ms = time_str.split(':')
    seconds, milliseconds = seconds_ms.split(',')
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000.0

# 转换方法由gemini 3.0编写
def youtube_subtitle_smart_convert(subtitle_content, gap_threshold=2.0):
    """
    转换字幕为文本，如果两句话间隔超过 gap_threshold 秒，则换行分段。
    """
    # 1. 清洗头部非字幕内容 (如视频地址)
    subtitle_content = re.sub(r'^视频地址:.*', '', subtitle_content).strip()

    # 2. 使用正则表达式提取每一个字幕块的关键信息
    # 逻辑：匹配 "开始时间 --> 结束时间"，然后捕获随后的文本，直到遇到下一个数字序号或文件结束
    # pattern 解释:
    # (\d{2}:\d{2}:\d{2},\d{3})  --> 捕获组1: 开始时间
    # \s-->\s                    --> 匹配箭头
    # (\d{2}:\d{2}:\d{2},\d{3})  --> 捕获组2: 结束时间
    # \s*\n                      --> 换行
    # ([\s\S]*?)                 --> 捕获组3: 字幕文本 (非贪婪匹配所有字符)
    # (?=\n\d+\s*\n|$)           --> 正向预查: 遇到"换行+数字+换行"(下一个块的开始) 或 字符串结尾 时停止
    pattern = re.compile(r'(\d{2}:\d{2}:\d{2},\d{3})\s-->\s(\d{2}:\d{2}:\d{2},\d{3})\s*\n([\s\S]*?)(?=\n\d+\s*\n|$)', re.MULTILINE)

    matches = pattern.findall(subtitle_content)

    if not matches:
        return "未找到有效的字幕格式"

    final_text = []
    last_end_seconds = 0.0
    is_first_block = True

    for start_str, end_str, text_content in matches:
        # 转换时间
        start_seconds = srt_time_to_seconds(start_str)
        end_seconds = srt_time_to_seconds(end_str)

        # 清洗文本：去除文本块内部的换行符，去除首尾空格
        clean_text = text_content.replace('\n', ' ').strip()

        # 如果文本为空，跳过
        if not clean_text:
            continue

        # 逻辑判断：如何连接上一段文本
        if is_first_block:
            final_text.append(clean_text)
            is_first_block = False
        else:
            # 计算间隔：当前开始时间 - 上一段结束时间
            gap = start_seconds - last_end_seconds

            if gap > gap_threshold:
                # 间隔超过阈值（例如2秒），插入两个换行符（分段）
                final_text.append("\n\n" + clean_text)
            else:
                # 间隔很短，视为同一句话，插入空格连接
                final_text.append(" " + clean_text)

        # 更新"上一段结束时间"
        last_end_seconds = end_seconds

    # 合并结果
    return "".join(final_text)

def process_subtitle(contents):
    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Summarize a youtube video subtitle')


    prompts = {
        'v1': '下一行之后是一个视频的字幕内容，请根据字幕生成中文(Chinese)的内容概括，不限字数，'
              '请涵盖视频中的具有洞察力的观点和论据。在完成概括之后，最后一行输出一个简短版本的视频标题。',
        'v2': '下一行之后是一个视频的字幕内容, 请根据字幕生成中文(Chinese)的内容概括, 不限字数, '
              '请涵盖视频中的具有洞察力的观点和论据. 在开始概况时, 先输出视频的地址([视频地址](url)这种格式), '
              '在完成概括之后, 最后一行输出一个简短版本的视频标题.',
    }

    parser.add_argument('youtube_link', type=str, help='The youtube video link')
    parser.add_argument('-m', '--model', type=str, default='gemini-3.0-flash', help='The model to use for generating summary')
    parser.add_argument('-p', '--prompt', type=str, default='v2', help='The prompt to use for generating summary')
    parser.add_argument('-q', '--quiet', action='store_true', default=False, help='静默模式，只显示错误信息（不显示进度和结果）')

    args = parser.parse_args()

    logger = logutils.SumLogger(quiet=args.quiet)

    model_id = llm.get_model(args.model)

    if args.prompt in prompts:
        prompt = prompts[args.prompt]
    else:
        prompt = args.prompt

    # 判断字符串是否是16进制
    def ishex(s):
        try:
            int(s, 16)
            return True
        except ValueError:
            return False

    youtube_link = args.youtube_link

    # youtube_link可以是cache id
    if len(youtube_link) == 8 and ishex(youtube_link):
        youtube_id_md5 = youtube_link
        youtube_id = None
        youtube_link = None
    else:
        youtube_id = args.youtube_link.split('=')[-1]
        youtube_id_md5 = hashlib.md5(youtube_id.encode()).hexdigest()[:8]

    subtitle_storage = storage.get_storage('subtitle_cache', None)

    if youtube_link is None:
        key = f'{youtube_id_md5}.url'
        if subtitle_storage.has(key):
            youtube_link = subtitle_storage.get(key)
            youtube_id = youtube_link.split('=')[-1]

    cache_candidates = [f'{youtube_id_md5}.chinese.txt',
                        f'{youtube_id_md5}.english.txt',
                        f'{youtube_id_md5}.japanese.txt',
                        f'{youtube_id_md5}.korean.txt',
                        f'{youtube_id_md5}.french.txt',
                        f'{youtube_id_md5}.chinese_auto.txt',
                        f'{youtube_id_md5}.english_auto.txt',
                        f'{youtube_id_md5}.japanese_auto.txt',
                        f'{youtube_id_md5}.korean_auto.txt',
                        f'{youtube_id_md5}.french_auto.txt']

    subs = []
    for cache_file in cache_candidates:
        if subtitle_storage.has(cache_file):
            subs.append((cache_file.split('.')[1], 'txt', subtitle_storage.load(cache_file)))

    if len(subs) == 0:
        logger.info('Downloading subtitle file for video: %s', args.youtube_link)
        metadata = downsub.retrive_metadata(args.youtube_link)
        subs = downsub.retrive_subtitles(metadata)
        if len(subs) == 0:
            logger.error('Failed to retrieve subtitles for the video.')
            sys.exit(1)

        for lang, fmt, content in subs:
            key = f'{youtube_id_md5}.{lang}.{fmt}'
            subtitle_storage.save(key, content)

        subtitle_storage.save(f'{youtube_id_md5}.url', youtube_link)

        metadata_str = json.dumps(metadata, indent=4)
        subtitle_storage.save(f'{youtube_id_md5}.metadata', metadata_str)

    # 选择字幕文件
    priority = ['chinese', 'english',
                'chinese_auto', 'english_auto',
                'japanese', 'japanese_auto',
                'korean', 'korean_auto',
                'french', 'french_auto']
    contents = None
    contents_type = None
    for p in priority:
        for sub in subs:
            if sub[0] == p:
                contents = sub[2]
                contents_type = sub[1]
                break

        if contents:
            break

    assert contents is not None, 'subtitle downloader returns a list of subtitles, but no subtitle is selected'

    if contents_type == 'srt':
        contents_text = youtube_subtitle_smart_convert(contents)
    else:
        contents_text = contents

    logger.info('Parsing subtitle using %s.', model_id)
    contents_url = f'视频地址: {youtube_link}\n'
    message = contents_url + contents_text
    summary = llm.chat(prompt, message, model_id, use_case='sum_youtube', save=True)
    logger.result(summary)

    # 保存结果

    summary_lines = summary.split('\n')
    video_title = None
    for l in summary_lines[-1::-1]:
        if len(l.strip()) > 0:
            video_title = l
            if ('：' in video_title or ':' in video_title) and '标题' in video_title:
                if '：' in video_title:
                    video_title = video_title[video_title.index('：')+1:].strip()
                else:
                    video_title = video_title[video_title.index(':')+1:].strip()

            boilerplate_chars = ['【', '】', '（', '）', '(', ')', '《', '》', '「', '」', '“', '”', '【', '】', '‘', '’', '『', '』', '**', '*']
            for c in boilerplate_chars:
                if c in video_title:
                    video_title = video_title.replace(c, '')

            if ' ' in video_title:
                video_title = video_title.replace(' ', '_')

            break

    if video_title is not None:
        model_save_name = model_id.replace('/', '_')

        filename = f'{youtube_id_md5}_{video_title}_{model_save_name}.txt'
        storage_obj = storage.get_storage('video_summary', None)

        contents = f'video: {args.youtube_link}\n'
        contents += f'prompt: {prompt}\n\n'
        contents += summary
        contents += '\n'

        storage_obj.save(filename, contents)

