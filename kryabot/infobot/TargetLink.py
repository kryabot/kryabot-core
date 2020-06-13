from infobot.LinkTable import LinkTable
from infobot.Target import Target
from object.Base import Base


class TargetLink(Base):
    def __init__(self, raw, target):
        self.id: int = int(self.get_attr(raw, 'infobot_link_id'))
        self.target_id: int = int(self.get_attr(raw, 'infobot_id'))
        self.link_table: LinkTable = LinkTable(self.get_attr(raw, 'link_table', 'unknown'))
        self.link_id: int = int(self.get_attr(raw, 'link_id'))
        self.target: Target = target
