from datetime import datetime
from typing import List, Dict
import logging
from infobot.LinkTable import LinkTable
from object.Base import Base


class Profile(Base):
    def __init__(self, raw, ts, profile_table):
        self.logger: logging.Logger = logging.getLogger('krya.infomanager')
        self.last_update: datetime = None
        self.raw = None
        self.profile_id: int = None
        self.link_table: LinkTable = profile_table
        self.profile_id_key: str = '{}_id'.format(self.link_table.value)
        self.update(raw, ts)

    def update(self, raw, ts):
        self.last_update = ts
        self.raw = raw
        self.profile_id = int(raw[self.profile_id_key])

    def outdated(self, ts: datetime)->bool:
        return self.last_update < ts

    def in_list(self, list: List[Dict], key: str, value: str)->bool:
        for row in list:
            if str(row[key]) == str(value):
                return True

        return False

    def set_history(self, history):
        pass

    async def restore_from_cache(self, redis):
        pass