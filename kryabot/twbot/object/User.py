from object.Base import Base


class User(Base):
    def __init__(self, name, twitch_id, display_name=None):
        self.name = name
        self.twitch_id = twitch_id
        self.display_name = display_name if display_name else name
        self.db_info = None

    def set_db_info(self, db_info):
        self.db_info = db_info
