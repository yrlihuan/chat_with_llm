# 扫描chat_history下面的文件, 对没有summary文件的内容生成摘要

import argparse
import os.path

from chat_with_llm import storage
from chat_with_llm import llm

if __name__ == '__main__':
    prompts = {
        'v1': '对下面的内容生成标题和概况. 标题十六个字之内, 概况在80字到120字. 输出分两行, 第一行标题, 第二行概况. 不需要其他内容',
        'v2': '对下面的内容生成标题和概况. 标题十六个字之内, 概况在80字到120字. 如果内容包含多个话题, 用三到四个名词做标题. 输出分两行, 第一行标题, 第二行概况. 不需要其他内容',
    }

    parser = argparse.ArgumentParser(description='Generate summary for chat history')
    parser.add_argument('-m', '--model', type=str, default='ds-chat', help='The model to use for generating summary')
    parser.add_argument('-p', '--prompt', type=str, default='v2')
    parser.add_argument('-u', '--use_cases', type=lambda s: s.split(','), default=[])

    args = parser.parse_args()

    if args.prompt in prompts:
        prompt = prompts[args.prompt]
    else:
        prompt = args.prompt

    for use_case in args.use_cases:
        storage_obj = storage.get_storage('chat_history', use_case)
        keys = storage_obj.list()
        conversations = set()
        summaries = set()

        for key in keys:
            if key.endswith('.input.txt'):
                continue
            elif key.endswith('.summary.txt'):
                summaries.add(key[:-len('.summary.txt')])
            elif key.endswith('.txt'):
                conversations.add(key[:-len('.txt')])
                
        to_be_summarized = conversations - summaries
        print(f'{use_case}: {len(to_be_summarized)}个聊天记录待摘要')

        model_id = llm.get_model(args.model)
        for key in to_be_summarized:
            print(f'正在处理 {key}...')
            contents = storage_obj.load(key + '.txt')

            answer = llm.chat(
                prompt=prompt,
                contents=contents,
                model_id=model_id,
                use_case='gen_conversation_summary',
                save=False,
                retries=1,
                throw_ex=False
            )

            storage_obj.save(key + '.summary.txt', answer.strip() + '\n')
