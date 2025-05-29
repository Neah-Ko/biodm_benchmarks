#!/usr/bin/env python
from copy import copy, deepcopy

from flask import jsonify, make_response, request
from flask_restx import Resource, Namespace
from flask_cors import cross_origin
from sqlalchemy import or_


# doc_models needs to be imported before import app
from server.apis.doc_models import VIEW_ALL_DATASETS_BODY

from server.app import app, api, db

from server.model import File, Group, Groups, Dataset, Project, ProjectMapping
from server.security import login_required, get_token
from server.factories.view_factory import data_view_builder

# from server.factories.admin_factory import admin_view_builder
from server.factories.create_factory import react_create_builder
from server.utils.table_methods import db_add, db_commit
from server.utils.error_handler import (
    InvalidGroup,
    WrongSchema,
    handle_expected_err,
)

from server.utils.ceph import create_presigned_url

from server.utils.permissions import is_valid_kc_group

from server.utils.schema import get_obj_schema
from server.utils.validators import validate_schema

from sqlalchemy.orm.attributes import flag_modified

# optimize api that it follows best practices
# https://stackoverflow.com/questions/20715238/flask-restful-api-multiple-and-complex-endpoints

# TODO
# client should not need to be able to build the urls
# from scratch better would be to only show the top level urls
# like datasets, files, groups, etc.
# and then the server returns the urls for the sub-resources

# How to use add_resource with namespace ?
# https://github.com/noirbizarre/flask-restplus/issues/631

parser = api.parser()
parser.add_argument(
    "Authorization", type=str, location="headers", required=True
)

ns = Namespace(
    "datasets",
    description="datasets related operations",
    decorators=[cross_origin()],
)

# !FIXME
# With the following project settings the dataset cannot be shared
# The following error is thrown:
# The datasets of precisedads_test cannot be shared/unshared
# Dataset visibility private
# Dataset visibility changeable False

# this also needs to be tested


@api.expect(parser)
@ns.route("/validate", methods=(["POST"]))
class DatasetSubmissionValidation(Resource):

    """
    Validate the submission of multiple datasets
    Make sure that in all the to be to the db added datasets
    the dataset_id is not already exists
    """

    @login_required
    @api.doc(description="Returns...")
    @api.response(500, "Server error")
    @api.response(200, "Success")
    def post(self, userid, groups):

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
            Dataset,
            "DATASET",
            "dataset_id",
            request_data,
            add_to_db=False,
        )

        return make_response(jsonify(response), status_code)


@api.expect(parser)
@ns.route("/create", methods=(["POST"]))
class DatasetSubmission(Resource):
    @login_required
    @api.doc(description="Returns...")
    @api.response(500, "Server error")
    @api.response(200, "Success")
    def post(self, userid, groups):

        # FIXME
        # the disease validation seems to be broken
        # because it was possible to add a dataset with the disease name
        # select

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

        policy_file = request_data.get("file")
        clinical_file = request_data.get("file2")

        # TODO
        # payloads no longer should be a list
        request_data = [request_data]

        response, status_code = react_create_builder(
            group,
            group_name,
            userid,
            Dataset,
            "DATASET",
            "dataset_id",
            request_data,
        )

        if not policy_file and not clinical_file:
            return make_response(jsonify({"message": response}), status_code)

        dataset_id = response[1]
        policy_aws_key = ""
        clinical_aws_key = ""

        if policy_file:
            policy_aws_key = "/".join(
                [group_name, dataset_id, "dataPolicy", policy_file[0]]
            )

        if clinical_file:
            clinical_aws_key = "/".join(
                [group_name, dataset_id, "clinical", clinical_file[0]]
            )

        return make_response(
            jsonify(
                {
                    "message": "dataset inserted",
                    "dataPolicyAwsKey": policy_aws_key,
                    "clinicalDataAwsKey": clinical_aws_key,
                }
            ),
            200,
        )


