import os


class Config:
    """Singleton конфигурация"""
    config = {}

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Config, cls).__new__(cls)
        return cls.instance

    @classmethod
    def load_config(cls):
        cls.config = {
            'debug': os.environ.get('DEBUG', False) in (True, 'True'),
            'mysql': {
                'host': os.environ.get("MYSQL_HOST", "127.0.0.1"),
                'user': os.environ.get("MYSQL_USER", "root"),
                'password': os.environ.get("MYSQL_PASSWORD", ""),
                'database': os.environ.get("MYSQL_DB", "ripple"),
                'port': int(os.environ.get("MYSQL_PORT", '3306'))
            },
            'redis': {
                'host': os.environ.get("REDIS_HOST", "127.0.0.1"),
                'port': int(os.environ.get("REDIS_PORT", '6379')),
                'password': os.environ.get("REDIS_PASSWORD", ""),
                'db': int(os.environ.get("REDIS_DB", '0'))
            },
            'host': {
                'address': os.environ.get("WEB_HOST", '127.0.0.1'),
                'port': int(os.environ.get("WEB_PORT", '13371')),
                'irc_port': int(os.environ.get("IRC_PORT", '0'))  # TODO: IRC
            },
            'geoloc_ip': os.environ.get("GEOLOC_IP", "https://country.kurikku.pw/")
        }
