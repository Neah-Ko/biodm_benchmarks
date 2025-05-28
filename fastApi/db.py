import datetime as dt
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, declared_attr

from sqlalchemy import DateTime, CHAR, TIMESTAMP, Column, Integer, ForeignKey, Boolean, String, ForeignKeyConstraint, SmallInteger, text
from sqlalchemy.orm import Mapped, relationship, mapped_column


# Replace with your actual credentials
# DATABASE_URL = "asyncpg+postgresql://devel_omicsdm_3tr_rw:pass@172.17.0.4:5432/fastapi"
DATABASE_URL = "postgresql://devel_omicsdm_3tr_rw:pass@172.17.0.5:5432/fastapi"

# engine = create_engine(DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
class Base(DeclarativeBase):
    @declared_attr
    def __tablename__(cls):
        """Generate tablename."""
        return cls.__name__.upper()


class DatabaseManager():
    """Manages DB side query execution."""
    def __init__(self) -> None:
        self._database_url = self.async_database_url(DATABASE_URL)
        try:
            self.engine = create_async_engine(
                str(self._database_url),
                echo=True,
            )
            self.async_session = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        except SQLAlchemyError as _:
            raise

    @staticmethod
    def async_database_url(url) -> str:
        """Adds a matching async driver to a database url."""
        url = str(url)
        match url.split("://"):
            case ["postgresql", _]:
                url = url.replace( # type: ignore [unreachable]
                    "postgresql://", "postgresql+asyncpg://"
                )
            case ["sqlite", _]:
                url = url.replace( # type: ignore [unreachable]
                    "sqlite://", "sqlite+aiosqlite://"
                )
            case _:
                raise Exception()
        return url

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Opens and yields a new AsyncSession."""
        try:
            async with self.async_session() as session:
                yield session
                await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def init_db(self) -> None:
        """Drop all tables and create them."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
