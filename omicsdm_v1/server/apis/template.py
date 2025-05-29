#!/usr/bin/env python

from flask import request, send_from_directory, make_response, jsonify
from flask_restx import Resource, Namespace
from flask_cors import cross_origin

from server.security import login_required
from server.app import api, app

ns = Namespace(
    "template",
    description="template related operations",
    decorators=[cross_origin()],
)

parser = api.parser()
parser.add_argument(
    "Authorization", type=str, location="headers", required=True
)


@ns.route("/", methods=("GET",))
class TemplateData(Resource):
    """
    API endpoint that get several templates
    for e.g. dataset creation or file submission

        Resource = /api/template
    """

    @login_required
    def get(self, userid, groups):
        """
        get the template
        """

        # TODO
        # use the template generator to have input validation

        # TODO
        # write tests

        arg = request.args.get("arg")

        filename = ""

        if arg == "project":

            # get group to check if user is allowed to create a project
            group_name = groups[0]
            if group_name != "admin":
                return make_response(
                    jsonify(
                        {"message": "You are not allowed to create a project"}
                    ),
                    403,
                )

            filename = "project"

        elif arg == "dataset":
            # TODO generate this dynamically to prefill responsible partner
            filename = "dataset"

        elif arg == "file":
            filename = "file"

        else:
            return make_response(jsonify({"message": "arg forbidden"}), 405)

        return send_from_directory(
            app.config["TEMPLATE_FOLDER"],
            f"{filename}_template.xlsx",
            as_attachment=True,
        )
