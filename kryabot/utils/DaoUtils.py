from object.Base import Base
from object.PostgreDatabase import PostgreDatabase


async def save(db, content):
    async with db.sessionmaker() as session:
        async with session.begin():
            session.add_all(content)
            return await session.commit()


class DaoUtils(Base):
    db = PostgreDatabase().get_instance()

    async def save(self, content=None):
        if not content:
            content = [self]

        return await save(DaoUtils.db, content)

    @staticmethod
    async def execute_all(query):
        async with DaoUtils.db.sessionmaker() as session:
            return (await session.execute(query)).all()

    @staticmethod
    async def execute_first(query):
        async with DaoUtils.db.sessionmaker() as session:
            return (await session.execute(query)).first()
