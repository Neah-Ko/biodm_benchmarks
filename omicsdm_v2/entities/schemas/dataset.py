from marshmallow import Schema
from marshmallow.fields import String, Date, List, Nested, Integer, Boolean, Email
from marshmallow.validate import OneOf

# from biodm.schemas import UserSchema
from .project import ProjectSchema


class DumpProjectSchema(ProjectSchema):
    class Meta:
        exclude=('datasets',)


# class FileCollectionSchema(Schema):
#     # id = Integer()
#     dataset_id = Integer(required=True)
#     dataset_version = Integer(required=True)
#     files = List(Nested('FileSchema'))


class DatasetSchema(Schema):
    # Pk
    id              = Integer()
    version         = Integer()

    #  Versioned
    is_latest = Boolean(dump_only=True)

    # Classic
    short_name      = String(required=True)
    long_name       = String()
    description     = String()
    submission_date = Date(dump_only=True)

    # Bio
    disease =  String(
        validate=OneOf(("COPD", "ASTHMA", "CD", "UC", "MS", "SLE", "RA", "HEALTHY")),
        required=True
    )
    treatment =  String(required=True)
    molecular_info =  String(required=True)
    sample_type =  String(required=True)
    data_type =  String(required=True)
    value_type =  String(required=True)
    platform =  String(required=True)
    genome_assembly = String(required=True)
    annotation =  String(required=True)
    samples_count =  Integer(required=True)
    features_count =  Integer(required=True)
    features_id =  String(required=True)
    healthy_controls_included = Boolean(required=True)
    additional_info =  String()

    # Fk
    project_id = Integer(required=True)
    submitter_username = String() # Auto-filled
    # contact_username = String(required=True)
    contact_email = Email(required=True)

    # Rel
    project = Nested(DumpProjectSchema)
    tags = List(Nested('TagSchema'))
    files = List(Nested('FileSchema'))


# gen_schema output for reference, required is just a hint
# id <class 'int'> required: False
# version <class 'int'> required: False

# short_name <class 'str'> required: True
# long_name <class 'str'> required: False
# description <class 'str'> required: False
# submission_date <class 'datetime.datetime'> required: False

# disease <class 'str'> required: True
# treatment <class 'str'> required: True
# molecular_info <class 'str'> required: True
# sample_type <class 'str'> required: True
# data_type <class 'str'> required: True
# value_type <class 'str'> required: True
# platform <class 'str'> required: True
# genome_assembly <class 'str'> required: True
# annotation <class 'str'> required: True
# samples_count <class 'int'> required: False
# features_count <class 'int'> required: False
# features_id <class 'str'> required: True
# healthy_controls_included <class 'bool'> required: False
# additional_info <class 'str'> required: False

# project_id <class 'int'> required: True
# submitter_username <class 'str'> required: True
# contact_username <class 'str'> required: True
# ---
# project
# tags
# files
