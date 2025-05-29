from server.app import app, db
from server.model import Group, Groups, Project
import json
from server.utils.table_methods import (
    db_add,
    db_update_groups,
    db_update_project,
)
from server.utils.validators import (
    validate_ids,
    validate_schema,
    # validate_using_pydantic,
)
from server.utils.error_handler import (
    DataAlreadyPresent,
    EmptyQuery,
    WrongSchema,
)

from server.utils.schema import get_obj_schema2

from server.utils.error_handler import InvalidGroup

from server.utils.permissions import get_all_kc_groups, is_valid_kc_group

# from server.utils.pydanticModels import DatasetSubmission


def db_id_still_available(group, table, table_name, column_name, id):
    """
    Datasets:
    Make sure that there is within a keycloak group not already
    one Dataset having the same (opal) Dataset idS
    raise => Dataset id is already used

    Projects:
    Make sure that each project id is unique
    raise => Project id is already used
    """

    if table_name == "DATASET":
        ds = (
            db.session.query(table)
            .join(Groups, table.id == Groups.dataset_id)
            .filter(Groups.group_id == group.id)
            .filter(getattr(table, column_name) == id)
            .with_entities(table.dataset_id)
            .one_or_none()
        )
        if ds is not None:
            raise DataAlreadyPresent(ds[0])

    else:
        projects = (
            db.session.query(table)
            .filter(getattr(table, column_name) == id)
            .one_or_none()
        )
        if projects is not None:
            raise DataAlreadyPresent(column_name)


def create_project(row, new_id, table, table_name, token, add_to_db):

    # put it in config.py
    extra_cols_to_types = {
        "description": str,
        "diseases": list,
        "dataset_visibility_default": str,
        "dataset_visibility_changeable": bool,
        "file_dl_allowed": bool,
        "logo_url": str,
    }

    row_new = {"extra_cols": {}}
    mapping = app.config[f"{table_name}_COL_MAPPING"]

    # put it in config.py
    mapping = {
        "id": "project_id",
        "name": "name",
        "owners": "owners",
        "description": "description",
        "datasetVisibilityDefault": "dataset_visibility_default",
        "datasetVisibilityChangeable": "dataset_visibility_changeable",
        "fileDlAllowed": "file_dl_allowed",
        "diseases": "diseases",
        "logoUrl": "logo_url",
    }

    for col, value in row.items():
        mapped_col = mapping[col]

        if mapped_col in extra_cols_to_types:
            row_new["extra_cols"][mapped_col] = value
        else:
            row_new[mapped_col] = value

    # insert defaults for the missing extra_cols
    # * only needed for a new field in extra_cols
    # needs to be tested with a dummy db
    for col, value_type in extra_cols_to_types.items():
        if col not in row_new["extra_cols"]:

            row_new["extra_cols"][col] = ""
            if value_type == bool:
                row_new["extra_cols"][col] = True

            if col == "dataset_visibility_default":
                row_new["extra_cols"][col] = "private"

    # get the owner groups
    owners = row_new["owners"].split(",")

    proj_owners = owners
    if len(owners) == 1 and owners[0] == "ALL":
        proj_owners = get_all_kc_groups(token)

    owner_ids = []
    for group_name in proj_owners:
        group_query = (
            db.session.query(Group)
            .filter_by(kc_groupname=group_name)
            .one_or_none()
        )
        if group_query is None:
            if is_valid_kc_group(group_name, token) is False:
                raise (InvalidGroup(group_name))
            else:
                db_add(Group(kc_groupname=group_name))
                group_query = (
                    db.session.query(Group)
                    .filter_by(kc_groupname=group_name)
                    .one_or_none()
                )
        owner_ids.append(group_query.id)

    row_new["owners"] = owner_ids
    row_new["project_id"] = new_id
    row_obj = table(**row_new)

    if add_to_db:
        row_obj.save_to_db()

    return True


