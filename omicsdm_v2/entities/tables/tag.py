from sqlalchemy import Column, String

from biodm.components.table import Base


class Tag(Base):
    name = Column(String, nullable=False, primary_key=True)
