import datetime as dt


from sqlalchemy import (
    Column, String, TIMESTAMP, Text, Integer, ForeignKey, Boolean, String, ForeignKeyConstraint, SmallInteger, text
)
from sqlalchemy.orm import mapped_column, Mapped

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from db import Base


def utcnow() -> dt.datetime:
    """Support for python==3.10 and below."""
    # pylint: disable=no-member
    try:
        return dt.datetime.now(dt.UTC)
    except ImportError:
        return dt.datetime.utcnow()


class Project(Base):
    """Copied and adapted from OMICSDMv2 sources"""
    id         = Column(Integer, primary_key=True, autoincrement=True)
    short_name = Column(String,  nullable=False,   unique=True)
    long_name  = Column(String,  nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=utcnow)
    description = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    # datasets: Mapped[List["Dataset"]] = relationship(back_populates="project")

    # __permissions__ = (
    #     Permission(datasets, write=True, download=True, propagates_to=['files']),
    # )


class ProjectSchema(BaseModel):
    id: int
    short_name: str
    long_name: str
    created_at: datetime
    description: str
    logo_url: str

    model_config = ConfigDict(from_attributes=True)


class ProjectCreateSchema(BaseModel):
    short_name: str
    long_name: str
    description: str
    logo_url: str

    model_config = ConfigDict(from_attributes=True)



class History(Base):
    """History table."""
    timestamp = Column(TIMESTAMP(timezone=True), default=utcnow,
                       nullable=False, primary_key=True)
    user_username: Mapped[str] = mapped_column(String(100), primary_key=True)

    content = Column(Text, nullable=False)
    endpoint = Column(String(500), nullable=False)
    method = Column(String(10), nullable=False)
