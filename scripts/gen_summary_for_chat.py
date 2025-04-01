# 扫描chat_history下面的文件, 对没有summary文件的内容生成摘要

import argparse
import os.path

from chat_with_llm import storage
from chat_with_llm import llm

if __name__ == '__main__':
    prompts = {
        'v1': '对下面的内容生成一个十六个字之内的标题',
        'v2': '对下面的内容生成一个十六个字之内的概况, 主要是用于快速识别文章中讨论的话题, 可以只是重点内容的名词. 输出只包括概括, 不需要其他内容',
        'v3': '对下面的内容生成一个十六个字之内的概况. 如果是一个话题, 正常概况内容. 如果内容包含多个话题, 用一个重点名词来概括前三个话题. 输出只包括概括, 不需要其他内容',
    }

    parser = argparse.ArgumentParser(description='Generate summary for chat history')
    parser.add_argument('-m', '--model', type=str, default='ds-chat', help='The model to use for generating summary')
    parser.add_argument('-p', '--prompt', type=str, default='v3')
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
