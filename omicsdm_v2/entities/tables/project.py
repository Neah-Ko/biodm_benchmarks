from typing import TYPE_CHECKING, List, Set

from sqlalchemy import DateTime, CHAR, TIMESTAMP, Column, Integer, ForeignKey, Boolean, String, ForeignKeyConstraint, SmallInteger, text
from sqlalchemy.orm import Mapped, relationship, mapped_column

from biodm import config
from biodm.components.table import Base
from biodm.utils.utils import utcnow
from biodm.utils.security import Permission


if TYPE_CHECKING:
    from .dataset import Dataset
    from .visualization import Visualization


class Project(Base):
    """
    Contains the projects e.g. 3TR, PRECISEDADS

    TODO
    Request by GP
    Give users the possibility to follow a project
    ==> meaning they got informed (via Email) when
    a dataset is created/shared/uploaded/deleted

    Schema
    project_id = unique project id
    name = name of the project (human readable)

    last_updated_at: when datasets created/shared or files uploaded/"deleted"
    last_updated_by: user who created/shared datasets or uploaded/deleted files
    last_update: what was the last update e.g. "created", "shared" etc
    owners: kc groups which are allowed to create datasets, upload files etc.

    - extra_cols = JSON containing the following columns:
        - description = string
        - diseases = list of strings
        - Dataset Visibility Default = Boolean
        - Dataset Visibility Changeable = Boolean
        - File Download Allowed = Boolean
        - ceph_path_to_logo = string
    """
    id         = Column(Integer, primary_key=True, autoincrement='sqlite' not in str(config.DATABASE_URL))
    short_name = Column(String,  nullable=False,   unique=True) # form: project_id
    long_name  = Column(String,  nullable=True)                 # form: name

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=utcnow) # server_default="now()")# default=utcnow) # added

    # Apparently not useful.
    # last_updated_at: when datasets created/shared or files uploaded/"deleted"
    # last_updated_by: user who created/shared datasets or uploaded/deleted files
    # last_update: what was the last update e.g. "created", "shared" etc

    description = Column(String, nullable=True)

    # Offloaded to dataset.
        # - diseases = list of strings

    logo_url = Column(String, nullable=True) # form: ceph_path_to_logo
    datasets: Mapped[List["Dataset"]] = relationship(back_populates="project")

    # Refactored by BioDM permission system.
    # owners: kc groups which are allowed to create datasets, upload files etc.
    # - Dataset Visibility Default = Boolean
    # - Dataset Visibility Changeable = Boolean
    # - File Download Allowed = Boolean

    # "project owners" -> WRITE/DOWNLOAD
    #                  -> Leave download empty, if everyone is allowed to download 
    #  -> project owners + other groups for finer grained download access

    __permissions__ = (
        Permission(datasets, write=True, download=True, propagates_to=['files']),
    )