def create_project_returning(row, new_id, table, table_name, token, add_to_db):

    # put it in config.py
    extra_cols_to_types = {
        "description": str,
        "diseases": list,
        "dataset_visibility_default": str,
        "dataset_visibility_changeable": bool,
        "file_dl_allowed": bool,
        "logo_url": str,
    }

    row_new = {"extra_cols": {}}
    mapping = app.config[f"{table_name}_COL_MAPPING"]

    # put it in config.py
    mapping = {
        "id": "project_id",
        "name": "name",
        "owners": "owners",
        "description": "description",
        "datasetVisibilityDefault": "dataset_visibility_default",
        "datasetVisibilityChangeable": "dataset_visibility_changeable",
        "fileDlAllowed": "file_dl_allowed",
        "diseases": "diseases",
        "logoUrl": "logo_url",
    }

    for col, value in row.items():
        mapped_col = mapping[col]

        if mapped_col in extra_cols_to_types:
            row_new["extra_cols"][mapped_col] = value
        else:
            row_new[mapped_col] = value

    # insert defaults for the missing extra_cols
    # * only needed for a new field in extra_cols
    # needs to be tested with a dummy db
    for col, value_type in extra_cols_to_types.items():
        if col not in row_new["extra_cols"]:

            row_new["extra_cols"][col] = ""
            if value_type == bool:
                row_new["extra_cols"][col] = True

            if col == "dataset_visibility_default":
                row_new["extra_cols"][col] = "private"

    # get the owner groups
    owners = row_new["owners"].split(",")

    proj_owners = owners
    if len(owners) == 1 and owners[0] == "ALL":
        proj_owners = get_all_kc_groups(token)

    owner_ids = []
    for group_name in proj_owners:
        group_query = (
            db.session.query(Group)
            .filter_by(kc_groupname=group_name)
            .one_or_none()
        )
        if group_query is None:
            if is_valid_kc_group(group_name, token) is False:
                raise (InvalidGroup(group_name))
            else:
                db_add(Group(kc_groupname=group_name))
                group_query = (
                    db.session.query(Group)
                    .filter_by(kc_groupname=group_name)
                    .one_or_none()
                )
        owner_ids.append(group_query.id)

    row_new["owners"] = owner_ids
    row_new["project_id"] = new_id
    row_obj = table(**row_new)

    if add_to_db:
        row_obj.save_to_db()

    return row_obj


def create_dataset(
    data,
    row,
    column_name,
    new_id,
    user_id,
    table,
    table_name,
    group,
    add_to_db,
):
    visibility = data.get("visibility", "private")
    row.update(
        {
            column_name: new_id,
            "submitter_name": user_id,
            "private": visibility != "visible to all",
            "shared_with": [],
        }
    )

    row_new = {"extra_cols": {}}
    extra_cols = app.config["DATASETS_EXTRA_COLS"]
    for col, value in row.items():
        if col == "dataset_id" or col == "private" or col == "project_id":
            row_new[col] = value
        else:
            if col in extra_cols:
                row_new["extra_cols"][col] = value

                # TODO
                # check if the value strip is still needed?
                # if not isinstance(value, int):
                #     row_new["extra_cols"][col] = value.strip()

                # TODO
                # test if trailing spaces are removed

                # TODO
                # check if trailing spaces are appearing
                # in other columns as well

                # TODO
                # fix spelling errors in the column names
                if col == "healthyControllsIncluded":
                    row_new["extra_cols"][col] = value is True

            else:
                row_new[col] = value

    # get the project id from the project table
    project_id = (
        db.session.query(Project)
        .filter(Project.project_id == row_new["project_id"])
        .with_entities(Project.id)
        .one_or_none()
    )
    row_new["project_id"] = project_id[0]
    row_obj = table(**row_new)

    if add_to_db:
        db_update_groups(group, row_obj)
        db_update_project(row_obj)
    return True