@api.expect(parser)
@ns.route("/", methods=(["POST", "GET", "PUT"]))
class DatasetData(Resource):
    """
    API endpoint that get dataset Fields For React Experiment View
        Resource = /api/dataset
    """

    @get_token
    @login_required
    def put(self, userid, groups, token):
        """
        update a Dataset of a certain userid
        """

        arg = request.args.get("arg")

        if arg not in ["addGroup", "removeGroup", "dataset", "group"]:
            # raise
            return make_response(jsonify({"message": "arg forbidden"}), 405)

        # FIXME
        # this only picks the first group
        user_group_name = groups[0]

        user_group_id = (
            Group.query.filter_by(kc_groupname=user_group_name)
            .with_entities(Group.id)
            .one_or_none()
        )

        if user_group_id is None:
            return make_response(jsonify({"message": "group not found"}), 404)

        user_group_id = user_group_id[0]

        # TODO
        # better do the put by json and not by url modification
        # doing it by json you could summarize puts into one request
        # --> (un)share multiple datasets with different groups with one query

        # could look kind of like this
        # data = {
        #   "ID1":{{addGroup}:["group1", "group2"],removeGroup:["group3"]},
        #   "ID2":{{addGroup}:["group3"],removeGroup:["group1","group2"]},
        #   "ID3":{{addGroup}:["ALL"],removeGroup:[]},
        #   "ID4":{{addGroup}:[],removeGroup:[ALL]}
        # }

        # at the moment it is working like this
        # /datasets?arg=addGroup&dataset=t1,t2,t3&group=ALL
        # /datasets?arg=addGroup&dataset=t1,t2,t3&group=cnag

        # /datasets?arg=removeGroup&dataset=t1,t2,t3&group=ALL
        # /datasets?arg=removeGroup&dataset=t1,t2,t3&group=cnag

        project_id = request.args.get("project")

        # check if it is allowed to share/unshare a dataset
        proj_extra_cols = (
            db.session.query(Project)
            .filter_by(project_id=project_id)
            .with_entities(Project.extra_cols)
            .one_or_none()
        )

        if proj_extra_cols is None:
            return make_response(
                jsonify({"message": "project not found"}), 404
            )

        if proj_extra_cols[0]["dataset_visibility_changeable"] is False:
            return make_response(
                jsonify(
                    {
                        "message": "dataset visibility is not changeable",
                        "project": project_id,
                    }
                ),
                405,
            )

            # TODO
            # on the frontend return an error message

        # needs to be tested

        # TODO if one of the args above is None
        # raise an error

        group_name = request.args.get("group")
        ds_ids = request.args.get("dataset")
        for ds_id in ds_ids.split(","):

            if group_name != "ALL":
                if is_valid_kc_group(group_name, token) is False:
                    raise (InvalidGroup(group_name))

                group = Group.find_by_name(group_name)
                if group is None:
                    group_obj = Group(kc_groupname=group_name)
                    db_add(group_obj)
                    group = Group.find_by_name(group_name)

                # do not allow adding/removal if the user's group is owner:
                group_id = group.id
                if group_id == user_group_id:
                    # raise
                    return make_response(
                        jsonify({"message": "group is owner"}), 405
                    )

            # TODO
            # test is still missing

            ds = (
                db.session.query(Dataset)
                .with_for_update()  # locks the row
                .join(Groups, Dataset.id == Groups.dataset_id)
                .join(Project, Dataset.project_id == Project.id)
                .filter(Groups.group_id == user_group_id)
                .filter(Project.project_id == project_id)
                .filter(Dataset.dataset_id == ds_id)
                .one_or_none()
            )

            if ds is None:
                # raise
                return make_response(
                    jsonify({"message": "dataset not exist"}), 404
                )

            # does not work w/o copy
            shared_groups = copy(ds.shared_with)

            if group_name == "ALL":
                shared_groups = []
                ds.private = False

                if arg == "removeGroup":
                    ds.private = True  # set to private

            if arg == "addGroup" and group_name != "ALL":
                if group_id in shared_groups:
                    continue

                ds.private = True
                shared_groups.append(group_id)

            elif arg == "removeGroup" and group_name != "ALL":

                if group_id not in shared_groups:
                    continue

                shared_groups.remove(group_id)

            ds.shared_with = shared_groups

            # updating the shared_with on the Dataset level
            # overwrites the shared with on file level*
            # *sharing on file level is not implemented

            files = (
                db.session.query(File).filter(File.dataset_id == ds.id).all()
            )

            for file in files:
                file.shared_with = shared_groups

            db_commit()

        return make_response(jsonify({"message": "groups updated"}), 200)


