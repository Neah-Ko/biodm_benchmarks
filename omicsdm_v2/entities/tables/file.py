from typing import TYPE_CHECKING, List
import uuid

from sqlalchemy import DateTime, Column, Integer, ForeignKey, Boolean, PrimaryKeyConstraint, String, ForeignKeyConstraint, SmallInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, relationship, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.asyncio import AsyncSession
from biodm import config
from biodm.components.table import Base, S3File, Versioned
from biodm.utils.utils import utcnow
from .asso import asso_dataset_file


if TYPE_CHECKING:
    from .dataset import Dataset


class File(S3File, Versioned, Base):
    """
    Schema and functions for the table files
    - id = autoincremented integer
    - name = filename (TODO we might need to hash it in the future)
    - submitter_name = keycloak id of the one who created the project
    - groups = keycloak groups of the 'submitter_name'
    - submission_date = file submission date in utc
    - version = file version (integer)
    - enabled = boolean for file deletion
    - upload_finished = file upload state True=finished | False=in progress

    - shared_with = keycloak groups which are able to see that file (0 = ALL)

    - extra_cols = JSON containing the following columns:
        - comment = string
    """
    # Orig
    id = Column(Integer, primary_key=True, autoincrement='sqlite' not in str(config.DATABASE_URL))

    # clinical/molecular/licence
    type: Mapped[str] = mapped_column(String(9), nullable=False) # added

    dataset_id      = Column(Integer, nullable=False)
    dataset_version = Column(Integer, nullable=False)

    dataset: Mapped["Dataset"] = relationship(back_populates="files", foreign_keys=[dataset_id, dataset_version])
    # datasets: Mapped[List["Dataset"]] = relationship(back_populates="files", secondary=asso_dataset_file)

    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_id", "dataset_version"],
            ["DATASET.id", "DATASET.version"],
            name="fk_file_dataset",
        ),
        UniqueConstraint(
            "filename",
            "extension",
            "version",
            "dataset_id",
            "dataset_version",
            name="uc_file_in_dataset"
        ),
    )

    submitter_username:  Mapped[str] = mapped_column(ForeignKey("USER.username"), nullable=False) # form: submitter_name
    enabled = Column(Boolean, nullable=False, server_default='1') # TODO
    description = Column(String(200), nullable=True) # form: comment
