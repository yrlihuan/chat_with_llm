import os.path
import yaml
import time

from openai import OpenAI

CUR_DIR = os.path.dirname(os.path.abspath(__file__))

models = {
    '4o': 'or-openai/chatgpt-4o-latest',
    'o1': 'lobechat-o1-2024-12-17',
    'o1-mini': 'or-openai/o1-mini-2024-09-12',
    'o3-mini': 'lobechat-o3-mini-2025-01-31',
    'gpt4.5': 'or-openai/gpt-4.5-preview-2025-02-27',
    'gpt-4.5': 'or-openai/gpt-4.5-preview-2025-02-27',
    'gemini-1.5-pro': '',
    'gemini-2.0-flash': '',
    'gemini-2.0-flash-thinking': 'gemini-2.0-flash-thinking-exp-01-21',
    'gemini-2.0-pro': 'gemini-2.0-pro-exp-02-05',
    'grok-2.0-pro': '',
    'grok-2.0-latest': '',
    'grok-beta': '',
    'deepseek-reasoner': 'deepseek-reasoner-alpha-data-process',
    'deepseek-chat': 'deepseek-chat-alpha-data-process',
}

def get_model(simple_name):
    model_id = models.get(simple_name, simple_name)
    if model_id == '':
        model_id = simple_name # 重命名为空表示使用原始名称

    return model_id

def chat(prompt, contents, model_id, use_case='default', save=True, sep='\n'):
    cfg = yaml.load(open(os.path.join(CUR_DIR, 'config.yaml')), yaml.FullLoader)
    
    client = OpenAI(
        api_key=cfg["OPENAI_API_KEY"],
        base_url=cfg['OPENAI_API_BASE'],
    )

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": f'{prompt}{sep}{contents}',
            }
        ],
        model=model_id,
    )

    summary = chat_completion.choices[0].message.content

    if 'reasoning_content' in chat_completion.choices[0].message:
        reasoning = chat_completion.choices[0].message.reasoning_content
    else:
        reasoning = None

    if save:
        use_case_dir = os.path.join('chat_history', use_case)
        if not os.path.exists(use_case_dir):
            os.makedirs(use_case_dir)

        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f'{use_case_dir}/{timestamp}_{model_id}.txt'
        while os.path.exists(filename):
            if filename.endswith(f'{model_id}.txt'):
                filename = filename[:-len('.txt')] + '_1.txt'
            else:
                filename_parts = filename.split('_')
                filename = '_'.join(filename_parts[:-1]) + f'_{int(filename_parts[-1]) + 1}.txt'

        data = f'model: {model_id}\n'
        data += f'prompt:\n{prompt}\n'
        data += f'reasoning:\n{reasoning}\n' if reasoning else ''
        data += f'response:\n{contents}\n'

        with open(filename, 'w') as fout:
            fout.write(data)

        with open(filename[:-len('.txt')] + '.input.txt', 'w') as fout:
            fout.write(contents)
                                                                  
    return summary