@api.expect(parser)
@ns.route("/", methods=(["POST"]))
class DatasetExtraFilesUploadFinished(Resource):
    """
    update the extra_cols of the dataset
    with the uploaded files (data policy or clinical data)
    Note: the endpoint is triggered for each file individually
    """

    @login_required
    def post(self, userid, groups):
        group_name = groups[0]
        group = Group.find_by_name(group_name)

        if group is None:
            # group is only none if the user's keycloak group
            # has never interacted with the server before
            # => blocks possible malicious actions
            return make_response(
                jsonify({"message": "user not authorized"}), 405
            )

        # TODO
        # json schema validation is missing

        data = request.get_json()
        aws_key = data["aws_key"]

        kc_group, dataset_id, sub_key, file_name = aws_key.split("/")
        # make sure that the group is the same as the user's group name
        if kc_group != group_name:
            return make_response(
                jsonify({"message": "group name does not match"}),
                405,
            )

        dataset = (
            db.session.query(Dataset)
            .with_for_update()  # locks the row
            .join(Groups, Dataset.id == Groups.dataset_id)
            .filter(Groups.group_id == group.id)
            .filter(Dataset.dataset_id == dataset_id)
            .one_or_none()
        )

        if dataset is None:
            return make_response(
                jsonify({"message": "dataset does not exist"}), 404
            )

        extra_file_mapping = {
            "dataPolicy": "file",
            "clinical": "file2",
        }

        col = extra_file_mapping[sub_key]
        dataset.extra_cols[col] = [file_name]
        flag_modified(dataset, "extra_cols")
        db_commit()

        return make_response(jsonify({"message": "File upload finished"}), 200)


@api.expect(parser)
@ns.route("/", methods=(["POST"]))
class DatasetExtraFilesDownload(Resource):
    @login_required
    def post(self, userid, groups):
        """
        create a presigned url for downloading
        the extra files (data policy or clinical data)
        Note: the endpoint is triggered for each file individually
        """

        group_name = groups[0]
        group = Group.find_by_name(group_name)

        if group is None:
            # group is only none if the user's keycloak group
            # has never interacted with the server before
            # => blocks possible malicious actions
            return make_response(
                jsonify({"message": "user not authorized"}), 405
            )

        data = request.get_json()

        fields = ["datasetId", "fileType"]
        schema = get_obj_schema(
            {k: {"type": "string"} for k in fields}, required=fields
        )
        schema["properties"]["datasetId"]["type"] = "integer"
        validate_schema(data, schema)

        or_conditions = [
            Groups.group_id == group.id,
            Dataset.shared_with.contains([group.id]),
            Dataset.private.is_(False),
        ]

        query = (
            db.session.query(Dataset)
            .join(Groups, Dataset.id == Groups.dataset_id)
            .join(Group, Groups.group_id == Group.id)
            .filter(or_(*or_conditions))
            .filter(Dataset.id == data["datasetId"])
            .with_entities(Dataset, Group.kc_groupname)
            .one_or_none()
        )

        if query is None:
            return make_response(
                jsonify({"message": "dataset does not exist"}), 404
            )
        dataset, ds_owner_group = query

        extra_file_mapping = {
            "dataPolicy": "file",
            "clinical": "file2",
        }

        file_type = data["fileType"]
        col = extra_file_mapping[file_type]

        presigned_url = create_presigned_url(
            app.config,
            "get_object",
            ds_owner_group,
            dataset.dataset_id,
            dataset.extra_cols[col][0],
            None,
            subkey=file_type,
        )

        msg_mapping = {
            "dataPolicy": "Policy data url created",
            "clinical": "Clinical data url created",
        }

        return make_response(
            jsonify(
                {
                    "message": msg_mapping[file_type],
                    "presigned_url": presigned_url,
                }
            ),
            200,
        )


@api.expect(parser)
@ns.route("/", methods=(["POST"]))
class DatasetView(Resource):
    """
    Dataset resource
    """

    @login_required
    @api.doc(body=VIEW_ALL_DATASETS_BODY, description="Returns...")
    @api.response(500, "Server error")
    @api.response(200, "Success")
    def post(self, userid, groups):
        """
        Get all the datasets data by keycloak group
        """

        ns.logger.info("Get all datasets data by keycloak group")

        # !FIXE
        # only works when the user is only in one group
        group_name = groups[0]
        # group = (
        #     db.session.query(Group)
        #     .filter_by(kc_groupname=group_name)
        #     .one_or_none()
        # )

        # request_data = request.get_json()

        result = data_view_builder(
            group_name, Dataset, "DATASETS", request, ns
        )
        return result


