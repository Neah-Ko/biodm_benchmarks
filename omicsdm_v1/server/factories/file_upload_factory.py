#!/usr/bin/env python

# might be interesting if we want allow uploading of analysis scripts

# import json
# from time import time
# from pathlib import Path
# from tempfile import NamedTemporaryFile

# from flask import jsonify, make_response
# from werkzeug.formparser import parse_form_data
# from werkzeug.exceptions import BadRequestKeyError, RequestEntityTooLarge

# from server.run import app, db
# from server.model import File, Dataset, Groups

# from server.utils.table_methods import db_add
# from server.utils import ceph
# from server.utils.schema import get_arr_schema
# from server.utils.validators import validate_schema

# from server.utils.error_handler import (
#     BadFile,
#     DataNotFound,
#     ImplementationError,
#     PayloadTooLarge,
# )

# # TODO
# # look into the following plugin
# # https://github.com/jugmac00/flask-reuploaded

# # Maybe it helps to limit the size
# of the uploaded file

# # TODO
# # Check why this config MAX_CONTENT_LENGTH
# # is not working

# # maybe that is inspiring:
# # https://github.com/pallets/flask/issues/2086

# # Especially that !
# # https://gitlab.nsd.no/ire/python-webserver-file-submission-poc/
# blob/master/flask_app.py


# def custom_stream_factory(
#     total_content_length, filename, content_type, content_length=None
# ):
#     """
#     custom stream factory for werkzeug.formparser.parse_form_data
#         - tests for allowed filetypes
#         - returns a tmpfile with the prefix 3tr-flask
#     """

#     # based on:
#     # https://medium.com/tictail/python-streaming-
# 	request-data-files-streaming
# 	-to-a-subprocess-504769c7065f
#     # https://gist.github.com/tgwizard/95b82c98e17e72a4c3c0d75dda19eef4

#     # large file uploads eating up memory
#     # https://gitlab.nsd.no/ire/python-webserver-file-submission-poc/blob/
# 	master/flask_app.py
#     # https://github.com/pallets/flask/issues/2086

#     print(
#         "Start writing to tempfile: "
#         f"total_content_length={total_content_length} "
#         f"content_type={content_type} "
#         f"filename={filename} "
#         f"content_length={content_length}"
#     )

#     # TODO
#     # put the file validators into validators.py

#     # TODO
#     # test upload multiple filesizes (100mb, 1GB, etc..)
#     # set a limit for the maximum uploadable file size

#     allowed_filetypes = app.config["ALLOWED_FILE_EXTENSIONS"]

#     # TODO
#     # test if error missing file extension is raised correctly
#     try:
#         file_extension = filename.rsplit(".")[1]
#     except IndexError:
#         raise BadFile(filename, "missing file extension")

#     if file_extension not in allowed_filetypes:
#         print(allowed_filetypes)
#         raise BadFile(filename, "forbidden file extension")

#     tmpfile = NamedTemporaryFile("wb+", prefix="3tr-flask_")

#     print("tmpfile => " + str(tmpfile.name))
#     return tmpfile


# def parse_fileupload_form(
#     environ, form_key="metaData", stream_factory=custom_stream_factory
# ):

#     # TODO
#     # might be interesting to keep track of the RAM usage?
#     """
#     wrapper around werkzeug.formparser.parse_form_data
#         - enables to track time to read a file upload request
#         - uses a custom stream factory
#           which generates a tmpfile per uploaded file
#         - returns MultiDict for the uploaded files (file_data)
#                             and the files metadata (form_data)
#     """

#     print("Starting to read request")
#     start = time()

#     try:
#         _, form_data, file_data = parse_form_data(
#             environ,
#             stream_factory=stream_factory,
#             max_content_length=app.config["MAX_CONTENT_LENGTH"],
#         )
#     except RequestEntityTooLarge:
#         raise PayloadTooLarge()

#     end = time()

#     # TODO
#     # Test if the DataNotFound Error is raised correctly
#     # make sure neither file_data nor form_data is an empty list
#     if not all([bool(file_data), bool(form_data)]):
#         raise DataNotFound("files or metadata")

#     print("Finished reading request: time=%s" % (end - start))

#     # is json loads secure enough?
#     # opinion from SO: YES
#     # https://stackoverflow.com/questions/38813298/is-json-loads-vulnerable-
# 	to-arbitrary-code-execution
#     try:
#         form_data = json.loads(form_data[form_key])
#     except BadRequestKeyError as e:
#         raise ImplementationError(e, __file__)

#     return file_data, form_data


# def file_uploader(userid, group_id, group_name, request):

#     # TODO
#     # better raise an error
#     result = make_response(jsonify({"message": "something went wrong"}), 500)

