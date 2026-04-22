from app.db.base import Base
from app.db.session import engine
import app.db.models


async def init_db():
    print("INIT_DB_START")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("INIT_DB_DONE")