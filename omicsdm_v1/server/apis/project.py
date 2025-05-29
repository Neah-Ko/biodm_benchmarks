#!/usr/bin/env python
from sqlalchemy.orm.attributes import flag_modified

from flask import jsonify, make_response, request
from flask_restx import Resource, Namespace
from flask_cors import cross_origin

from server.app import app, api, db
from server.model import Group, Project
from server.security import login_required

from server.utils.table_methods import db_add

from server.security import get_token

from server.utils.table_methods import db_commit

from server.factories.create_factory import react_create_builder, react_create_builder_returning  

from server.factories.view_factory import data_view_builder


from server.utils.schema import get_obj_schema
from server.utils.validators import validate_schema

from server.utils.permissions import is_valid_kc_group


parser = api.parser()
parser.add_argument(
    "Authorization", type=str, location="headers", required=True
)

ns = Namespace(
    "projects",
    description="projects related operations",
    decorators=[cross_origin()],
)

# TODO
# API to return the project submission cols to the client
# so the client no longer needs the cols to be defined
# in the config.js


@api.expect(parser)
@ns.route("/validate", methods=(["POST"]))
class ProjectCreationValidation(Resource):

    """
    Validate the submission of multiple projects
    Make sure that in all the to be to the db added datasets
    the project_id does not already exists
    """

    @login_required
    @get_token
    @api.doc(description="Returns...")
    @api.response(500, "Server error")
    @api.response(200, "Success")
    def post(self, userid, groups, token):

        group_name = groups[0]
        # FIXME
        # this only picks the first group
        # -> so it only works if one user has only one keycloak group
        # better would be to pick all possible groups
        # and then change the queries to _or a usr

        group = (
            db.session.query(Group)
            .filter_by(kc_groupname=group_name)
            .one_or_none()
        )

        request_data = request.get_json()

        response, status_code = react_create_builder(
            group,
            group_name,
            userid,
            Project,
            "PROJECT",
            "project_id",
            request_data,
            token=token,
            add_to_db=False,
        )

        return make_response(jsonify(response), status_code)


@api.expect(parser)
@ns.route("/submissioncols", methods=(["GET"]))
class ProjectSubmissionCols(Resource):
    """
    API endpoint that get project submission fields for
    the React Project Submission View
    """

    @login_required
    @api.doc(description="Returns...")
    @api.response(500, "Server error")
    @api.response(200, "Success")
    def get(self, userid, groups):
        """
        Get project submission fields
        """

        group_name = groups[0]
        if "admin" not in group_name:
            return make_response(
                jsonify({"message": "Only admin users can create projects"}),
                405,
            )

        return jsonify({"message": app.config["SUBMIT_PROJECTS_HEADERS"]}, 200)


# TODO
# merge submitcols and viewcols into one endpoint
@api.expect(parser)
@ns.route("/adminviewcols", methods=(["POST"]))
class ProjectViewCols(Resource):
    """
    API endpoint that get project view fields for
    the React Project View
    """

    @login_required
    @api.doc(description="Returns...")
    @api.response(500, "Server error")
    @api.response(200, "Success")
    def post(self, userid, groups):
        """
        Get project submission fields
        """

        group_name = groups[0]
        if "admin" not in group_name:
            return make_response(
                jsonify({"message": "Only admin users can view the projects"}),
                405,
            )

        return jsonify({"headers": app.config["PROJECTS_VIEW_HEADERS"]}, 200)


@api.expect(parser)
class ProjectCreate(Resource):
    """
    API endpoint that get dataset Fields For React Experiment View
        Resource = /api/dataset
    """

    @get_token
    @login_required
    @api.doc(description="Returns...")
    @api.response(500, "Server error")
    @api.response(200, "Success")
    def post(self, userid, groups, token):
        """
        Create a new project
        """

        group_name = groups[0]
        if "admin" not in group_name:
            return make_response(
                jsonify({"message": "Only admin users can create a project"}),
                405,
            )

        group = (
            db.session.query(Group)
            .filter_by(kc_groupname=group_name)
            .one_or_none()
        )
        
        request_data = request.get_json()
        if not request_data and isinstance(request.data, bytes):
            import json
            request_data = json.loads(request.data)

        response, status_code = react_create_builder_returning(
            group,
            group_name,
            userid,
            Project,
            "PROJECT",
            "project_id",
            request_data,
            token=token,
        )



        return make_response(jsonify({"message": response}), status_code)


