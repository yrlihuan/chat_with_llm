# 该脚本从youtube下下载字幕文件，然后通过LLM服务进行摘要生成

import os
import sys
import json
import yaml
import hashlib

import downsub

import argparse

from chat_with_llm import llm
from chat_with_llm import config

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Summarize a youtube video subtitle')

    parser.add_argument('youtube_link', type=str, help='The youtube video link')
    parser.add_argument('--model', type=str, default='gemini-2.0-pro-exp-02-05', help='The model to use for generating summary')
    parser.add_argument('--prompt', type=str, default='下一行之后是一个视频的字幕内容，请根据字幕生成中文(Chinese)的内容概括，不限字数，请涵盖视频中的具有洞察力的观点和论据。在完成概括之后，最后一行输出一个简短版本的视频标题。', help='The prompt to use for generating summary')

    args = parser.parse_args()
    model_id = llm.get_model(args.model)

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

    sub_cache_dir = config.get('SUBTITLE_CACHE_DIR')
    if not os.path.exists(sub_cache_dir):
        os.makedirs(sub_cache_dir)

    if youtube_link is None:
        url_cache = os.path.join(sub_cache_dir, f'{youtube_id_md5}.url')
        if os.path.exists(url_cache):
            with open(url_cache, 'r') as fin:
                youtube_link = fin.read().strip()
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
        if os.path.exists(os.path.join(sub_cache_dir, cache_file)):
            with open(os.path.join(sub_cache_dir, cache_file), 'r') as fin:
                subs.append((cache_file.split('.')[1], 'txt', fin.read()))

    if len(subs) == 0:
        print("Downloading subtitle file for video: %s" % args.youtube_link)
        metadata = downsub.retrive_metadata(args.youtube_link)
        subs = downsub.retrive_subtitles(metadata)
        if len(subs) == 0:
            print('Failed to retrieve subtitles for the video.')
            sys.exit(1)

        for lang, fmt, content in subs:
            with open(os.path.join(sub_cache_dir, f'{youtube_id_md5}.{lang}.{fmt}'), 'w') as fout:
                fout.write(content)

        with open(os.path.join(sub_cache_dir, f'{youtube_id_md5}.url'), 'w') as fout:
            fout.write(youtube_link)

        with open(os.path.join(sub_cache_dir, f'{youtube_id_md5}.metadata.json'), 'w') as fout:
            json.dump(metadata['data'], fout, indent=4)

    # 选择字幕文件
    priority = ['chinese', 'english',
                'chinese_auto', 'english_auto',
                'japanese', 'japanese_auto',
                'korean', 'korean_auto',
                'french', 'french_auto']
    for p in priority:
        for sub in subs:
            if sub[0] == p:
                contents = sub[2]
    
    print(f'Parsing subtitle using {model_id}.')
    summary = llm.chat(args.prompt, contents, model_id, use_case='youtube_subtitle', save=True)
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
        save_dir = config.get('VIDEO_SUMMARY_DIR')
        with open(os.path.join(save_dir, filename), 'w') as fout:
            fout.write(f'video: {args.youtube_link}\n')
            fout.write(f'prompty: {args.prompt}\n\n')
            fout.write(summary)

