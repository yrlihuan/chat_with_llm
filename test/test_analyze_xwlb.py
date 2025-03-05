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
    parser.add_argument('-p', '--prompt', default='下一行之后是多个日期的新闻联播的内容，请根据新闻联播的内容总结中国政府最为关心的经济政治发展方向。不限字数，可以把次要关注的方向也列举出来。')

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
            contents += f'{key_date}日新闻联播文字版\n'
            contents += parsed + '\n'
        else:
            print(f'Retrieving {key_date} failed')

    print(f'数据准备完毕，开始使用模型{model_id}进行分析...\n')
    message = llm.chat(prompt=prompt, contents=contents, model_id=model_id,
                       use_case='xwlb', save=True)
    print(message)
    