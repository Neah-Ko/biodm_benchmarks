#!/usr/bin/env python

# could also be used with pydantic
# https://github.com/python-restx/flask-restx/issues/59#issuecomment-899790061

# flask.cli.NoAppException:
# While importing 'server.app', an ImportError was raised.
from flask_restx import fields

# from flask_restx import Resource, reqparse, fields
from server.app import api

# dataset.py
VIEW_ALL_DATASETS_BODY = api.model(
    "All_DATASETS_GET_RESPONSE",
    {
        "pageSize": fields.Integer(description="Number of datasets per page"),
        "page": fields.Integer(description="Page number"),
        "sorted": fields.String(description="Sorted by"),
        "filtered": fields.String(description="Filtered by"),
    },
)