class SubmissionTypeSpecificSchemaModification:

    """
    modify the validation_schema based on the submission type
    """

    def __init__(self, data, schema, table):
        self.data = data
        self.schema = schema
        self.table = table

    def modify_validation_schema(self, table_name):
        """
        helper function to implement a switch case functionality
        """
        # call one of the table specific functions
        schema = getattr(self, f"table_{table_name}")()
        return schema

    def table_PROJECT(self):
        """
        modify the validation_schema for the projects table
        """
        self.schema["properties"]["logoUrl"]["pattern"] = ".*"
        if self.data.get("logoUrl", "") != "":
            regex = "^(http|https)://.*$"
            self.schema["properties"]["logoUrl"]["pattern"] = regex

        self.schema["properties"]["datasetVisibilityDefault"]["enum"] = [
            "private",
            "visible to all",
        ]
        return self.schema

    def table_DATASET(self):
        """
        modify the validation_schema for the datasets table
        """

        proj_id = self.data.get("project_id")
        if proj_id is None:
            raise WrongSchema("project_id is missing")

        query = (
            db.session.query(Project)
            .filter(Project.project_id == proj_id)
            .with_entities(Project.extra_cols)
        )
        ds_extra_cols = query.one_or_none()
        if ds_extra_cols is None:
            raise EmptyQuery(query, "project not exist")

        extra_cols = ds_extra_cols[0]

        # modify the disease enums in the schema
        default = ["healthy control"]
        self.schema["properties"]["disease"]["enum"] = default + extra_cols[
            "diseases"
        ].split(",")

        # TODO
        # this has not tests yet
        if extra_cols["dataset_visibility_changeable"] is False:
            self.schema["properties"]["visibility"]["enum"] = [
                extra_cols["dataset_visibility_default"]
            ]

        for field in ["samplesCount", "featuresCount"]:
            self.schema["properties"][field] = {
                "type": "string",
                "pattern": r"^\d+$",
            }

        self.schema["properties"]["file"] = {
            "type": "array",
            "items": {
                "type": "string",
                "allOf": [
                    {"pattern": "^[^\\s]+$"},
                    {"pattern": "^.+\\.pdf$"},
                ],
            },
            "maxItems": 1,
        }

        self.schema["properties"]["file2"] = {
            "type": "array",
            "items": {
                "type": "string",
                "allOf": [
                    {"pattern": "^[^\\s]+$"},
                    {"pattern": "^.+\\.(csv|json)$"},
                ],
            },
            "maxItems": 1,
        }

        self.schema["properties"]["project_id"] = {
            "type": "string",
            "minLength": 1,
        }

        return self.schema


