import fnmatch
import os.path
import random
import time

from openai import OpenAI, OpenAIError

from chat_with_llm import config
from chat_with_llm import storage

CUR_DIR = os.path.dirname(os.path.abspath(__file__))

__all__ = ['list_models', 'get_model', 'get_storage', 'get_model_query_delay', 'chat', 'reason']

#g_model_to_short_name = 
def _load_model_from_config():
    models = config.get_model_configs()

    model_to_short_name = {}
    short_name_to_model = {}
    model_delays = {}

    for data in models:
        model_id = data.get('name')
        alias = data.get('alias')
        delay = data.get('delay')
        disabled = data.get('disabled', False)

        if isinstance(alias, list):
            model_to_short_name[model_id] = alias[0] if len(alias) > 0 else model_id
            
            for a in alias:
                short_name_to_model[a] = model_id
        elif isinstance(alias, str):
            model_to_short_name[model_id] = alias
            short_name_to_model[alias] = model_id
        else:
            model_to_short_name[model_id] = model_id
            short_name_to_model[model_id] = model_id

        # 用delay=-1标识被禁用的模型
        if delay or disabled:
            model_delays[model_id] = -1 if disabled else delay

    return model_to_short_name, short_name_to_model, model_delays

g_model_to_short_name, g_short_name_to_model, g_model_delays = _load_model_from_config()

def list_models():
    models = list(g_model_to_short_name.keys())
    return [m for m in models if get_model_query_delay(m) != -1]

def get_model(model_id_or_alias, fail_on_unknown=True):
    if model_id_or_alias == 'random':
        models = list_models()
        model = random.choice(models)
    elif '*' in model_id_or_alias:
        models = list_models()
        models = fnmatch.filter(models, model_id_or_alias)
        if len(model) == 0:
            raise ValueError(f'No model found for {model_id_or_alias}')
        
        model = random.choice(models)
    else:
        model = g_short_name_to_model.get(model_id_or_alias)

    if fail_on_unknown and model is None:
        raise ValueError(f'Unknown model name {model_id_or_alias}')
    
    return model or model_id_or_alias

def get_model_short_name(model_id):
    return g_model_to_short_name.get(model_id, model_id)

def get_model_from_save_name(save_name):
    for model_id in g_model_to_short_name.keys():
        if get_model_save_name(model_id) == save_name:
            return model_id
        
    return None

def get_model_save_name(model_id):
    return model_id.replace("/", "_").replace(":", "_")

llm_storages = {}
def get_storage(use_case):
    if use_case not in llm_storages:
        llm_storages[use_case] = storage.get_storage('chat_history', use_case)
    
    return llm_storages[use_case]

def get_model_query_delay(model_id_or_alias):
    model = get_model(model_id_or_alias, fail_on_unknown=False)

    return g_model_delays.get(model_id_or_alias, 0)

def chat(prompt, contents, model_id, **kwargs):
    response, reasoning, filename = chat_impl(prompt, contents, model_id, **kwargs)
    return response

def chat_impl(prompt,
              contents,
              model_id,
              use_case='default',
              save=True,
              save_date=None,
              sep='\n',
              prompt_follow_contents=False,
              retries=3,
              throw_ex=True):
    
    delay = get_model_query_delay(model_id)
    if delay == -1:
        raise ValueError(f'Model {model_id} is disabled')
    
    client = OpenAI(
        api_key=config.get("OPENAI_API_KEY"),
        base_url=config.get('OPENAI_API_BASE'),
    )

    request_message = f'{prompt}{sep}{contents}' if not prompt_follow_contents else f'{contents}{sep}{prompt}'
    chat_completion = None
    retry_cnt = 0
    while chat_completion is None:
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": request_message,
                    }
                ],
                model=model_id,
            )
        except OpenAIError as ex:
            if retry_cnt < retries:
                print('openai api failed, retrying...')
                print(ex)
                time.sleep(min(5 * retry_cnt, 60))
                retry_cnt += 1
                continue
            else:
                print('openai api failed, giving up')
                print('input_len: ', len(prompt), len(contents))
                print(prompt)
                print(contents[:min(256, len(contents))])

                if throw_ex:
                    raise ex
                else:
                    return None, None

    response = chat_completion.choices[0].message.content

    if 'reasoning_content' in chat_completion.choices[0].message:
        reasoning = chat_completion.choices[0].message.reasoning_content
    else:
        reasoning = None

    filename = None
    if save:
        storage_obj = get_storage(use_case)

        model_save_name = get_model_save_name(model_id)
        if save_date is None:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
        else:
            timestamp = time.strftime(f'{save_date}_%H%M%S')
            
        filename = f'{timestamp}_{model_save_name}.txt'
        while storage_obj.has(filename):
            if filename.endswith(f'{model_id}.txt'):
                filename = filename[:-len('.txt')] + '@1.txt'
            else:
                filename_parts = filename.split('_')
                filename = '_'.join(filename_parts[:-1]) + f'@{int(filename_parts[-1]) + 1}.txt'

        data = f'model: {model_id}\n'
        data += f'prompt:\n{prompt}\n'
        data += f'reasoning:\n{reasoning}\n' if reasoning else ''
        data += f'response:\n{response}\n'

        storage_obj.save(filename, data)
        storage_obj.save(filename[:-len('.txt')] + '.input.txt', contents)
                                                                  
    return response, reasoning, filename

if __name__ == '__main__':
    # Quick test of models

    client = OpenAI(
        api_key=config.get("OPENAI_API_KEY"),
        base_url=config.get('OPENAI_API_BASE'),
    )

    upstream_models = client.models.list().data
    upstream_models = {m.id: m.owned_by for m in upstream_models}

    for model in list_models():
        short_name = get_model_short_name(model)

        owned_by = upstream_models.get(model)
        if not owned_by:
            print(f'model {model} not found in upstream models')
            continue
        else:
            print(f'{model} ({short_name}), {owned_by}. testing...', end=' ')

            try:
                delay = get_model_query_delay(model)
                t0 = time.time()
                if delay:
                    time.sleep(delay)
                response = chat('Please response with "OK" and nothing else.', '', model, save=False, retries=0)
                t1 = time.time()
                if response.strip() == 'OK':
                    print(f'Done, {t1 - t0:.2f}s')
                else:
                    print(f'Model return response of length {len(response)} ({response[:32]}...), {t1 - t0:.2f}s')
            except OpenAIError as ex:
                print(f'Failed: {ex}')
                