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
    parser.add_argument('-m', '--model', type=str, default='gemini-2.0-pro', help='The model to use for generating summary')
    parser.add_argument('-p', '--prompt', type=str, default='v2', help='The prompt to use for generating summary')

    args = parser.parse_args()

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
        print("Downloading subtitle file for video: %s" % args.youtube_link)
        metadata = downsub.retrive_metadata(args.youtube_link)
        subs = downsub.retrive_subtitles(metadata)
        if len(subs) == 0:
            print('Failed to retrieve subtitles for the video.')
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
    for p in priority:
        for sub in subs:
            if sub[0] == p:
                contents = sub[2]
                break

    assert contents is not None, 'subtitle downloader returns a list of subtitles, but no subtitle is selected'
    
    print(f'Parsing subtitle using {model_id}.')
    contents_url = f'视频地址: {youtube_link}\n'
    message = contents_url + contents
    summary = llm.chat(prompt, message, model_id, use_case='sum_youtube', save=True)
    print(summary)

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

