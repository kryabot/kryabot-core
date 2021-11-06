from infobot.LinkTable import LinkTable
from infobot.Target import Target
from object.Base import Base
from typing import List, Dict
from utils.json_parser import json_to_dict, dict_to_json


class LinkConfig(Base):
    def __init__(self, raw):
        self.fields: Dict = raw
        self.required_fields: List[Dict] = []

    def set_field(self, field_name: str, field_value: bool):
        self.fields[field_name] = field_value

    def get_field_value(self, field_name: str) -> bool:
        try:
            return bool(self.fields[field_name])
        except Exception as ex:
            return False

    def fill_missing(self):
        for field in self.required_fields:
            if field['name'] not in self.fields.keys():
                self.fields[field['name']] = field['default']

    def export(self):
        return dict_to_json(self.fields)


class TwitchLinkConfig(LinkConfig):
    required_fields = [
                {'name': 'show_start', 'default': True},
                {'name': 'show_update', 'default': True},
                {'name': 'show_end', 'default': True},
                {'name': 'pin_start', 'default': False}
            ]

    def __init__(self, raw):
        super().__init__(raw)
        self.required_fields = TwitchLinkConfig.required_fields
        self.fill_missing()


class TargetLink(Base):
    def __init__(self, raw, target):
        self.id: int = int(self.get_attr(raw, 'infobot_link_id'))
        self.target_id: int = int(self.get_attr(raw, 'infobot_id'))
        self.link_table: LinkTable = LinkTable(self.get_attr(raw, 'link_table', 'unknown'))
        self.link_id: int = int(self.get_attr(raw, 'link_id'))
        self.raw = raw
        self.target: Target = target

        if raw['config']:
            parsed = json_to_dict(raw['config'])
            if self.link_table == LinkTable.TWITCH:
                self.config = TwitchLinkConfig(parsed)
            else:
                self.config = LinkConfig(parsed)

    def get_table(self) -> str:
        return self.link_table.value

    def get_display_text(self) -> str:
        # Concept: python default values are common for all platform, but additionally possible extra values based on SQL query.
        # Would be possible to extend InfobotLink, but to simplify it - use ifs

        if self.link_table == LinkTable.TWITCH:
            return 'TWITCH <b>{}</b>'.format(self.raw['dname'])
        # TODO: handle other platforms
        return '{}_{}'.format(self.link_table.value, self.link_id)

    def get_display_button(self) -> str:
        if self.link_table == LinkTable.TWITCH:
            return self.raw['dname']

        return self.get_display_text()
