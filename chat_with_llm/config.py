import os
import yaml

class Config():
    def __init__(self):
        # load config from config.yaml
        config_candidates = [os.path.expanduser('~/.chat_with_llm/config.yaml'),
                             os.path.join(os.path.dirname(__file__), '..', 'config.yaml'),
                             'config.yaml',]
        for config_file in config_candidates:
            if os.path.exists(config_file):
                self.cfg = yaml.load(open(config_file), yaml.FullLoader)
                break
        else:
            raise Exception('No config file found in %s' % config_candidates)
        
        # print(self.cfg)

    def __getitem__(self, key):
        return self.cfg[key]
    
_the_config = Config()

def get(name):
    value = os.environ.get(name) or _the_config[name]
    if name.endswith('_DIR') and value.startswith('~'):
        value = os.path.expanduser(value)

    return value
