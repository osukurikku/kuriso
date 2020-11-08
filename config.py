import io
import json


class Config:
    """Singleton конфигурация"""
    config = {}

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Config, cls).__new__(cls)
        return cls.instance

    @classmethod
    def load_config(cls):
        try:
            config_file = io.open("config.json", "r")
        except FileNotFoundError:
            cls.config = {
                'debug': True,
                'mysql': {
                    'host': '127.0.0.1',
                    'user': 'root',
                    'password': '',
                    'database': 'ripple',
                    'port': 3306
                },
                'redis': {
                    'host': '127.0.0.1',
                    'port': 6379,
                    'password': '',
                    'db': 0
                },
                'host': {
                    'address': '127.0.0.1',
                    'port': 13371,
                    'irc_port': 0 # TODO: IRC
                },
                'geoloc_ip': 'https://country.kurikku.pw/'
            }
            return
        config_raw = config_file.read()
        try:
            cls.config = json.loads(config_raw)
        except json.decoder.JSONDecodeError:
            print("Config file is not correct")
            exit()