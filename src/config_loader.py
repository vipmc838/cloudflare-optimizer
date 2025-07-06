import configparser
import os
from pathlib import Path

class ConfigLoader:
    def __init__(self, config_path="/app/config/config.ini"):
        self.config_path = Path(config_path)
        self.config = configparser.ConfigParser()
        self.load_config()
    
    def load_config(self):
        if not self.config_path.exists():
            self.create_default_config()
        self.config.read(self.config_path, encoding='utf-8')
    
    def create_default_config(self):
        # 路径配置
        self.config['paths'] = {
            'data_dir': '/app/data',
            'log_dir': '/app/log',
            'static_dir': '/app/static',
            'config_dir': '/app/config',
            'log_file': '/app/log/cf.log',
            'ipv4_file': '/app/data/ip.txt',
            'ipv6_file': '/app/data/ipv6.txt',
            'result_file': '/app/data/result.csv',
            # 根据系统自动判断，但在容器中通常是无后缀的
            'binary_file': '/app/data/CloudflareST'
        }

        # CloudflareST 工具参数配置
        self.config['cloudflare'] = {
            # 以下参数留空，以使用 CloudflareST 的默认值
            'n': '200',
            't': '4',
            'dn': '1',
            'dt': '10',
            'tp': '',
            'url': '',
            'httping': 'false',
            'httping_code': '',
            'cfcolo': '',
            'tl': '200',
            'tll': '40',
            'tlr': '',
            'sl': '12',
            'p': '',
            'ip': '',
            'o': self.config.get('paths', 'result_file'),
            'dd': 'true', # 默认不禁用下载测速
            'allip': 'false',
            'debug': 'false',
            'cron': '0 */3 * * *',
            'ipv4': 'true',
            'ipv6': 'false',
            're_install': 'false',
            'proxy': '',
            'api_port': '6788',
            'api_key': '12345678'
        }
        os.makedirs(self.config_path.parent, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            self.config.write(f)
    
    def get(self, section, key, fallback=None):
        return self.config.get(section, key, fallback=fallback)
    
    def getboolean(self, section, key, fallback=False):
        return self.config.getboolean(section, key, fallback=fallback)
    
    def getint(self, section, key, fallback=0):
        return self.config.getint(section, key, fallback=fallback)
    
    def getfloat(self, section, key, fallback=0.0):
        return self.config.getfloat(section, key, fallback=fallback)
    
    def get_args_dict(self):
        """获取优选参数字典"""
        args = {}
        section = 'cloudflare'
        
        # 数值参数
        num_keys = ['n', 't', 'dn', 'dt', 'tp', 'p', 'tl', 'tll', 'sl']
        for key in num_keys:
            value_str = self.get(section, key)
            if value_str: # 只有在值不为空时才处理
                try:
                    args[key] = int(value_str)
                except (ValueError, TypeError):
                    # 如果值无法转换为整数，则忽略
                    pass
        
        # 浮点数参数
        float_keys = ['tlr']
        for key in float_keys:
            value_str = self.get(section, key)
            if value_str: # 只有在值不为空时才处理
                try:
                    args[key] = float(value_str)
                except (ValueError, TypeError):
                    pass
        
        # 字符串参数
        str_keys = ['url', 'httping_code', 'cfcolo', 'ip', 'o']
        for key in str_keys:
            value = self.get(section, key)
            if value:
                args[key] = value
        
        # 布尔参数
        bool_keys = ['httping', 'dd', 'allip', 'debug', 'ipv4', 'ipv6', 're_install']
        for key in bool_keys:
            # 直接调用 getboolean 会在值为空字符串时报错。
            # 我们需要先获取字符串，如果为空则视为 False，否则再进行转换。
            value_str = self.get(section, key)
            if value_str and value_str.lower() in ('true', '1', 'yes', 'on'):
                args[key] = True
            else:
                # 任何其他值（包括空字符串）都将被视为 False
                args[key] = False
        
        # 安全处理API密钥
        if 'api_key' in args:
            args['api_key'] = "******"
        
        return args

config = ConfigLoader()
