from enum import Enum
import json

from utils import json_parser


class UpdateAction(Enum):
    UPDATE = "UPDATE"
    REMOVE = "REMOVE"


class UpdateTopic(Enum):
    LINK = "LINK"
    TWITCH = "TWITCH"
    INSTAGRAM = "INSTAGRAM"
    BOOSTY = "BOOSTY"


class UpdaterEncoder(json.JSONEncoder):
    def default(self, o):
        if not isinstance(o, (TwitchUpdate, BoostyUpdate, InstagramUpdate, LinkUpdate, UpdateTopic, UpdateAction)):
            return super(UpdaterEncoder, self).default(o)

        if isinstance(o, Enum):
            return o.value

        return o.__dict__


class InfoBotUpdate(object):
    def __init__(self, action: UpdateAction, topic: UpdateTopic):
        # check of instance is needed due to serialization and deserialization of object
        self.action: UpdateAction = action if isinstance(action, UpdateAction) else UpdateAction(action)
        self.topic: UpdateTopic = topic if isinstance(topic, UpdateTopic) else UpdateTopic(topic)

    # Best would be to have _json methods in utils, but these implementations are fully dependent on object and enums from update functionality
    def to_json(self) -> str:
        return json.dumps(self, cls=UpdaterEncoder)

    @staticmethod
    def from_json(json_message):
        json_dict = json_parser.json_to_dict(json_message)
        object_type = json_dict['topic']

        # Remove topic manually, topic is not part of constructor
        json_dict.pop('topic')

        if object_type == UpdateTopic.TWITCH.value:
            return TwitchUpdate(**json_dict)
        elif object_type == UpdateTopic.BOOSTY.value:
            return BoostyUpdate(**json_dict)
        elif object_type == UpdateTopic.INSTAGRAM.value:
            return InstagramUpdate(**json_dict)
        elif object_type == UpdateTopic.LINK.value:
            return LinkUpdate(**json_dict)

        raise ValueError("Unknown update message: {}".format(json_message))


class TwitchUpdate(InfoBotUpdate):
    def __init__(self, action: UpdateAction, user_id: int):
        super().__init__(action, UpdateTopic.TWITCH)
        self.user_id: int = user_id


class BoostyUpdate(InfoBotUpdate):
    def __init__(self, action: UpdateAction, username: str):
        super().__init__(action, UpdateTopic.BOOSTY)
        self.username: str = username


class InstagramUpdate(InfoBotUpdate):
    def __init__(self, action: UpdateAction, username: str):
        super().__init__(action, UpdateTopic.INSTAGRAM)
        self.username: str = username


class LinkUpdate(InfoBotUpdate):
    def __init__(self, action: UpdateAction, infobot_id: int, link_table: str, link_id: int):
        super().__init__(action, UpdateTopic.LINK)
        self.infobot_id: int = infobot_id
        self.link_table: str = link_table
        self.link_id: int = link_id