@api.expect(parser)
@ns.route("/", methods=(["POST"]))
class ProjectList(Resource):
    """
    project resource
    """

    @login_required
    def post(self, userid, groups):
        """
        Get all the projects data by keycloak group
        """

        projects_list = []

        ns.logger.info("Get all projects data by keycloak group")

        # ! FIXME
        # error handler when no group is found is missing
        # the group can be empty if the token is expired
        # => return 401

        # check where the error handler should be called
        # maybe best in the login_required decorator
        group_name = groups[0]
        group = (
            db.session.query(Group)
            .filter_by(kc_groupname=group_name)
            .one_or_none()
        )

        # TODO
        # needs to be tested
        if group is None:
            ns.logger.info(f"add kc group {group_name} to db")
            group = Group(kc_groupname=group_name)
            db_add(group)

        # only show the projects in which the group.id is in Project.owners
        projects = (
            db.session.query(Project).filter(Project.owners.any(group.id))
        ).all()

        # this should be in config.py
        col_mapping = {
            "project_id": "project_id",
            "name": "name",
        }

        # TODO
        # put below into config.py
        extra_cols = ["diseases", "logo_url", "description"]

        # TODO
        # test is missing for len(projects) == 0
        if len(projects) > 0:
            for project in projects:
                data = {k: getattr(project, v) for k, v in col_mapping.items()}

                for col in extra_cols:
                    data[col] = getattr(project, "extra_cols")[col]

                projects_list.append(data)

        return make_response(jsonify({"projects": projects_list}), 200)


@api.expect(parser)
@ns.route("/", methods=(["POST"]))
class ProjectDataAdminView(Resource):
    """
    Project Data Admin View
    """

    # TODO
    # misses functionality to get filtered

    @login_required
    def post(self, userid, groups):
        """
        Get all the project data
        """
        # !FIMXE
        # only works when a user has only one group
        group_name = groups[0]
        if group_name != "admin":
            return make_response(
                jsonify({"message": "Only admin users can view projects"}),
                404,
            )

        res = data_view_builder(group_name, Project, "PROJECTS", request, ns)

        # # TODO
        # # workaround till the
        # # errors are handled correctly in
        # # admin_view_builder
        # try:
        #     if projects.status_code != 200:
        #         return projects
        # except Exception:
        #     pass

        # # TODO
        # # schema validation is missing

        # # this should be in config.py
        # col_mapping = {
        #     "id": "id",
        #     "project_id": "project_id",
        #     "name": "name",
        #     "owners": "owners",
        # }

        # # TODO
        # # put below into config.py
        # extra_cols = [
        #     "diseases",
        #     "logo_url",
        #     "description",
        #     "dataset_visibility_default",
        #     "dataset_visibility_changeable",
        #     "file_dl_allowed",
        # ]

        # for project in projects:
        #     data = {k: getattr(project, v) for k, v in col_mapping.items()}

        #     # get the owners keycloak group from the database
        #     db_query = (
        #         db.session.query(Group)
        #         .filter(Group.id.in_(data["owners"]))
        #         .with_entities(Group.kc_groupname)
        #         .all()
        #     )

        #     owners = [group[0] for group in db_query]
        #     data["owners"] = ",".join(owners)

        #     for col in extra_cols:
        #         try:
        #             data[col] = str(getattr(project, "extra_cols")[col])

        #         # below is only for a database migration
        #         # can only be tested with a database modification
        #         # whithin a test run
        #         except TypeError as err:
        #             if str(err) != "'NoneType' object is not subscriptable":
        #                 raise
        #             else:
        #                 data[col] = ""
        #         except KeyError:
        #             data[col] = ""

        #     res["items"].append(data)

        return res


