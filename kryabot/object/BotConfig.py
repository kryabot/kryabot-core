import json
import os

default_file: str = 'bot.conf'


class BotConfig:
    cached_files = {}

    def __init__(self, file_name=default_file):
        secret_path = os.getenv('SECRET_DIR')
        if secret_path is None:
            secret_path = ''

        with open(secret_path + file_name, 'r') as f:
            self.data = json.load(f)

    @staticmethod
    def get_instance(file_name=default_file):
        existing_config = BotConfig.cached_files.get(file_name, None)
        if not existing_config:
            existing_config = BotConfig(file_name=file_name)
            BotConfig.cached_files[file_name] = existing_config

        return existing_config

    def getConfig(self):
        return self.data

    def getTwitchConfig(self):
        return self.data['TWITCH']

    def getTwitchWebhookConfig(self):
        return self.getTwitchConfig()['WEBHOOK']

    def getVKConfig(self):
        return self.data['VK']

    def getSQLConfig(self):
        return self.data['SQL']

    def getTelegramConfig(self):
        return self.data['TELEGRAM']

    def getRedisConfig(self):
        return self.data['REDIS']

    def getInstanceConfig(self):
        return self.data['INSTANCE']

    def getGuardBotConfig(self):
        return self.data['GUARDBOT']

    def getKbApiConfig(self):
        return self.data['KB_API']

    def getGoogleVisionConfig(self):
        return self.data['GOOGLEVISION']

    def getInfoManagerConfig(self):
        return self.data['INFOMANAGER']
