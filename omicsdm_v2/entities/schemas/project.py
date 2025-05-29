from marshmallow import Schema#, pre_dump, post_dump
from marshmallow.fields import String, List, Nested, Integer, Date


class ProjectSchema(Schema):
    id          = Integer()

    short_name  = String(required=True)
    long_name   = String()
    description = String()
    created_at  = Date(dump_ony=True)
    logo_url    = String()

    datasets    = List(Nested('DatasetSchema'))

# id <class 'int'> required: False
# short_name <class 'str'> required: True
# long_name <class 'str'> required: False
# created_at <class 'datetime.datetime'> required: False
# description <class 'str'> required: False
# logo_url <class 'str'> required: False
# ---
# datasets
