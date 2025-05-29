# might be interesting for downloading analysis results

# from time import time, localtime
# from io import BytesIO
# import zipfile

# from flask import jsonify, make_response, send_file

# from server.run import app
# from server.utils import ceph
# from server.utils.schema import get_arr_schema
# from server.utils.validators import validate_schema, file_exists

# def zip_files(files):
#     """
#     based on the accepted answer on SO
#     https://stackoverflow.com/questions/27337013/how-to-send-zip-files-in-the-python-flask-framework
#     """

#     mem_zip = None

#     try:
#         mem_zip = BytesIO()
#         with zipfile.ZipFile(mem_zip, "w") as zf:
#             for fn, file_obj in files:
#                 data = zipfile.ZipInfo(
#                     filename=fn, date_time=localtime(time())[:6]
#                 )
#                 data.compress_type = zipfile.ZIP_DEFLATED
#                 zf.writestr(data, file_obj)
#         # seek back to the beginning of the file
#         mem_zip.seek(0)
#     except Exception as e:
#         # raise
#         print("EXCEPTION")
#         print(e)

#     return mem_zip


# def file_downloader(rows, group):
#     res = {}
#     res["message"] = ""

#     data = []
#     failed_downloads = []

#     # check schema
#     fields_to_types = app.config["FILE_DL_FIELDS_TYPES"]

#     props = {k: {"type": v} for k, v in fields_to_types.items()}
#     schema = get_arr_schema(
#         array_of="objects", props=props,
# 	  required=list(fields_to_types.keys())
#     )

#     # TODO
#     # Write a tests
#     validate_schema(rows, schema)

#     # 1. download files
#     for row in rows:

#         dataset_id, owner, fname, version = file_exists(row, group)

#         # TODO
#         # check if file exists on ceph

#         bytes_obj = ceph.download_file(
#             app.config, dataset_id, owner, fname, version
#         )

#         if bytes_obj is None:
#             failed_downloads.append(fname)

#         # TODO
#         # create a folder per data_owner (cnag / 3tr)
#         # and a subfolder per dataset name (test / test2)

#         file_id = f"{dataset_id}_{owner}_v{str(version)}_{fname}"

#         data.append((file_id, bytes_obj))

#     if len(failed_downloads) > 0:
#         # raise
#         return make_response(
#             jsonify(
#                 {
#                     "message": "file(s) download failed",
#                     "failed_files": failed_downloads,
#                 }
#             ),
#             404,
#         )

#     # 2. zip files and send file
#     mem_zip = zip_files(data)
#     if mem_zip is None:
#         return make_response(
# 		jsonify({"message": "zipping files failed"}), 404)

#     return send_file(mem_zip, mimetype="application/zip")
