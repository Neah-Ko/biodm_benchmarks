#!/usr/bin/env python

import codecs

import hmac
import hashlib
import base64

from sqlalchemy import or_

from flask import request, make_response, jsonify
from flask_restx import Resource, Namespace
from flask_cors import cross_origin

from server.app import db, api, app
from server.model import File, Dataset, Group
from server.security import login_required
from server.factories.view_factory import data_view_builder

from server.model import Groups, Project, ProjectMapping

from server.utils.table_methods import db_add, db_commit
from server.utils.ceph import create_presigned_url
from server.utils.schema import get_arr_schema, get_obj_schema
from server.utils.validators import validate_schema

from sqlalchemy.orm.attributes import flag_modified

from server.utils.error_handler import (
    BadFile,
    EmptyQuery,
)

ns = Namespace(
    "files",
    description="files related operations",
    decorators=[cross_origin()],
)

parser = api.parser()
parser.add_argument(
    "Authorization", type=str, location="headers", required=True
)


@api.expect(parser)
@ns.route("/viewcols", methods=(["GET"]))
class FilesViewCols(Resource):
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
        return jsonify({"headers": app.config["FILES_VIEW_HEADERS"]}, 200)


@api.expect(parser)
@ns.route("/adminviewcols", methods=(["POST"]))
class FilesAdminViewCols(Resource):
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
        Get datasets view fields
        """
        return jsonify({"headers": app.config["FILES_VIEW_HEADERS"]}, 200)


@ns.route("/", methods=(["GET"]))
class RequestSigner(Resource):
    @login_required
    def get(self, userid, groups):
        """
        sign request
        https://github.com/TTLabs/EvaporateJS/blob/master/example/signing_example.py
        """

        # TODO
        # check how to do the request signing using
        # AWS signature version 4

        # TODO
        # validate to_sign_str
        # "3tr/test_id/test.csv_uploadedVersion_1.csv"

        # check if the owner is correct
        # check if the dataset_id belongs to the owner
        # make sure that it does not overwrite existing file

        # needs to be tested
        print("request.headers", request.headers)

        # ! only works for one keycloak group per user
        group_name = groups[0]
        group = Group.find_by_name(group_name)
        if group is None:
            return make_response(jsonify({"error": "invalid group"}), 400)

        to_sign_str = str(request.args.get("to_sign"))
        print("to_sign_str -> ", to_sign_str)

        # verify to_sign_str
        # (since startUpload creates the signed url it should be correct
        # however, we never can be sure if someone is trying to hack us
        # by intercepting the signed url and replace it with another one
        # therefore we need to verify the signed url)

        ceph_obj_key = to_sign_str.split()[-1].split("/")[1:]
        # correct bucket
        if ceph_obj_key[0] != app.config["BUCKET_NAME"]:
            return make_response(jsonify({"error": "invalid bucket"}), 400)

        # TODO
        # test missing
        if ceph_obj_key[1] != group_name:
            return make_response(jsonify({"error": "invalid data owner"}), 400)

        # map dataset_id (string) to dataset.id (integer)
        # but make sure that the keycloak group is the dataset_owner
        dataset = (
            db.session.query(Dataset)
            .join(Groups, Dataset.id == Groups.dataset_id)
            .filter(Groups.group_id == group.id)
            .filter(Dataset.dataset_id == ceph_obj_key[2])
            .with_entities(Dataset.id, Dataset.shared_with)
            .one_or_none()
        )

        if dataset is None:
            return make_response(jsonify({"error": "invalid dataset"}), 400)

        if ceph_obj_key[3] not in ["dataPolicy", "clinical"]:
            # make sure that the file not already exists

            # TODO
            # test what happens if you have file with _uploadedVersion_
            # in its name

            # TODO
            # make sure that _uploadedVersion_
            # is in the file name if not throw an error

            file_name, file_version = ceph_obj_key[3].split(
                "_uploadedVersion_"
            )
            file_version = file_version.split(".")[0]

            file_query = (
                db.session.query(File)
                .join(Dataset, File.dataset_id == Dataset.id)
                .join(Groups, Groups.dataset_id == Dataset.id)
                .filter(Groups.group_id == group.id)
                .filter(File.name == file_name)
                .filter(File.version == file_version)
                .filter(File.upload_finished.is_(True))
                .filter(Dataset.dataset_id == ceph_obj_key[2])
                .one_or_none()
            )
            if file_query is not None and file_query.upload_finished:
                return make_response(
                    jsonify({"error": "file already exists"}), 400
                )

        secret = codecs.encode(app.config["SECRET_KEY"])
        signature = base64.b64encode(
            hmac.new(
                secret, to_sign_str.encode("utf-8"), hashlib.sha1
            ).digest()
        )

        result = make_response(signature, 200)

        return result


@ns.route("/finishupload", methods=(["POST"]))
class FileFinishUpload(Resource):
    @login_required
    def post(self, userid, groups):

        group_name = groups[0]
        group = Group.find_by_name(group_name)

        data = request.get_json()

        if group is None:
            # group is only none if the user's keycloak group
            # has never interacted with the server before
            # => blocks possible malicious actions
            return make_response(
                jsonify({"message": "user not authorized"}), 405
            )

        # TODO
        # validation has to be reimplemented

        aws_key = data["aws_key"]

        # TODO
        # this might fail if the file has
        # "_uploadedVersion_" in the filename

        # rewrite CEPH structure as follows:
        # <owner>/<dataset_id>/<filename>/<version>/<filename_uploadedVersion_#.fileExtension>

        # split aws_key into kc_group,dataset_id, file_name & version
        kc_group, dataset_id, file_name = aws_key.split("/")

        # make sure that the group is the same as the user's group name
        if kc_group != group_name:
            return make_response(
                jsonify({"message": "group name does not match"}),
                405,
            )

        # TODO
        # add tests which makes sure that it is possible to uplaod a file
        # with multiple "_uploadedVersion_" in the filename
        # e.g.SLE_transcriptome_counts.tsv_uploadedVersion_1.tsv_uploadedVersion_1.tsv

        file_name, version = file_name.rsplit("_uploadedVersion_", 1)
        version = version.split(".")[0]

        # map dataset_id (string) to dataset.id (int) [=row in sql table]
        # but make sure that the keycloak group is the dataset_owner
        dataset = (
            db.session.query(Dataset)
            .join(Groups, Dataset.id == Groups.dataset_id)
            .filter(Groups.group_id == group.id)
            .filter(Dataset.dataset_id == dataset_id)
            .with_entities(Dataset.id)
            .one_or_none()
        )
        # TODO
        # TESTING make sure that the dataset id is correct
        if dataset is None:
            return make_response(
                jsonify({"message": "dataset does not exist"}), 404
            )

        file_query = (
            db.session.query(File)
            .filter(File.dataset_id == dataset.id)
            .filter(File.name == file_name)
            .filter(File.version == version)
            .order_by(File.submission_date.desc())
            .first()
        )

        if file_query is None:
            return make_response(
                jsonify({"message": "file does not exist"}), 404
            )

        file_query.upload_finished = True
        db_commit()

        # TODO
        # Test what happens if the file Platform or Comments is changed
        # from one file upload to another
        # e.g. 1. Upload: testfile1.csv / Platform: testPlatform
        #      2. Upload: testfile2.csv / Platform: testPlatform2

        return make_response(jsonify({"message": "File upload finished"}), 200)


@ns.route("/download", methods=(["POST"]))
class FileDownload(Resource):
    @login_required
    def post(self, userid, groups):

        group_name = groups[0]
        group = Group.find_by_name(group_name)

        data = request.get_json()

        if group is None:
            # cannot be none because the file id can only be known when
            # the file data have been queried from the database
            return make_response(
                jsonify({"message": "user not authorized"}), 405
            )

        schema = get_obj_schema(
            {"file_ids": {"type": "array"}}, required=["file_ids"]
        )
        schema["file_ids"] = get_arr_schema(
            array_of="integers",
        )
        validate_schema(data, schema)

        file_id_to_urls = {}
        for file_id in data["file_ids"]:

            # TODO
            # add an extra condition to check if the file
            # belongs to a project in which the file download is not allowed

            or_conditions = [
                Groups.group_id == group.id,
                File.shared_with.contains([group.id]),
                Dataset.private.is_(False),
            ]

            # TODO
            # Below is still WIP

            file_query = (
                db.session.query(File, Project)
                .filter(File.id == file_id)
                .filter(File.enabled.is_(True))
                .join(
                    ProjectMapping,
                    File.dataset_id == ProjectMapping.dataset_id,
                )
                .join(Project, ProjectMapping.project_id == Project.id)
                .join(Dataset, File.dataset_id == Dataset.id)
                .join(Groups, Dataset.id == Groups.dataset_id)
                .join(Group, Groups.group_id == Group.id)
                .filter(or_(*or_conditions))
                .with_entities(
                    Group.kc_groupname,
                    Dataset.dataset_id,
                    File.name,
                    File.version,
                    Project.extra_cols,
                )
                .one_or_none()
            )

            if file_query is None:
                return make_response(
                    jsonify({"message": "file not found"}), 404
                )

            url = "download forbidden"

            file_owner_group = file_query[0]
            file_dl_allowed = file_query[4]["file_dl_allowed"]

            if file_dl_allowed or file_owner_group == group_name:
                url = create_presigned_url(
                    app.config, "get_object", *file_query
                )

            file_id_to_urls[file_id] = url

        result = make_response(
            jsonify(
                {
                    "message": "returned presigned urls",
                    "presignedUrls": file_id_to_urls,
                }
            ),
            200,
        )
        return result


@ns.route("/disable", methods=(["POST"]))
class FileDisable(Resource):
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

        data = request.get_json()

        schema = get_obj_schema(
            {"fileIds": {"type": "array"}}, required=["fileIds"]
        )
        schema["fileIds"] = get_arr_schema(
            array_of="integers",
        )
        validate_schema(data, schema)

        file_ids = data["fileIds"]

        query = (
            db.session.query(File)
            .filter(Groups.group_id == group.id)
            .filter(File.id.in_(file_ids))
            .filter(File.enabled.is_(True))
            .join(Dataset, File.dataset_id == Dataset.id)
            .join(Groups, Dataset.id == Groups.dataset_id)
            .join(Group, Groups.group_id == Group.id)
        )

        files = query.all()
        if len(files) != len(file_ids):
            raise EmptyQuery(
                query, "at least one of the requested files was not found"
            )

        for file in files:
            file.enabled = False

        db_commit()
        res = make_response(
            jsonify({"message": "file(s) status changed"}),
            200,
        )
        return res


class FileDataView(Resource):
    @login_required
    def post(self, userid, groups):
        group_name = groups[0]

        # !FIMXE
        # only works when a user has only one group
        group_name = groups[0]
        res = data_view_builder(group_name, File, "FILES", request, ns)
        return res


class FileDataAdminView(Resource):
    @login_required
    def post(self, userid, groups):
        """
        Get all the file data
        """
        # !FIMXE
        # only works when a user has only one group
        group_name = groups[0]
        if group_name != "admin":
            return make_response(
                jsonify({"message": "Only admin users can view files"}),
                404,
            )

        res = data_view_builder(group_name, File, "FILES", request, ns)

        # # TODO
        # # workaround till the
        # # errors are handled correctly in
        # # admin_view_builder
        # try:
        #     if files.status_code != 200:
        #         return files
        # except Exception:
        #     pass

        # # # TODO
        # # # schema validation is missing

        # # this should be in config.py
        # col_mapping = {
        #     "id": "id",
        #     "dataset_id": "dataset_id",
        #     "submitter_name": "submitter_name",
        #     "version": "version",
        #     "upload_finished": "upload_finished",
        #     "shared_with": "shared_with",
        #     "enabled": "enabled",
        #     "name": "name",
        # }

        # # TODO
        # # submission date is missing

        # # # TODO
        # # # put below into config.py
        # extra_cols = [
        #     "Comment",
        # ]

        # for file in files:
        #     data = {k: getattr(file, v) for k, v in col_mapping.items()}

        #     # get the project id
        #     db_query = (
        #         db.session.query(Project)
        #         .filter(Project.id == data["dataset_id"])
        #         .with_entities(Project.project_id)
        #         .all()
        #     )

        #     try:
        #         data["project_id"] = db_query[0][0]
        #     except IndexError as err:
        #         print(err)
        #         print(db_query)
        #         data["project_id"] = ""

        #     # get the owners keycloak group from the database
        #     # db_query = (
        #     #     db.session.query(Group)
        #     #     .filter(Group.id.in_(data["owners"]))
        #     #     .with_entities(Group.kc_groupname)
        #     #     .all()
        #     # )

        #     # owners = [group[0] for group in db_query]
        #     # data["owners"] = ",".join(owners)

        #     for col in extra_cols:
        #         try:
        #             data[col] = str(getattr(file, "extra_cols")[col])
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
class FileDataUpdate(Resource):
    """
    Dataset resource
    """

    # TODO
    # allow the update of a extra cols field
    # from the frontend
    # copy all values from the old name to the new name
    # e.g. Comment -> comment

    @login_required
    def post(self, userid, groups):
        """
        Update file(s)
        """

        if "admin" not in groups:
            return make_response(
                jsonify({"message": "Only admin users can update a file"}),
                405,
            )

        request_data = request.get_json()

        selectedFiles = request_data["dbRowIds"]
        selectedField = request_data["field"]
        newValue = request_data["value"]

        # validate the request data
        fields = ["dbRowIds", "field", "value"]
        schema = get_obj_schema(
            {k: {"type": "string"} for k in fields}, required=fields
        )

        # cannot update dataset id -> file download will stop working
        allowed_fields = ["comment"]

        schema["properties"]["dbRowIds"] = {
            "type": "array",
            "items": {"type": "integer"},
        }

        schema["properties"]["field"]["enum"] = allowed_fields

        validate_schema(request_data, schema)

        # FIXME
        # somehow the fields in the table's extra cols
        # are inconsistent they should be all
        # lowercase but they are not
        if selectedField == "comment":
            selectedField = "Comment"

        # update one field of the project
        query = (
            db.session.query(File)
            .with_for_update()  # locks the row
            .filter(File.id.in_(selectedFiles))
            .one_or_none()
        )
        if query is None:
            return make_response(jsonify({"message": "file not found"}), 404)

        # TODO
        # only update the value if the new value is actually different
        try:
            query.extra_cols[selectedField] = newValue
        except TypeError as err:
            err = str(err)
            if err != "'NoneType' object does not support item assignment":
                raise
            else:
                query.extra_cols = {}
                query.extra_cols[selectedField] = newValue

        flag_modified(query, "extra_cols")

        setattr(query, selectedField, newValue)
        db_commit()

        return make_response(jsonify({"message": "File(s) updated"}), 200)


@api.expect(parser)
@ns.route("/submissioncols", methods=(["GET"]))
class FileSubmissionCols(Resource):
    @login_required
    @api.doc(description="Returns...")
    @api.response(500, "Server error")
    @api.response(200, "Success")
    def get(self, userid, groups):
        """
        Get file submission fields
        """
        return jsonify({"message": app.config["SUBMIT_FILES_HEADERS"]}, 200)


@ns.route("/", methods=(["POST"]))
class FileDataStartUpload(Resource):
    @login_required
    def post(self, userid, groups):

        group_name = groups[0]
        group = Group.find_by_name(group_name)

        if group is None:
            # group is only none if the user's keycloak group
            # has never interacted with the server before
            # => blocks possible malicious actions
            return make_response(
                jsonify({"message": "user not authorized"}), 404
            )

        data = request.get_json()

        props = {
            k: {"type": "string", "minLength": 1}
            for k in app.config["FILE_FIELDS"]
        }
        props["Comment"] = {"type": "string"}

        schema = get_obj_schema(
            props,
            required=["projectId", "DatasetID", "fileName", "Comment"],
        )

        # TODO
        # the schema should be more explicit
        # => e.g. projectID or datasetID or FileName
        # cannot be an empty string

        schema["properties"]["file"] = {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        }

        # TODO
        # Test what happens if the file Comments is changed
        # from one file upload to another
        # e.g. 1. Upload: testfile1.csv / Comment: test
        #      2. Upload: testfile2.csv / Comment: test2

        # TODO
        # Write a tests
        # trying to upload two files with the same file name
        # -> should fail

        # trying to upload a file with enum not in FILE_FIELS_ENUMS
        # -> should fail

        validate_schema(data, schema)

        # TODO
        # at the moment the meta data insert is per file
        # better would be per dataset (row)
        file_name = data["fileName"]

        # TODO
        # check if file is empty on frontend side

        # TODO
        # add the spaces check to the schema validation

        if " " in file_name:
            # TODO do this check also in the frontend
            # raise
            return make_response(
                jsonify({"message": f"file {file_name} contains spaces"}),
                405,
            )

        # TODO
        # add test to make sure that it is possible to upload a file with
        # multiple dots in the file_name
        # e.g. CS_Transcriptome_counts_SLE.tsv_uploadedVersion_1.tsv

        # TODO
        # add the file extension check to the
        # schema validation

        file_extension = file_name.rsplit(".", 1)[1]
        if file_extension not in app.config["ALLOWED_FILE_EXTENSIONS"]:
            raise BadFile(
                data, f"file {file_name} contains forbidden file extension"
            )

        # map dataset_id (string) to dataset.id (integer)
        # but make sure that the keycloak group is the dataset_owner
        dataset = (
            db.session.query(Dataset)
            .join(Groups, Dataset.id == Groups.dataset_id)
            .join(Project, Dataset.project_id == Project.id)
            .filter(Groups.group_id == group.id)
            .filter(Project.project_id == data["projectId"])
            .filter(Dataset.dataset_id == data["DatasetID"])
            .with_entities(Dataset.id, Dataset.shared_with)
            .one_or_none()
        )
        # TODO
        # TESTING make sure that the dataset id is correct
        if dataset is None:
            return make_response(
                jsonify({"message": "dataset does not exist"}), 404
            )

        dataset_id = dataset[0]
        ds_shared_with = dataset[1]

        # get current file_version and increment it if file already present
        # make sure that the file upload is finished
        file_version = 0
        query = (
            db.session.query(File)
            .filter(File.dataset_id == dataset_id)
            .filter(File.name == file_name)
            .filter(File.upload_finished.is_(True))
            .order_by(File.version.desc())
            .with_entities(File.version)
            .first()
        )

        if query is not None:
            file_version = query[0]
        file_version += 1

        # TODO
        # checksum validation after data upload:
        # https://fairplus.github.io/the-fair-cookbook/content/recipes/findability/checksum-validate.html
        # https://stackoverflow.com/questions/24847602/how-to-create-a-checksum-of-a-file-in-python

        # need an extra column in  the React view
        # where the user could provide a checksum
        # and then calculate the checksum with python to make sure that
        # the user provided checksum and the calculated one match.

        # store file metadata in the database

        # TODO
        # put below into config.py
        file_extra_cols = ["Comment"]

        extra_cols = {}
        for key in data:
            if key in file_extra_cols:
                extra_cols[key] = data[key].strip()

        meta_data = File(
            dataset_id=dataset_id,
            name=file_name,
            submitter_name=userid,
            version=file_version,
            enabled=True,
            upload_finished=False,
            shared_with=ds_shared_with,
            extra_cols=extra_cols,
        )

        db_add(meta_data)

        # dataset_id as string (e.g. "test_id")
        ds = data["DatasetID"]
        ext = file_extension
        aws_key = "/".join(
            [
                group_name,
                ds,
                f"{file_name}_uploadedVersion_{file_version}.{ext}",
            ]
        )

        result = make_response(
            jsonify(
                {
                    "message": "File metadata inserted in database",
                    "awsKey": aws_key,
                }
            ),
            200,
        )

        return result


# File resources
ns.add_resource(FilesViewCols, "/viewcols", endpoint="files_view_cols")

ns.add_resource(
    FilesAdminViewCols, "/viewcols", endpoint="files_vadmin_view_cols"
)

ns.add_resource(
    FileFinishUpload, "/finishupload", endpoint="file_finish_upload"
)
ns.add_resource(FileDownload, "/donwnload", endpoint="file_download")
ns.add_resource(FileDisable, "/disable", endpoint="file_disable")
ns.add_resource(RequestSigner, "/", endpoint="request_signer")
ns.add_resource(FileDataView, "/all", endpoint="file_data_by_keycloak_group")
ns.add_resource(FileDataAdminView, "/admin/view", endpoint="file_data_all")
ns.add_resource(FileDataUpdate, "/admin/update", endpoint="file_data_update")
ns.add_resource(
    FileDataStartUpload, "/startupload", endpoint="file_data_start_upload"
)
ns.add_resource(
    FileSubmissionCols, "/submissioncols", endpoint="file_submission_cols"
)
