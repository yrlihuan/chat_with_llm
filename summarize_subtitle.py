# 该脚本从youtube下下载字幕文件，然后通过LLM服务进行摘要生成

import os
import sys
import json
import yaml
import hashlib

import downsub

import argparse

from openai import OpenAI

CUR_DIR = os.path.dirname(os.path.abspath(__file__))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Summarize a youtube video subtitle')

    models = [
        'gemini-1.5-pro',
        'gemini-2.0-flash',
        'gemini-2.0-flash-thinking-exp-01-21',
        'gemini-2.0-pro-exp-02-05',
        'grok-2.0-pro',
        'grok-2.0-latest',
        'grok-beta',
        'deepseek-reasoner-alpha-data-process',
    ]

    parser.add_argument('youtube_link', type=str, help='The youtube video link')
    parser.add_argument('--model', type=str, default='gemini-2.0-pro-exp-02-05', help='The model to use for generating summary')
    parser.add_argument('--prompt', type=str, default='下一个:之后是一个视频的字幕内容，请根据字幕生成中文的内容概括，不限字数，请涵盖视频中的具有洞察力的观点。在总结完之后，再列出视频中最有趣的一些论据。在完成概括之后，最后一行输出一个简短版本的视频标题:', help='The prompt to use for generating summary')

    args = parser.parse_args()

    print("Downloading subtitle file for video: %s" % args.youtube_link)
    metadata = downsub.retrive_metadata(args.youtube_link)
    subs = downsub.retrive_subtitles(metadata)

    if len(subs) == 0:
        print("No subtitles found for the video.")
        sys.exit(1)
    
    print(f'Parsing subtitle using {args.model}.')
    cfg = yaml.load(open(os.path.join(CUR_DIR, 'config.yaml')), yaml.FullLoader)
    
    client = OpenAI(
        api_key=cfg["OPENAI_API_KEY"],
        base_url=cfg['OPENAI_API_BASE'],
    )

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": f'{args.prompt}{subs[0][1]}',
            }
        ],
        model=args.model,
    )

    summary = chat_completion.choices[0].message.content
    print(summary)

    # 保存结果
    youtube_id = args.youtube_link.split('=')[-1]
    youtube_id_md5 = hashlib.md5(youtube_id.encode()).hexdigest()[:8]

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
        filename = f'{youtube_id_md5}_{video_title}_{args.model}.txt'
        with open(os.path.join(CUR_DIR, 'video_summary', filename), 'w') as fout:
            fout.write(summary)