def react_create_builder(
    group,
    group_name: str,
    user_id: str,
    table,
    table_name: str,
    column_name: str,
    request_data,
    token=None,
    add_to_db=True,
):
    api_success = []

    if not isinstance(request_data, list):
        raise WrongSchema("payload is not a list")

    validate_ids(request_data, column_name)

    # TODO
    # possible fields should be extracted from
    # DATASETS_COL_MAPPING in config.py

    # new idea for DATASETS_COL_MAPPING
    # it should not only map the column names from the client
    # to the server column names
    # but also contain the field types (e.g. string, integer, boolean)

    # FIXME
    # there seems to be a missunderstanding what type of data
    # is expected for the field "file"?
    # should be a string or an array of length 1?

    # schema = get_obj_schema(
    #     {
    #         k: {"type": v}
    #         for k, v in app.config[f"{table_name}_FIELDS_TO_TYPES"].items()
    #     },
    #     app.config.get(f"{table_name}_FIELDS_ENUMS"),
    #     required=["id"],
    # )

    fields = app.config[f"SUBMIT_{table_name}S_HEADERS"]
    schema = get_obj_schema2(
        fields,
        app.config.get(f"{table_name}_FIELDS_ENUMS"),
        required=[field["id"] for field in fields],
    )

    # TODO
    # make sure that all mandatory string fields have a string with length > 0
    # get the mandatory information from the config file
    # config_3tr_client.py

    # TODO
    # replace private / visible to all with a Boolean

    # TODO
    # check that healthyControlsIncluded is boolean

    for data in request_data:

        schema = SubmissionTypeSpecificSchemaModification(
            data, schema, table
        ).modify_validation_schema(table_name)

        try:
            validate_schema(data, schema)
        except WrongSchema as err:
            raise WrongSchema(err.message)

        new_id = data["id"]

        if group is None:
            group = Group(kc_groupname=group_name)
            db_add(group)

        db_id_still_available(group, table, table_name, column_name, new_id)

        #  # TODO
        # map the react table Ids to the database table Ids

        # get the react table Ids already here
        # so there is no need to loop twice

        # map the react table Ids to the database table Ids
        # already when creating the variable "row"
        # so there is no need to loop twice
        row = {
            k: data.get(k, "")
            for k in data.keys()
            if k not in ["id", "visibility"]
        }

        if table_name == "PROJECT":
            success = create_project(
                row, new_id, table, table_name, token, add_to_db
            )
            assert success

            response = "project inserted"
            if add_to_db is False:
                response = "projects can be inserted"

        if table_name == "DATASET":
            success = create_dataset(
                data,
                row,
                column_name,
                new_id,
                user_id,
                table,
                table_name,
                group,
                add_to_db,
            )

        api_success.append(success)

    status_code = 200

    # TODO
    # below is needed for having the possibility to
    # return which submissions failed but for now it
    # should stop the submission and return an error immediately

    # if any(isinstance(e, str) for e in api_success):
    #     # TODO
    #     # return also the if some are failed and explain why
    #     response = ";".join(api_success)
    #     status_code = 405

    if table_name == "DATASET":
        response = ("dataset inserted", new_id)

        # !FIXME
        # This needs to be tested
        if add_to_db is False:
            response = {
                "message": "datasets can be inserted",
            }

    return response, status_code




def react_create_builder_returning(
    group,
    group_name: str,
    user_id: str,
    table,
    table_name: str,
    column_name: str,
    request_data,
    token=None,
    add_to_db=True,
):
    """Patched method to return the result."""
    api_success = []

    if not isinstance(request_data, list):
        raise WrongSchema("payload is not a list")

    validate_ids(request_data, column_name)

    fields = app.config[f"SUBMIT_{table_name}S_HEADERS"]
    schema = get_obj_schema2(
        fields,
        app.config.get(f"{table_name}_FIELDS_ENUMS"),
        required=[field["id"] for field in fields],
    )

    for data in request_data:

        schema = SubmissionTypeSpecificSchemaModification(
            data, schema, table
        ).modify_validation_schema(table_name)

        try:
            validate_schema(data, schema)
        except WrongSchema as err:
            raise WrongSchema(err.message)

        new_id = data["id"]

        if group is None:
            group = Group(kc_groupname=group_name)
            db_add(group)

        db_id_still_available(group, table, table_name, column_name, new_id)

        row = {
            k: data.get(k, "")
            for k in data.keys()
            if k not in ["id", "visibility"]
        }

        if table_name == "PROJECT":
            success = create_project_returning(
                row, new_id, table, table_name, token, add_to_db
            )
            assert success
    
    
    
            response = {}
            response.update(getattr(success, 'extra_cols'))
            for field in ['project_id', 'name']:
                response[field] = getattr(success, field, None) 
            response['created_at'] = str(getattr(success, 'created_at', ''))

            # response = success.__dict__.copy()
            # del response['_sa_instance_state']
            # del response['extra_cols']
            # response.update(success.__dict__.get('extra_cols', {}))
            response = json.dumps(response)

            # response = "project inserted"
            if add_to_db is False:
                response = "projects can be inserted"

        if table_name == "DATASET":
            success = create_dataset(
                data,
                row,
                column_name,
                new_id,
                user_id,
                table,
                table_name,
                group,
                add_to_db,
            )

        api_success.append(success)

    status_code = 200

    return response, status_code
