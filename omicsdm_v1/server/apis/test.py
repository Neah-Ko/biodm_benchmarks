#!/usr/bin/env python

"""
For testing if Flask can be accessed from the frontend
"""

from flask_restx import Resource, Namespace
from flask_cors import cross_origin

from server.security import login_required
from server.app import api

ns = Namespace(
    "test", description="test related operations", decorators=[cross_origin()]
)

parser = api.parser()
parser.add_argument(
    "Authorization", type=str, location="headers", required=True
)


@ns.route("/curltest", methods=("GET",))
class CurlTest(Resource):
    def get(self):
        """
        To test curl access
        """
        return {"curlTest": "OK"}


@ns.route("/tokentest", methods=("GET",))
class TokenTest(Resource):
    """
    API endpoint to test if the token is found and returns
    the userid and its associated groups
     - userid = Keycloak id of the user
     - groups = Groups mapped to the Keycloak id (e.g. CNAG/3TR)
     - sub_group = sub groups inside 3TR / CNAG - is that needed?
    """

    @login_required
    def get(self, userid, groups):
        return {"user": userid, "groups": groups}
