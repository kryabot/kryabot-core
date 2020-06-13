import json
import os

class BotConfig:

    def __init__(self, file_name='bot.conf'):
        secret_path = os.getenv('SECRET_DIR')
        if secret_path is None:
            secret_path = ''
        #print("Opening secret file from: ${dir}${fname}".format(dir=secret_path, fname=file_name))
        with open(secret_path + file_name, 'r') as f:
            self.data = json.load(f)

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