@api.expect(parser)
@ns.route("/", methods=(["POST"]))
class DatasetsList(Resource):
    """
    Dataset resource
    """

    @login_required
    @api.doc(
        description="""
            Returns list of all dataset IDs of the user's kc group;
            can be filtered by dataset id
        """
    )
    @api.response(500, "Server error")
    @api.response(200, "Success")
    def post(self, userid, groups):
        """
        Get all datasets by keycloak group and filtered by project_id
        (additionally it can be filtered by the dataset_id)
        """

        ns.logger.info("Get all datasets by keycloak group")

        group_name = groups[0]
        group = (
            db.session.query(Group)
            .filter_by(kc_groupname=group_name)
            .with_entities(Group.id)
            .one_or_none()
        )

        if group is None:
            # raise
            return make_response(jsonify({"message": "group not exist"}), 404)

        query = request.get_json()

        fields = ["project_id", "dataset_id"]
        schema = get_obj_schema(
            {k: {"type": "string"} for k in fields}, required=fields
        )
        validate_schema(query, schema)

        # TODO
        # add a test for filter by project_id
        # 1. if project id is not in the list of the user's projects

        search = query.get("dataset_id")

        # this returns the list of dataset_ids
        dataset_ids = (
            db.session.query(ProjectMapping)
            .join(Project, ProjectMapping.project_id == Project.id)
            .join(Dataset, ProjectMapping.dataset_id == Dataset.id)
            .join(Groups, Dataset.id == Groups.dataset_id)
            .filter(Project.project_id == query.get("project_id"))
            .filter(Groups.group_id == group[0])
            .filter(Dataset.dataset_id.contains(search))
            .with_entities(ProjectMapping.dataset_id)
            .all()
        )
        if len(dataset_ids) == 0:
            # raise
            return make_response(
                jsonify(
                    {
                        "message": (
                            "no access to that project or "
                            "the project has no datasets yet"
                        )
                    }
                ),
                404,
            )

        # TODO
        # better would be to filter by list
        # => no for loop
        # => no sort at the end

        # but needs an extra query to get the "dataset_id"s
        datasets = []
        for dataset_id in dataset_ids:
            ds = (
                db.session.query(Dataset)
                .filter(Dataset.id == dataset_id[0])
                .with_entities(Dataset.dataset_id)
                .one_or_none()
            )
            datasets.append(ds[0])

        # sort datasets ascending
        datasets.sort()

        # res = [ds[0] for ds in datasets]
        return datasets


@api.expect(parser)
@ns.route("/", methods=(["POST"]))
class DatasetsSubmissionCols(Resource):
    """
    Dataset resource
    """

    @login_required
    @api.doc(
        description="""
            Modify the columns for dataset submission
        """
    )
    @api.response(500, "Server error")
    @api.response(200, "Success")
    def post(self, userid, groups):
        """
        Get the columnn specification for the dataset submission
        from the project table
        """

        # TODO
        # tests still missing

        # TODO
        # at the moment this endpoint only returns the selection options
        # for the disease column but in future it should return the
        # specification for all the columns

        # TODO
        # this function should include the possibility to return the
        # dataset_visibility_default_value and
        # if dataset_visibility is changeable

        # put the dataset_visibility default value on position 0
        # in the list of the options
        # if dataset_visibility is NOT changeable
        # then the default value should be the first option

        ns.logger.info("Get all datasets by keycloak group")

        # !FIXME
        # this only works when the user is only in one group
        group_name = groups[0]
        group = (
            db.session.query(Group)
            .filter_by(kc_groupname=group_name)
            .with_entities(Group.id)
            .one_or_none()
        )

        if group is None:
            group_obj = Group(kc_groupname=group_name)
            db_add(group_obj)
            group = Group.find_by_name(group_name)

        query = request.get_json()

        fields = ["project_id"]
        schema = get_obj_schema(
            {k: {"type": "string"} for k in fields}, required=fields
        )
        validate_schema(query, schema)

        # TODO
        # add a test for filter by project_id
        project_id = query.get("project_id")

        project_extra_cols = (
            db.session.query(Project)
            .filter(Project.project_id == project_id)
            .filter(Project.owners.contains([group.id]))
            .with_entities(Project.extra_cols)
            .one_or_none()
        )
        if project_extra_cols is None:
            # raise
            return make_response(
                jsonify({"message": "no access to that project"}), 404
            )

        # TODO
        # put col_id mapping and the default values in config file

        # mapping react col_id to dataset extra_col_id
        col_id_mapping = {
            "disease": "diseases",
        }

        # deep copy the default values from the config file
        headers = deepcopy(app.config["SUBMIT_DATASETS_HEADERS"])
        for header in headers:
            col_id = header["id"]
            if header["id"] == "disease":
                default = ["select", "healthy control"]
                options = project_extra_cols[0][col_id_mapping[col_id]]
                options = default + options.split(",")
                header["selection"] = options

            elif col_id == "visibility":
                extra_cols = project_extra_cols[0]
                dataset_visibility_default = extra_cols[
                    "dataset_visibility_default"
                ]
                options = [dataset_visibility_default]

                if extra_cols["dataset_visibility_changeable"]:
                    if dataset_visibility_default == "visible to all":
                        options.append("private")
                    else:
                        options.append("visible to all")

                header["selection"] = options

        return make_response(
            jsonify(
                {
                    "message": "colum options returned",
                    "headers": headers,
                }
            ),
            200,
        )


