from marshmallow import Schema
from marshmallow.fields import String


class TagSchema(Schema):
    name = String(required=True)
