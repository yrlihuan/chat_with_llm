import argparse
import os.path
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from chat_with_llm import llm
from chat_with_llm.web import online_content as oc

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze xwlb news using llm.')

    candidate_prompts = {
        'v1': '下一行之后是多日新闻联播的内容, 请根据新闻联播的内容总结中国政府最为关心的经济政治发展方向。不限字数，可以把次要关注的方向也列举出来。',
        'v2': '下一个之后是多日新闻联播的内容, 请总结近期发生的重大事件，包括国际国内政治、经济、社会等方面的事件。不限字数，可以列举多个事件。',
        'v3': '下一行之后是多日新闻联播的内容。将新闻中除了政治领域以外的和以往不同的表述(不要从文章中推断，而是使用已有的知识)总结一下。尽量简短。',
    }

    last_day = time.strftime('%Y%m%d', time.localtime(time.time() - 86400))
    parser.add_argument('-d', '--date', default=last_day, help='The last date to analyze')
    parser.add_argument('-n', '--ndays', type=int, default=3, help='Contain at most news from the last n days')
    parser.add_argument('-m', '--model', type=str, default='gemini-2.0-pro', help='The model to use for generating summary')
    parser.add_argument('-p', '--prompt', default='v2')
    parser.add_argument('--llm_use_case', type=str, default='sum_xwlb', help='The use case for the llm model')
    parser.add_argument('--prompt_follow_contents', type=lambda s: s.lower() == 'true' or s == '1', default=False, help='Whether to follow the contents after the prompt')

    args = parser.parse_args()

    model_id = llm.get_model(args.model)
    retriever = oc.get_online_retriever('mrxwlb', date_end=args.date)
    urls = retriever.list(args.ndays)
    
    if args.prompt in candidate_prompts:
        prompt = candidate_prompts[args.prompt]
    else:
        prompt = args.prompt

    contents = ''
    for url in urls:
        key_date = retriever.url2id(url)
        parsed = retriever.retrieve(url)
        if parsed:
            contents += f'{key_date}日新闻联播文字版\n'
            contents += parsed + '\n'
        else:
            print(f'Retrieving {key_date} failed')

    print(f'数据准备完毕，开始使用模型{model_id}进行分析...\n')
    message = llm.chat(prompt=prompt, contents=contents, model_id=model_id,
                       use_case=args.llm_use_case, save=True)
    print(message)
    