#     file_data = None
#     form_data = None

#     file_data, form_data = parse_fileupload_form(
#         request.environ, form_key="metaData"
#     )

#     props = {k: {"type": "string"} for k in app.config["FILE_FIELDS"]}
#     schema = get_arr_schema(
#         array_of="objects",
#         props=props,
#         field_enums=app.config["FILE_FIELDS_ENUMS"],
#         required=["DatasetID"],
#     )
#     schema["items"]["properties"]["File"] =
# 	get_arr_schema(array_of="strings")

#     # TODO
#     # Write a tests
#     # trying to upload two files with the same file name -> should fail
#     # trying to upload a file with enum not in FILE_FIELS_ENUMS
# 	-> should fail

#     validate_schema(form_data, schema)

#     # store file in ceph

#     upload_error = []
#     for file in file_data.getlist("file"):
#         file_name = file.filename

#         if " " in file_name:
#             # TODO do this check also in the frontend
#             # raise
#             return make_response(
#                 jsonify(
# 		{"message": f"file {file_name} contains spaces"}), 405
#             )

#         if (
#             file_name.rsplit(".")[-1]
#             not in app.config["ALLOWED_FILE_EXTENSIONS"]
#         ):
#             raise BadFile(
#                 file, f"file {file_name} contains forbidden file extension"
#             )

#         file_path = file.stream.name
#         file_size = Path(file_path).stat().st_size
#         file_not_empty = bool(file_size)  # bool(0) == False

#         if file_not_empty is False:
#             raise BadFile(file, f"file {file_name} empty")
#             # TODO
#             # do not return immediately rather modify the React View
#             # so it shows which of the file uploads failed

#         # TODO
#         # test upload multiple filesizes (100mb, 1GB, etc..)
#         # test frontend / API individual
#         # set a limit for the maximum uploadable file size

#         meta_data = [d for d in form_data if file_name in d["File"]][0]

#         # map dataset_id (string) to dataset.id (integer)
#         # but make sure that the keycloak group is the dataset_owner
#         dataset = (
#             db.session.query(Dataset)
#             .join(Groups, Dataset.id == Groups.dataset_id)
#             .filter(Groups.group_id == group_id)
#             .filter(Dataset.dataset_id == meta_data["DatasetID"])
#             .with_entities(Dataset.id, Dataset.shared_with)
#             .one_or_none()
#         )
#         # TODO
#         # TESTING make sure that the dataset id is correct
#         if dataset is None:
#             return make_response(
#                 jsonify({"message": "dataset does not exist"}), 404
#             )

#         dataset_idx = dataset[0]  # index in the database
#         ds_shared_with = dataset[1]

#         # get current file_version and increment it if file already present
#         file_version = 0
#         query = (
#             db.session.query(File)
#             .filter(File.shared_with.contains([group_id]))
#             .filter(File.name == file_name)
#             .join(Dataset, File.dataset_id == Dataset.id)
#             .filter(Dataset.dataset_id == meta_data["DatasetID"])
#             .order_by(File.version.desc())
#             .with_entities(File.version)
#             .first()
#         )

#         if query is not None:
#             file_version = query[0]

#         file_version += 1

#         # TODO
#         # get from the metadata info if file is a single cell dataset

#         folder = meta_data["DatasetID"]
#         key = f"{group_name}_v{file_version}_{file_name}"
#         if file_name.endswith(".h5ad"):
#             folder = "3TR-cellxgene"
#             key = f"{meta_data['DatasetID']}_{key}"

#         key = f"{folder}/{key}"

#         try:
#             ceph.upload_file(app.config, file.stream.name, key)
#         except Exception:
#             upload_error.append(file_name)
#             print(upload_error)

#         # TODO
#         # checksum validation after data upload:
#         # https://fairplus.github.io/the-fair-cookbook/content/recipes/
# 		findability/checksum-validate.html
#         # https://stackoverflow.com/questions/24847602/how-to-create-a-
# 		checksum-of-a-file-in-python

#         # need an extra column in  the React view
#         # where the user could provide a checksum
#         # and then calculate the checksum with python to make sure that
#         # the user provided checksum and the calculated one match.

#         # store file metadata in the d

#         file = File(
#             dataset_id=dataset_idx,
#             name=file_name,
#             platform=meta_data.get("Platform", ""),
#             comment=meta_data.get("Comment", ""),
#             submitter_name=userid,
#             version=file_version,
#             enabled=True,
#             shared_with=ds_shared_with,
#         )

#         db_add(file)

#         result = make_response(
#             jsonify({"message": "File metadata inserted in database"}), 200
#         )

#     return result
