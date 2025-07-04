#!/usr/bin/env python

"""
Table schemas for the postgres db
"""
from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, ForeignKey, String, Integer, Boolean, DateTime
from sqlalchemy.dialects.postgresql import ARRAY

from server.app import db

# TODO
# create a base class for the table methods
# find_by_id; find_by_name

# https://stackoverflow.com/questions/35814211/how-to-add-a-custom-function-method-in-sqlalchemy-model-to-do-crud-operations

# if we have multiple use cases
# CNAG vs 3TR it might be interesting to dynamically create the sql models:
# https://sparrigan.github.io/sql/sqla/2016/01/03/dynamic-tables.html


class Groups(db.Model):
    """
    Link between tables datasets and group.
    Provides permissions to datasets based on keycloak groups
    """

    __tablename__ = "dataset_group"

    dataset_id = Column(Integer, ForeignKey("datasets.id"), primary_key=True)
    group_id = Column(Integer, ForeignKey("group.id"), primary_key=True)
    owner = Column(Boolean)


class Group(db.Model):
    """
    Contains the keycloak groups e.g. granada
    """

    __tablename__ = "group"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kc_groupname = Column(String, nullable=False)

    @classmethod
    def find_by_id(cls, id):
        """
        unused?
        """
        return cls.query.filter_by(id=id).one_or_none()

    @classmethod
    def find_by_name(cls, groupname):
        """
        returns Group entity based on groupname
        """
        return cls.query.filter_by(kc_groupname=groupname).one_or_none()


class Project(db.Model):
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

    # TODO
    # missing path to logo
    """

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # the unique constraint is missing on integration
    project_id = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated_at = Column(DateTime, nullable=True)
    last_updated_by = Column(String, nullable=True)
    last_update = Column(String, nullable=True)
    owners = Column(ARRAY(Integer), nullable=False)
    extra_cols = Column(JSONB, nullable=True)

    def save_to_db(self):
        """
        insert into db
        """
        db.session.add(self)
        db.session.commit()


class ProjectMapping(db.Model):
    """
    Link between tables project and datasets
    """

    __tablename__ = "project_dataset"

    project_id = Column(Integer, ForeignKey("projects.id"), primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), primary_key=True)

    def save_to_db(self):
        """
        insert into db
        """
        db.session.add(self)
        db.session.commit()


class Dataset(db.Model):

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
    """

    __tablename__ = "datasets"

    # TODO
    # put all the new columns in JSONB field

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, nullable=False)
    dataset_id = Column(String(120), nullable=False)
    name = Column(String(120), nullable=True)
    private = Column(Boolean, default=True)
    submitter_name = Column(String(120), nullable=False)
    submission_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    shared_with = Column(ARRAY(Integer), nullable=False)
    extra_cols = Column(JSONB, nullable=True)

    # is cascade="all,delete" needed?
    groups = db.relationship("Groups", cascade="all,delete")
    files = db.relationship("File", cascade="all,delete")

    def save_to_db(self):
        """
        insert into db
        """
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, id):
        """
        is used e.g. to map the id to the (opal)project_id
        """
        return cls.query.filter_by(id=id).one_or_none()


class File(db.Model):

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

    __tablename__ = "files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), primary_key=True)
    name = Column(String(120), nullable=False)
    submitter_name = Column(String(120), nullable=False)
    submission_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    version = Column(Integer, nullable=False)
    enabled = Column(Boolean, nullable=False)
    upload_finished = Column(Boolean, nullable=False)
    shared_with = Column(ARRAY(Integer), nullable=False)
    extra_cols = Column(JSONB, nullable=True)


class History(db.Model):

    """
    Schema and functions for the table history
    """

    __tablename__ = "history"

    id = Column(Integer, primary_key=True)
    entity_id = Column(String(300), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    username = Column(String(120), nullable=False)
    groups = Column(String(300), nullable=False)
    endpoint = Column(String(1000), nullable=False)
    method = Column(String(120), nullable=False)
    content = Column(JSONB)

    def save_to_db(self):
        """
        insert into db
        """
        db.session.add(self)
        db.session.commit()
