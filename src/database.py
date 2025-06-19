from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config.config_app import Config


engine = create_async_engine(Config.SQLALCHEMY_DATABASE_URI, echo=True)
async_session = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_session():
    async with async_session() as session:
        yield session