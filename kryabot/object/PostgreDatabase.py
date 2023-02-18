from object.Base import Base
from object.BotConfig import BotConfig
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import Session, sessionmaker


class PostgreDatabase(Base):
    instance = None

    def __init__(self):
        config = BotConfig.get_instance().getPostgresqlConfig()
        self.engine = create_async_engine(
            "postgresql+asyncpg://{}:{}@{}:{}/{}".format(config['USERNAME'],
                                                         config['PASSWORD'],
                                                         config['HOST'],
                                                         config['PORT'],
                                                         config['DATABASE']),
            echo=True,
            pool_size=5,
            max_overflow=0)

        self.sessionmaker = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    @staticmethod
    def get_instance():
        if not PostgreDatabase.instance:
            PostgreDatabase.instance = PostgreDatabase()

        return PostgreDatabase.instance