# TODO
# merge submitcols and viewcols into one endpoint


@api.expect(parser)
@ns.route("/viewcols", methods=(["GET"]))
class DatasetsViewCols(Resource):
    """
    API endpoint that get the dataset view fields for
    the React Dataset View
    """

    @login_required
    @api.doc(description="Returns...")
    @api.response(500, "Server error")
    @api.response(200, "Success")
    def get(self, userid, groups):
        """
        Get datasets view fields
        """
        return jsonify({"headers": app.config["DATASETS_VIEW_HEADERS"]}, 200)


# TODO
# merge all cols into one endpoint

# TODO
# why is the endpoint below a POST and not a GET?

# TODO
# it should not be needed that only admins can see the cols
# would be better to make it more generic


@api.expect(parser)
@ns.route("/adminviewcols", methods=(["POST"]))
class DatasetsAdminViewCols(Resource):
    """
    API endpoint that get the dataset view fields for
    the React Dataset View
    """

    @login_required
    @api.doc(description="Returns...")
    @api.response(500, "Server error")
    @api.response(200, "Success")
    def post(self, userid, groups):
        """
        Get datasets admin columns
        """

        group_name = groups[0]
        if "admin" not in group_name:
            return make_response(
                jsonify({"message": "endpoint only for admins"}),
                405,
            )

        cols = deepcopy(app.config["DATASETS_VIEW_HEADERS"])
        cols[0] = {"key": "id", "label": "id"}

        return jsonify({"headers": cols}, 200)


class DatasetDataAdminView(Resource):
    @login_required
    def post(self, userid, groups):
        """
        Get all the dataset data
        """

        ns.logger.info("Get all datasets data")

        # !FIMXE
        # only works when a user has only one group
        group_name = groups[0]

        if group_name != "admin":
            return make_response(
                jsonify({"message": "Only admin users can view datasets"}),
                404,
            )

        res = data_view_builder(group_name, Dataset, "DATASETS", request, ns)
        return res


def update_dataset_data_in_extra_cols(newValue, selectedField, dataset):
    """
    Update the dataset data
    """

    str_to_bool = {"True": True, "False": False}

    # TODO
    # this has not test yet
    if newValue in str_to_bool:
        newValue = str_to_bool[newValue]

    if "presigned_url" in selectedField and newValue != "regenerate":
        return make_response(
            jsonify(
                {"message": "enter regenerate to renew the presigned url"}
            ),
            503,
        )

    if selectedField == "disease":
        # verify that the disease value is one of the values
        # defined on the project level
        project_data = (
            db.session.query(Project)
            .filter(Project.id == dataset.project_id)
            .with_entities(Project.project_id, Project.extra_cols)
            .one_or_none()
        )

        if project_data:
            allowed_diseases = project_data[1]["diseases"].split(",")
            allowed_diseases.append("healthy control")
            project_id = project_data[0]

            if newValue not in allowed_diseases:
                err = (
                    f"{newValue} not allowed for the project "
                    f"{project_id},please select"
                    "one of the following:"
                    f"{','.join(allowed_diseases)}"
                )
                # throw an error
                raise WrongSchema(err)

        else:
            dataset_proj_ids = (
                db.session.query(Dataset)
                .filter(Dataset.project_id == 0)
                .with_entities(Dataset.project_id)
                .all()
            )
            if dataset_proj_ids is None:
                # raise an error
                return make_response(
                    jsonify({"message": "project not found"}), 404
                )

    try:
        dataset.extra_cols[selectedField] = newValue
    except TypeError as err:
        expected = "'NoneType' object does not support item assignment"
        handle_expected_err(err, expected)

        dataset.extra_cols = {}
        dataset.extra_cols[selectedField] = newValue

    flag_modified(dataset, "extra_cols")
    return dataset


