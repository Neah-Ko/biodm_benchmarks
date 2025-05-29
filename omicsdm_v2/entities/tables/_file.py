from typing import TYPE_CHECKING
import uuid

from sqlalchemy import DateTime, Column, Integer, ForeignKey, Boolean, PrimaryKeyConstraint, String, ForeignKeyConstraint, SmallInteger
from sqlalchemy.orm import Mapped, relationship, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.asyncio import AsyncSession
from biodm.components.table import Base, S3File, Versioned
from biodm.utils.utils import utcnow
# from .asso import asso_dataset_tag

if TYPE_CHECKING:
    from .dataset import Dataset


# class File(S3File, Base):
#     id = Column(Integer, nullable=False, primary_key=True)
#     dataset_id = Column(Integer, nullable=False)
#     dataset_version = Column(SmallInteger, nullable=False)

#     __table_args__ = (
#         ForeignKeyConstraint(
#             ["dataset_id", "dataset_version"],
#             ["DATASET.id", "DATASET.version"],
#             name="fk_file_dataset",
#         ),
#     )


#     # relationships
#     dataset: Mapped["Dataset"] = relationship(back_populates="files", foreign_keys=[dataset_id, dataset_version])

# #     # dataset: Mapped["Dataset"] = relationship(back_populates="files", foreign_keys=[dataset_id, dataset_version])
# #     # dataset: Mapped["Dataset"] = relationship('Dataset', primaryjoin="and_(Dataset.id == File.dataset_id, Dataset.version == File.dataset_version)")
# #     #  foreign_keys=[dataset_id, dataset_version]

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
    id = Column(Integer, primary_key=True, autoincrement=True)

    dataset_id      = Column(Integer, nullable=False)
    dataset_version = Column(Integer, nullable=False)

    __table_args__ = (
        # PrimaryKeyConstraint(
        #     "id",
        #     "version",
        #     name="pk_file"
        # ),
        ForeignKeyConstraint(
            ["dataset_id", "dataset_version"],
            ["DATASET.id", "DATASET.version"],
            name="fk_file_dataset",
        ),
    )

    # name = Column(String(120), nullable=False) # Replaced by S3File
    submitter_username:  Mapped[str] = mapped_column(ForeignKey("USER.username"), nullable=False) # form: submitter_name
    enabled = Column(Boolean, nullable=False, server_default='1') # TODO
    is_clinical = Column(Boolean, nullable=False) # No default.

    # Factored by S3File
    # submission_date = Column(DateTime, nullable=False, default=utcnow) # emitted_at
    # upload_finished = Column(Boolean, nullable=False) # validated
    # shared_with = Column(ARRAY(Integer), nullable=False) # Permission
    # extra_cols = Column(JSONB, nullable=True) # comment
    # Factored by Versioned
    # version = Column(Integer, nullable=False)

    # Replaced
    comment = Column(String(100), nullable=True)

    # Relationships
    # dataset: Mapped["Dataset"] = relationship(back_populates="files", foreign_keys=[dataset_id])

    @hybrid_property
    async def key_salt(self) -> str:
        # Pop session, populated by S3Service just before asking for that attr.
        session: AsyncSession = self.__dict__.pop('session')
        await session.refresh(self, ['dataset'])
        await session.refresh(self.dataset, ['project'])
        return f"{self.dataset.project.name}_{self.dataset.name}"
