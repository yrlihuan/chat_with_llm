import copy
import os
import yaml

class ConfigNotFoundError(Exception):
    pass

class Config():
    def __init__(self, config_name):
        # load config from config.yaml
        config_candidates = [os.path.expanduser(f'~/.chat_with_llm/{config_name}'),
                             os.path.join(os.path.dirname(__file__), '..', config_name),]
        for config_file in config_candidates:
            if os.path.exists(config_file):
                self.cfg = yaml.load(open(config_file), yaml.FullLoader)
                break
        else:
            raise Exception('No config file found in %s' % config_candidates)

    def __getitem__(self, key):
        if key in self.cfg:
            return self.cfg[key]
        else:
            raise ConfigNotFoundError(f'Config key {key} not found in config.yaml')
    
_the_config = Config('config.yaml')
_the_models_config = Config('models.yaml')

def get(name, default=None):
    try:
        value = os.environ.get(name) or _the_config[name]
    except ConfigNotFoundError:
        if default is None:
            raise
        value = default
    
    if name.endswith('_DIR') and isinstance(value, str) and value.startswith('~'):
        value = os.path.expanduser(value)

    return value

def get_model_configs():
    return copy.deepcopy(_the_models_config.cfg)
