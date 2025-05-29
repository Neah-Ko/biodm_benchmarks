# #!/usr/bin/env python
# from flask import jsonify, make_response

# from server.app import db, app
# from server.model import File, Dataset, Project, ProjectMapping
# from server.utils.validators import validate_schema
# from server.utils.schema import get_obj_schema


# class TableSpecificFiltering:
#     def __init__(self, filter_cols, db_query):
#         self.db_query = db_query
#         self.filter_cols = filter_cols

#     def modify_db_query(self, table_name):
#         """
#         helper function to implement a switch case functionality
#         """
#         # call one of the table specific functions
#         db_query = getattr(self, f"table_{table_name}")()
#         return db_query

#     def table_PROJECTS(self):
#         """
#         modify the query for the projects table
#         """
#         for col_to_id in self.filter_cols:
#             col, val = col_to_id.values()
#             if col == "project_id":
#                 db_query = self.db_query.filter(Project.project_id == val)
#             else:
#                 return None
#         return db_query

#     def table_DATASETS(self):
#         """
#         modify the query for the datasets table
#         """
#         for col_to_id in self.filter_cols:
#             col, val = col_to_id.values()

#             if col == "id":
#                 db_query = self.db_query.filter(Dataset.id == val)

#             elif col == "project_id":
#                 db_query = (
#                     self.db_query.join(
#                         ProjectMapping, Dataset.id ==
# ProjectMapping.dataset_id
#                     )
#                     .join(Project, ProjectMapping.project_id == Project.id)
#                     .filter(Project.project_id == val)
#                 )
#             else:
#                 return None

#         return db_query

#     def table_FILES(self):
#         """
#         modify the query for the files table
#         """
#         for col_to_id in self.filter_cols:
#             col, val = col_to_id.values()

#             if col == "file_id":
#                 db_query = self.db_query.filter(File.id == val)
#             else:
#                 return None
#         return db_query


# def admin_view_builder(groups, request, table, table_name, ns):
#     # make sure that the logged in user is in the admin group
#     if "admin" not in groups:
#         # TODO
#         # raise an error if the user is not in the admin group
#         msg = f"Only admin users can view {table_name.lower()}"
#         return (
#             make_response(
#                 jsonify({"message": msg}),
#                 405,
#             ),
#             None,
#         )

#     # TODO
#     # try to merge it with react_view_builder
#     #

#     request_data = request.get_json()

#     # TODO
#     # schema validation is missing

#     # initialize response result
#     result = {
#         "items": [],
#         "_meta": {
#             "total_items": 0,
#             "total_pages": 1,
#             "page_size": request_data.get("pageSize", 100),
#             "page": request_data.get("page", 1),
#         },
#     }

#     fields_to_types = app.config["VIEW_FIELDS_TYPES"]
#     props = {k: {"type": fields_to_types[k]} for k in fields_to_types}
#     schema = get_obj_schema(props)

#     filter_cols = request_data.get("filtered", [])

#     if not filter_cols:
#         validate_schema(request_data, schema)
#         ns.logger.info("schema validated")

#     db_query = db.session.query(table)

#     if filter_cols:
#         db_query = TableSpecificFiltering(
#             filter_cols, db_query
#         ).modify_db_query(table_name)

#     if db_query is None:
#         err_msg = "the selected field cannot be used for filtering"
#         # raise field not allowed
#         return (
#             make_response(
#                 jsonify({"message": err_msg}),
#                 405,
#             ),
#             None,
#         )

#     rows = db_query.all()
#     result["_meta"]["total_items"] = len(rows)

#     return rows, result
