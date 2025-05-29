from typing import TYPE_CHECKING, List

from sqlalchemy import Column, ForeignKeyConstraint, Integer
from sqlalchemy.orm import Mapped, relationship


from biodm.components.table import Base

from .asso import asso_dscoll_file

if TYPE_CHECKING:
    from .file import File
    from .dataset import Dataset


class FileCollection(Base):
    # id              = Column(Integer, primary_key=True,  autoincrement=True)
    # dataset_id      = Column(Integer, nullable=False)
    # dataset_version = Column(Integer, nullable=False)
    dataset_id      = Column(Integer, primary_key=True)
    dataset_version = Column(Integer, primary_key=True)

    files:    Mapped[List["File"]]   = relationship(secondary=asso_dscoll_file, uselist=True, cascade="all,delete")
    # files:    Mapped[List["File"]]   = relationship(back_populates="collection", secondary=asso_dscoll_file, uselist=True, cascade="all,delete")
    dataset: Mapped["Dataset"]       = relationship(back_populates="collection", foreign_keys=[dataset_id, dataset_version], single_parent=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_id", "dataset_version"],
            ["DATASET.id", "DATASET.version"],
            name="fk_file_dataset",
        ),
    )
