from jsonschema import validate
from jsonschema.exceptions import ValidationError

from datetime import datetime

from server.utils.error_handler import (
    BadValue,
    KeyNotFound,
    WrongSchema,
)

# from pydantic import ValidationError as PydanticValidationError

# TODO
# add email validation
# https://github.com/JoshData/python-email-validator
# (for dataset - contact)


def validate_schema(data, schema):
    try:
        validate(instance=data, schema=schema)
    except ValidationError as err:
        raise WrongSchema(err.message)


# def validate_using_pydantic(data, model):
#     try:
#         model(**data)
#     except PydanticValidationError as err:
#         raise WrongSchema(err.message)


def validate_ids(request_data, column_name):

    ids = list(map(lambda x: x.get("id"), request_data))
    if "" in ids:
        raise BadValue("id", "an empty string")

    if None in ids:
        raise KeyNotFound("id")

    if column_name == "project_id":
        if len(ids) != len(set(ids)):
            raise WrongSchema(f"duplicated {column_name}s not allowed")


def validate_timestamps(date_time, time_format):

    try:
        datetime.strptime(date_time, time_format)
    except ValueError:
        raise BadValue("date_time", "wrong format")
