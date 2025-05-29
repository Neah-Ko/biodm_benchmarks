from sqlalchemy import Column, Table, ForeignKey, ForeignKeyConstraint

from biodm.components.table import Base


## Associative tables for join operations
asso_dataset_tag = Table(
    "ASSO_DATASET_TAG",
    Base.metadata,
    Column("tag_name",          ForeignKey("TAG.name", ondelete="CASCADE"),        primary_key=True),
    Column("dataset_id",                                       primary_key=True),
    Column("dataset_version",                                  primary_key=True),
    ForeignKeyConstraint(
        ['dataset_id', 'dataset_version'],
        ['DATASET.id', 'DATASET.version'],
        onupdate="CASCADE",
        ondelete="CASCADE"
    )
)

asso_dataset_file = Table(
    "ASSO_DATASET_FILE",
    Base.metadata,
    Column("dataset_id",                                       primary_key=True),
    Column("dataset_version",                                  primary_key=True),
    Column("file_id",                                          primary_key=True),
    Column("file_version",                                     primary_key=True),
    ForeignKeyConstraint(
        ['dataset_id', 'dataset_version'],
        ['DATASET.id', 'DATASET.version']
    ),
    ForeignKeyConstraint(
        ['file_id', 'file_version'],
        ['FILE.id', 'FILE.version']
    )
)

# asso_dscoll_file = Table(
#     "ASSO_DSCOLL_FILE",
#     Base.metadata,
#     Column("filecollection_id", ForeignKey("FILECOLLECTION.id"),   primary_key=True),
#     Column("file_id",                                              primary_key=True),
#     Column("file_version",                                         primary_key=True),
#     ForeignKeyConstraint(
#         ['file_id', 'file_version'],
#         ['FILE.id', 'FILE.version']
#     )
# )

# asso_dscoll_file = Table(
#     "ASSO_DSCOLL_FILE",
#     Base.metadata,
#     Column("dataset_id",                                       primary_key=True),
#     Column("dataset_version",                                  primary_key=True),
#     Column("file_id",                                          primary_key=True),
#     Column("file_version",                                     primary_key=True),
#     ForeignKeyConstraint(
#         ['dataset_id', 'dataset_version'],
#         ['FILECOLLECTION.dataset_id', 'FILECOLLECTION.dataset_version']
#     ),
#     ForeignKeyConstraint(
#         ['file_id', 'file_version'],
#         ['FILE.id', 'FILE.version']
#     )
# )