@api.expect(parser)
@ns.route("/", methods=(["POST"]))
class ProjectUpdate(Resource):
    """
    Dataset resource
    """

    @get_token
    @login_required
    def post(self, userid, groups, token):
        """
        Update a project
        """

        # TODO
        # enable multiple project updates at once

        # put all the AdminUpdates into a function
        # - ProjectUpdate (project.py)
        # - DatasetDataUpdate (dataset.py)
        # - FileDataUpdate (file.py)

        if "admin" not in groups:
            return make_response(
                jsonify({"message": "Only admin users can update a project"}),
                405,
            )

        request_data = request.get_json()

        # validate the request data
        fields = ["dbRowIds", "field", "value"]
        schema = get_obj_schema(
            {k: {"type": "string"} for k in fields}, required=fields
        )

        schema["properties"]["dbRowIds"] = {
            "type": "array",
            "items": {"type": "integer"},
        }

        # TODO
        # make sure that for fields not all values are allowed
        allowed_fields = [
            "name",
            "owners",
            "diseases",
            "logo_url",
            "description",
            "dataset_visibility_default",
            "dataset_visibility_changeable",
            "file_dl_allowed",
        ]

        schema["properties"]["field"]["enum"] = allowed_fields

        # this should be in config.py
        field_to_possible_values = {
            "dataset_visibility_default": ["visible to all", "private"],
            "dataset_visibility_changeable": ["True", "False"],
            "file_dl_allowed": ["True", "False"],
        }

        selectedField = request_data["field"]
        if selectedField in field_to_possible_values:
            possible_values = field_to_possible_values[selectedField]

            schema["properties"]["value"]["enum"] = possible_values

        if selectedField == "logo_url":
            schema["properties"]["value"]["type"] = "string"
            schema["properties"]["value"]["format"] = "uri"
            schema["properties"]["value"]["pattern"] = "^(http|https)://.*$"

        validate_schema(request_data, schema)

        selectedProjects = request_data["dbRowIds"]
        newValue = request_data["value"]

        projects = (
            db.session.query(Project)
            .with_for_update()  # locks the row
            .filter(Project.id.in_(selectedProjects))
            .all()
        )

        if not projects:
            return make_response(
                jsonify({"message": "Project not found"}), 404
            )

        extra_cols = [
            "diseases",
            "logo_url",
            "description",
            "dataset_visibility_default",
            "dataset_visibility_changeable",
            "file_dl_allowed",
        ]

        # TODO
        # only update the value if the new value is actually different

        str_to_bool = {"True": True, "False": False}

        for project in projects:
            if selectedField in extra_cols:

                if newValue in str_to_bool:
                    newValue = str_to_bool[newValue]

                try:
                    project.extra_cols[selectedField] = newValue
                except TypeError as err:
                    exp = "'NoneType' object does not support item assignment"
                    err = str(err)
                    if err != exp:
                        raise
                    else:
                        project.extra_cols = {}
                        project.extra_cols[selectedField] = newValue

                flag_modified(project, "extra_cols")

            elif selectedField == "owners":

                updatedOwners = newValue.split(",")

                groups = (
                    db.session.query(Group)
                    .filter(Group.kc_groupname.in_(updatedOwners))
                    .with_entities(Group.id)
                    .all()
                )

                error_msg = "at least one of the owners is invalid"
                existing_groups_count = len(groups)
                if (existing_groups_count == 0) or (
                    existing_groups_count != len(updatedOwners)
                ):
                    for owner in updatedOwners:
                        if is_valid_kc_group(owner, token):
                            group = Group(kc_groupname=owner)
                            db.session.add(group)
                        else:
                            return make_response(
                                jsonify({"message": error_msg}), 404
                            )

                    groups = (
                        db.session.query(Group)
                        .filter(Group.kc_groupname.in_(updatedOwners))
                        .with_entities(Group.id)
                        .all()
                    )

                newValue = [group[0] for group in groups]

            setattr(project, selectedField, newValue)
        db_commit()

        return make_response(jsonify({"message": "project updated"}), 200)


# Resources for the project api


ns.add_resource(
    ProjectSubmissionCols,
    "/submissioncols",
    endpoint="projects_submission_cols",
)

ns.add_resource(
    ProjectViewCols, "/adminviewcols", endpoint="projects_view_cols"
)

ns.add_resource(ProjectCreate, "/create", endpoint="projects_create")

ns.add_resource(ProjectList, "/all", endpoint="projects_data")

ns.add_resource(
    ProjectDataAdminView, "/admin/view", endpoint="projects_data_all"
)
ns.add_resource(ProjectUpdate, "/admin/update", endpoint="projects_update")
