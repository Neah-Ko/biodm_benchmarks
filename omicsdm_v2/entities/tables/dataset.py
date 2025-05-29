from typing import List, Set # Optional, 

from sqlalchemy import TIMESTAMP, Boolean, DateTime, BIGINT, TEXT, Column, ForeignKeyConstraint, Identity, Integer, Sequence, SmallInteger, ForeignKey, String, PrimaryKeyConstraint, Text, UniqueConstraint, null
from sqlalchemy.orm import Mapped, relationship, mapped_column
from sqlalchemy.dialects.postgresql import JSONB


from biodm.components.table import Base, Versioned
# from biodm.tables import Group, User
from biodm.utils.utils import utcnow
from biodm.utils.security import Permission
from biodm import config
from .asso import asso_dataset_tag
# from .asso import asso_dataset_file
# from .asso import asso_dscoll_file
from .file import File
from .tag import Tag
from .project import Project
# from .filecollection import FileCollection


class Dataset(Versioned, Base):
    """
    Schema and functions for the table projects
    - id = autoincremented integer
    - project_id = project id (integer)
    - name = dataset name human readable
    - private = true (=dataset is private) or false (=dataset is public)
    - submitter_name = kcloak id of the one who created the project
    - submission_date = dataset creation date in utc
    - shared_with = kcloak groups which are able to see that project (0 = ALL?)
    - extra_cols = JSON containing the following columns:
        - disease = string
        - treatment = string
        - molecularInfo = string
        - sampleType = string
        - dataType = string
        - valueType = string
        - platform = string
        - genomeAssembly = string
        - annotation = string
        - samplesCount = integer
        - featuresCount = integer
        - featuresId = string
        - healthyControlIncluded = string
        - additional_info = string
        - contact = string
        - tags = string
        - "file": "file" -> Pheno-clinical information CSV/JSON
        - "file2": "file2" -> Licence PDF
    """
    # Management
    id              = Column(Integer,     primary_key=True, autoincrement='sqlite' not in str(config.DATABASE_URL))
    short_name      = Column(String(120), nullable=False) # form: dataset_id
    long_name       = Column(String(120), nullable=True)  # form: name
    description     = Column(TEXT,        nullable=True)  # added
    submission_date = Column(TIMESTAMP(timezone=True),    nullable=False, default=utcnow) # server_default="now()") # default=utcnow)

    # Metadata
    disease                   = Column(String(10),    nullable=False)
    treatment                 = Column(String(50),    nullable=False)
    molecular_info            = Column(String(100),   nullable=False) # form: molecularInfo
    sample_type               = Column(String(50),    nullable=False) # form: sampleType
    data_type                 = Column(String(50),    nullable=False) # form: dataType
    value_type                = Column(String(50),    nullable=False) # form: valueType
    platform                  = Column(String(50),    nullable=False)
    genome_assembly           = Column(String(50),    nullable=False) # form: genomeAssembly
    annotation                = Column(String(50),    nullable=False)
    samples_count             = Column(Integer,       nullable=False) # form: samplesCount
    features_count            = Column(Integer,       nullable=False) # form: featuresCount
    features_id               = Column(String,        nullable=False) # form: featuresID
    healthy_controls_included = Column(Boolean,       nullable=False) # form: healthyControlIncluded
    additional_info           = Column(String,        nullable=True) # form: additionalInfo

    # Foreign keys
    project_id:         Mapped[int] = mapped_column(ForeignKey("PROJECT.id"),    nullable=False)
    submitter_username: Mapped[str] = mapped_column(ForeignKey("USER.username"), nullable=False)
    # contact_username:   Mapped[str] = mapped_column(ForeignKey("USER.username"), nullable=False)s
    contact_email:   Mapped[str] = mapped_column(String, nullable=False) # TODO # form: contact

    # relationships
    project:  Mapped["Project"]      = relationship(back_populates="datasets")
    tags:     Mapped[List["Tag"]]     = relationship(
        secondary=asso_dataset_tag,
        uselist=True,
        cascade="save-update, merge, expunge, refresh-expire",
    )
    files:    Mapped[List["File"]]   = relationship(back_populates="dataset", cascade="all,delete")
    # files:    Mapped[List["File"]]   = relationship(back_populates="datasets", secondary=asso_dataset_file, uselist=True, cascade="all,delete")
    # collection: Mapped["FileCollection"] = relationship(back_populates="dataset")

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "short_name",
            "version",
            name="uc_dataset_short_name_version"
        ),
    )

    # "sharing" -> permission self
    # "dataset owners" -> permission files
    #                  -> also get shared, explicitely 
    # "dataset owners" are a subset (or subgroups) of the project owners

    # Below: refactored with BioDM permission system
    # private = true (=dataset is private) or false (=dataset is public)
    # shared_with = kcloak groups which are able to see that project (0 = ALL?)
    # groups = db.relationship("Groups", cascade="all,delete")

    __permissions__ = (
        Permission("self", read=True, download=True, propagates_to=['files']),
        Permission("files", write=True)
        # Permission("self", read=True, download=True, propagates_to=['collection']),
        # Permission("collection", write=True)
    )


# from sqlalchemy import inspect, func, select
# from sqlalchemy.orm import aliased, column_property


# aDS = aliased(Dataset)
# inspect(Dataset).add_property(
#     'is_latest',
#     column_property(
#         Dataset.version == (
#             select(func.max(aDS.version)).where(aDS.id == Dataset.id).group_by(aDS.id)
#         ).scalar_subquery()
#     )
# )