def update_dataset_data_in_normal_cols(newValue, selectedField, dataset):
    """
    Update the dataset data
    """

    # only allow changing the project if dataset.project_id is 0
    if selectedField == "project_id":
        if dataset.project_id != 0:
            return make_response(
                jsonify(
                    {
                        "message": "Cannot change project_id",
                    }
                ),
                400,
            )
        else:
            # check if the new project_id exists
            project = (
                db.session.query(Project)
                .filter(Project.project_id == newValue)
                .one_or_none()
            )

            if project is None:
                return make_response(
                    jsonify(
                        {
                            "message": "Project not found",
                        }
                    ),
                    400,
                )

            # before applying the changes
            # make sure if the dataset values do not conflict
            # with the values (e.g. disease) of the
            # to be assigned project

            allowed_diseases = project.extra_cols["diseases"]
            dataset_disease = dataset.extra_cols["disease"]

            if dataset_disease not in allowed_diseases:
                err = (
                    "Cannot assign selection to the project "
                    f"{project.project_id}, because the disease "
                    f"{dataset_disease} is not allowed."
                    "please first update the selection to one "
                    f"of the following:{allowed_diseases}"
                )
                return make_response(
                    jsonify(
                        {
                            "message": err,
                        }
                    ),
                    400,
                )

            if not project.extra_cols["dataset_visibility_changeable"]:
                project_visibility = project.extra_cols[
                    "dataset_visibility_default"
                ]

                dataset_has_to_be_private = project_visibility == "private"

                if dataset_has_to_be_private != dataset.private:
                    err = (
                        "Cannot assign selection to the project"
                        f"because the project {project.project_id}"
                        f" does not allow {newValue}."
                        "please first update the selection to  "
                        f"{project_visibility}"
                    )
                    return make_response(
                        jsonify(
                            {
                                "message": err,
                            }
                        ),
                        400,
                    )

            dataset.project_id = project.id

    if selectedField == "visibility":

        project_data = (
            db.session.query(Project)
            .filter(Project.id == dataset.project_id)
            .with_entities(Project.project_id, Project.extra_cols)
            .one_or_none()
        )

        if project_data:
            if project_data[1]["dataset_visibility_changeable"]:
                if newValue == "private":
                    dataset.private = True
                else:
                    dataset.private = False

            # first the project has to be changed
            else:
                err = (
                    "Cannot change the visibility of the dataset"
                    f" for the project {project_data[0]}"
                )
                return make_response(
                    jsonify(
                        {
                            "message": err,
                        }
                    ),
                    400,
                )

        else:
            dataset_proj_ids = (
                db.session.query(Dataset)
                .filter(Dataset.project_id == 0)
                .with_entities(Dataset.project_id)
                .all()
            )
            if dataset_proj_ids is None:
                # raise an error
                return make_response(
                    jsonify({"message": "project not found"}), 404
                )

            if newValue == "private":
                dataset.private = True
            else:
                dataset.private = False

    return dataset


