import sys
import os.path
import argparse

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import llm
from web import online_content as oc

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze xwlb news using llm.')

    parser.add_argument('-d', '--date', default='20250303', help='The last date to analyze')
    parser.add_argument('-n', '--ndays', type=int, default=50, help='Contain at most news from the last n days')
    parser.add_argument('-m', '--model', type=str, default='gemini-2.0-pro', help='The model to use for generating summary')
    parser.add_argument('-p', '--prompt', default=f'下一行之后是多个日期的新闻联播的内容。然后在{'-'*80}组成的分隔符之后是最后一日的联播内容。请将最后一日的新闻联播内容中，和以往（不限之前的新闻，也包括你的记忆中的历史新闻）不同的表述，尤其是和经济、科技和文化相关的内容，总结一下。尽量简短，只包括最重要的一两点。')
    parser.add_argument('--prompt_follow_contents', type=lambda s: s.lower() == 'true' or s == '1', default=False, help='Whether to follow the contents after the prompt')
    parser.add_argument('--llm_use_case', type=str, default='xwlb_new', help='The use case for the llm model')

    args = parser.parse_args()

    model_id = llm.get_model(args.model)
    retriever = oc.get_online_retriever('mrxwlb')
    urls = retriever.list(args.ndays, date_end=args.date)
    
    prompt = args.prompt
    contents = ''
    for url in urls:
        key_date = retriever.url2id(url)
        parsed = retriever.retrieve(url, force_fetch=False, force_parse=False, update_cache=True)
        if parsed:
            if url == urls[-1]:
                contents += '-' * 80 + '\n'

            contents += f'{key_date}日新闻联播文字版\n'
            contents += parsed + '\n'
        else:
            print(f'Retrieving {key_date} failed')

    print(f'数据准备完毕，开始使用模型{model_id}进行分析...\n')
    message = llm.chat(prompt=prompt, contents=contents, model_id=model_id,
                       use_case=args.llm_use_case, save=True,
                       prompt_follow_contents=args.prompt_follow_contents)
    print(message)
    