from object.Base import Base


class User(Base):
    def __init__(self, name: str, twitch_id: int, display_name=None):
        self.name: str = str(name)
        self.twitch_id: int = twitch_id
        self.display_name: str = str(display_name) if display_name else str(name)
        self.db_info = None

    def set_db_info(self, db_info):
        self.db_info = db_info