@api.expect(parser)
@ns.route("/", methods=(["POST"]))
class DatasetDataUpdate(Resource):
    """
    Dataset resource
    """

    @login_required
    def post(self, userid, groups):
        """
        Update dataset(s)
        """

        if "admin" not in groups:
            return make_response(
                jsonify({"message": "Only admin users can update a dataset"}),
                405,
            )

        # TODO
        # loop over files to update them

        request_data = request.get_json()

        # validate the request data
        fields = ["dbRowIds", "field", "value"]
        schema = get_obj_schema(
            {k: {"type": "string"} for k in fields}, required=fields
        )

        # note cannot change:
        # dataset_id -> file download would no longer work
        # shared_with -> can be changed by the user no admin access needed

        allowed_fields = [
            "project_id",
            "name",
            "submitter_name",
            "disease",
            "treatment",
            "molecularInfo",
            "dataType",
            "sampleType",
            "valueType",
            "platform",
            "genomeAssembly",
            "annotation",
            "samplesCount",
            "featuresCount",
            "featuresID",
            "healthyControllsIncluded",
            "additionalInfo",
            "contact",
            "tags",
            "visibility",
            "clinical_presigned_url",
            "policy_presigned_url",
        ]

        schema["properties"]["dbRowIds"] = {
            "type": "array",
            "items": {"type": "integer"},
        }

        schema["properties"]["field"]["enum"] = allowed_fields

        selectedField = request_data["field"]

        # in config.py missing is a mapping
        # of columnName to value type (e.g. string or integer)
        if selectedField in ["samplesCount", "featuresCount"]:
            schema["properties"]["value"]["pattern"] = r"^\d+$"

        if selectedField == "visibility":
            schema["properties"]["value"]["enum"] = [
                "private",
                "visible to all",
            ]

        if selectedField == "healthyControllsIncluded":
            schema["properties"]["value"]["enum"] = [
                "True",
                "False",
            ]

        validate_schema(request_data, schema)

        selectedDatasets = request_data["dbRowIds"]
        newValue = request_data["value"]

        datasets = (
            db.session.query(Dataset)
            .with_for_update()  # locks the rows
            .filter(Dataset.id.in_(selectedDatasets))
            .all()
        )

        if not datasets:
            return make_response(
                jsonify({"message": "dataset not found"}), 404
            )

        # TODO
        # should be in config.py
        extra_cols = [
            "disease",
            "treatment",
            "molecularInfo",
            "dataType",
            "sampleType",
            "valueType",
            "platform",
            "genomeAssembly",
            "annotation",
            "samplesCount",
            "featuresCount",
            "featuresID",
            "healthyControllsIncluded",
            "additionalInfo",
            "contact",
            "tags",
            "clinical_presigned_url",
            "policy_presigned_url",
        ]

        # TODO
        # only update the value if the new value is actually different

        for dataset in datasets:
            if selectedField in extra_cols:
                dataset = update_dataset_data_in_extra_cols(
                    newValue, selectedField, dataset
                )
            else:
                dataset = update_dataset_data_in_normal_cols(
                    newValue, selectedField, dataset
                )

            # TODO
            # workaround till the
            # errors are handled correctly in
            # update_dataset_data_in_extra_cols
            try:
                if dataset.status_code != 200:
                    return dataset
            except Exception:
                pass

            if selectedField != "project_id":
                setattr(dataset, selectedField, newValue)
        db_commit()

        return make_response(jsonify({"message": "dataset updated"}), 200)


# Dataset api resources
ns.add_resource(
    DatasetsViewCols,
    "/viewcols",
    endpoint="dataset_view_cols",
)

ns.add_resource(
    DatasetsAdminViewCols,
    "/adminviewcols",
    endpoint="dataset_admin_view_cols",
)

ns.add_resource(
    DatasetsSubmissionCols,
    "/submissioncols",
    endpoint="dataset_submission_cols",
)


ns.add_resource(DatasetData, "/", endpoint="datasets")

ns.add_resource(DatasetSubmission, "/create", endpoint="create_dataset")

ns.add_resource(
    DatasetView, "/all", endpoint="datasets_data_by_keycloak_group"
)
ns.add_resource(
    DatasetsList, "/list", endpoint="datasets_list_by_keycloak_group"
)

ns.add_resource(
    DatasetDataAdminView, "/admin/view", endpoint="dataset_data_all"
)
ns.add_resource(
    DatasetDataUpdate, "/admin/update", endpoint="dataset_data_update"
)

ns.add_resource(
    DatasetExtraFilesUploadFinished,
    "/extrafile/uploadfinish",
    endpoint="dataset_extra_file_upload_finish",
)

ns.add_resource(
    DatasetExtraFilesDownload,
    "/extrafile/download",
    endpoint="dataset_extra_file_download",
)
