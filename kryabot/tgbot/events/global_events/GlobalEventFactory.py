from tgbot.events.global_events.EasterEventProcessor import EasterEventProcessor
from tgbot.events.global_events.GlobalEventProcessor import GlobalEventProcessor
from tgbot.events.global_events.HalloweenEventProcessor import HalloweenEventProcessor
from tgbot.events.global_events.WinterEventProcessor import WinterEventProcessor


class GlobalEventFactory:
    factory = {
        "halloween": HalloweenEventProcessor.get_instance(),
        "winter": WinterEventProcessor.get_instance(),
        "easter": EasterEventProcessor.get_instance(),
            }

    @staticmethod
    def get(name)->GlobalEventProcessor:
        return GlobalEventFactory.factory.get(name)

    @staticmethod
    def start(name, client)->None:
        GlobalEventFactory.get(name).create_tasks(client)

    @staticmethod
    def start_all(client)->None:
        for event in GlobalEventFactory.factory.keys():
            GlobalEventFactory.start(event, client)

    @staticmethod
    def is_in_use(tg_chat_id: int) -> bool:
        for event in GlobalEventFactory.factory.keys():
            if GlobalEventFactory.get(event).is_in_use(tg_chat_id):
                return True

        return False