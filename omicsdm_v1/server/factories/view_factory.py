import math
import re
from copy import deepcopy
from datetime import datetime, timedelta

from sqlalchemy import or_, asc, desc

from server.app import db, app
from server.model import Group, Groups, Dataset, Project
from server.utils.schema import get_obj_schema, modify_schema
from server.utils.validators import validate_schema, validate_timestamps
from server.utils.error_handler import WrongKey, WrongSchema
from server.utils.table_methods import db_add, db_commit

from server.utils.ceph import create_presigned_url

from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.sql import text

from typing import Any, Iterator
import operator
from functools import reduce


def unevalled_all(ls: Iterator[Any]) -> Any:
    """Build (ls[0] and ls[1] ... ls[n]) but does not evaluate like all() does."""
    return reduce(operator.and_, ls)

def unevalled_or(ls: Iterator[Any]) -> Any:
    """Build (ls[0] or ls[1] ... ls[n]) but does not evaluate like or() does."""
    return reduce(operator.or_, ls)


def get_col_val_for_table_actions(table, table_name, data, key):
    """
    table = sql table
    data = request data
    key = "value" for filtering and "desc" for sorting
    """
    col_id = data.get("id")
    val = data.get(key)

    col = app.config[f"{table_name}_COL_MAPPING"].get(col_id)
    extra_cols = app.config[f"{table_name}_EXTRA_COLS"]

    # TODO
    # find a better naming for the col "checkbox"
    # do not forget to do it on the frontend too !

    # FIXME
    # project_id should be allowed in request data

    # => The config "FILES_COL_MAPPING" needs to be updated
    # needs to include "project_id"

    allowed_cols = ["checkbox", "owner", "project_id"] + extra_cols
    if col is None and col_id not in allowed_cols:
        raise WrongKey(col_id)

    if col_id == "checkbox" or col_id == "owner":
        return col, val

    if col_id in extra_cols:
        return "extra_cols", val

    return getattr(table, col), val


def modify_query(query):

    for filtered_field in query:
        if filtered_field["value"] in ["True", "False"]:
            filtered_field["value"] = (
                True if filtered_field["value"] == "True" else False
            )
            continue

        if filtered_field["value"] in [True, False]:
            continue

        # commented out because right now all the input is in string format
        # but in the future we might want to change this

        # try:
        #     filtered_field["value"] = int(filtered_field["value"])
        # except ValueError:
        #     continue


def filter_by_id(col_name, table_name, table, val, db_query):

    vals = val.split(",")
    if col_name == "id" and table_name == "FILES":
        vals = [int(val) for val in vals]
        db_query = db_query.filter(table.id.in_(vals))
        return db_query

    # TODO
    # missing partial filter for dataset_id
    if col_name == "dataset_id":
        col = Dataset.dataset_id
        db_query = db_query.filter(col.in_(vals))

    # TODO
    # add pytest
    # and end to end tests to make sure that it is possible
    # to filter by multiple project or dataset ids
    if col_name == "project_id":
        def gen_filter(val):
            if '*' in val:
                return Project.project_id.ilike(val.replace('*', '%'))
            else:
                return Project.project_id == val

        project_ids = (
            db.session.query(Project)
            # .filter({Project.project_id.in_(vals)})
            .filter(unevalled_or([
                gen_filter(v) for v in vals
            ]))
            .with_entities(Project.id)
            .all()
        )
        proj_ids = [proj_id[0] for proj_id in project_ids]

        if table_name == "PROJECTS":
            return db_query.filter(table.id.in_(proj_ids))

        if table_name == "DATASETS":
            return db_query.filter(table.project_id.in_(proj_ids))

        if table_name == "FILES":
            return db_query.filter(Dataset.project_id.in_(proj_ids))

    # if table_name == "FILES":
    #     dataset_ids = (
    #         db.session.query(Dataset)
    #         .filter(Dataset.project_id.in_(proj_ids))
    #         .with_entities(Dataset.id)
    #         .all()
    #     )
    #     ds_ids = [dataset_id[0] for dataset_id in dataset_ids]
    #     return db_query.filter(table.dataset_id.in_(ds_ids))

    return db_query


def filter_by_submit_date(col, val, db_query):
    # ! Question
    # how should filtering by date be tested
    # since the database is wiped completely after each test run

    # TODO
    # add tests for it
    # 1. if the query is in the correct format
    #  (-> should throw an error and the frontend should show it)

    # * Note: this is a hack because the date input
    # * from the frontend is a string e.g. "2022/04/01, 12:39:05"
    if "," not in val:
        validate_timestamps(val, "%Y/%m/%d")

        val = val.replace("/", "-")
        db_query = db_query.filter(
            col.between(f"{val} 00:00:00", f"{val} 23:59:59")
        )
    else:
        validate_timestamps(val, "%Y/%m/%d, %H:%M:%S")

        datetime_obj = datetime.strptime(val, "%Y/%m/%d, %H:%M:%S")
        db_query = db_query.filter(
            col.between(datetime_obj, datetime_obj + timedelta(seconds=1))
        )
    return db_query


def filter_by_shared_with(val, db_query):

    # TODO
    # it should be possible to filter by multiple groups

    private = False if val == "ALL GROUPS" else True
    db_query = db_query.filter(Dataset.private == private)
    if val not in ["ALL GROUPS", "None"]:

        # TODO
        # loop over all the groups
        # to filter by multiple groups

        group_query = (
            db.session.query(Group)
            .filter(Group.kc_groupname == val)
            .with_entities(Group.id)
            .one()
        )
        val = group_query[0]
        db_query = db_query.filter(Dataset.shared_with.contains([val]))

    return db_query


# TODO
# try to merge parts of this function with the one above
# with the sort_columns function
def filter_columns(schema, query, db_query, filter_cols, table, table_name):

    # w/o deepcopy all the other queries will use the modified config
    filtered_fields_to_types = deepcopy(app.config["FILTERED_FIELDS_TYPES"])

    # FIXME
    # filter_columns is too complex

    try:
        modify_query(query["filtered"])
    except TypeError:
        validate_schema(query, schema)

    query_vals = [dict["value"] for dict in query["filtered"]]

    filtered_fields_to_types["value"] = []

    # TODO
    # filtered fields to types should be only modified
    # if this is allowed by e.g.
    # DATASETS_FIELDS_TO_TYPES

    type_mapping = {str: "string", int: "integer", bool: "boolean"}
    for val_type in type_mapping.keys():
        if any(isinstance(val, val_type) for val in query_vals):
            val_type_string = type_mapping[val_type]
            filtered_fields_to_types["value"].append(val_type_string)

    modify_schema(schema, "filtered", filtered_fields_to_types)
    validate_schema(query, schema)

    # !FIXME
    # Shared with column is not filterable

    fields_to_types = app.config[f"{table_name}_FIELDS_TO_TYPES"]
    for col_to_id in filter_cols:

        col_name, val = col_to_id.values()

        if col_name == "shared_with":
            db_query = filter_by_shared_with(val, db_query)
            continue

        if col_name == "visibility":
            val = True if val == "private" else False
            db_query = db_query.filter(Dataset.private == val)
            continue

        if not (col_name == "project_id" and table_name == "FILES"):
            col, val = get_col_val_for_table_actions(
                table, table_name, col_to_id, "value"
            )

        # double check if the used variable type is allowed
        if type_mapping[type(val)] not in fields_to_types[col_name]:
            raise WrongSchema(
                f"{type_mapping[type(val)]} is not allowed for {col_name}"
            )

        if col_name in ["id", "project_id", "dataset_id"]:
            db_query = filter_by_id(col_name, table_name, table, val, db_query)
            continue

        # TODO
        # it would be good to a class
        # which acts as a switch for the different columns

        # TODO write a test for it
        # filter column by owner
        # TODO find a better name for the col "checkbox"

        if col_name == "submit_date":
            db_query = filter_by_submit_date(col, val, db_query)
            continue

        is_int = False
        if type(val) == str:
            is_int = re.match(r"^[-+]?\d+$", val)

        if col == "extra_cols":
            # TODO
            # it would be good if the frontend would send for number queries
            # an integer instead of a string
            if type(val) == bool or is_int:
                db_query = db_query.filter(
                    table.extra_cols.contains({col_to_id["id"]: val})
                )
                continue

            # partial match
            # ! has no API tests yet
            db_query = db_query.filter(
                text("extra_cols->> :key LIKE :value").bindparams(
                    key=col_to_id["id"], value="%" + val + "%"
                )
            )
            continue

        if is_int:
            # * only applies on the file level (file.version)
            db_query = db_query.filter(col == val)
            continue

        filter_vals = val.split(",")
        if len(filter_vals) > 1:
            db_query = db_query.filter(col.in_(filter_vals))
            continue

        if col_name == "checkbox" or col_name == "owner":
            col = Group.kc_groupname

        # try to implement a partial match
        # ! has no API tests yet
        db_query = db_query.filter(col.ilike(f"%{val}%"))

    return db_query


# TODO merge with filter_columns
def sort_columns(schema, query, db_query, sort_cols, table, table_name):

    modify_schema(schema, "sorted", app.config["SORTED_FIELDS_TYPES"])
    validate_schema(query, schema)

    col, desc_bool = get_col_val_for_table_actions(
        table, table_name, sort_cols[0], "desc"
    )

    col_name = sort_cols[0]["id"]

    # sort by owner
    if col_name == "checkbox" or col_name == "owner":
        col = Group.kc_groupname

    # * only applies on the file level (file.dataset_id))
    if col_name == "dataset_id":
        col = Dataset.dataset_id

    # TODO filter by Project ID is still missing

    if col == "extra_cols":
        # sort by JSON column
        if desc_bool:
            db_query = db_query.order_by(desc(table.extra_cols[col_name]))
        else:
            db_query = db_query.order_by(asc(table.extra_cols[col_name]))
    else:
        if desc_bool:
            db_query = db_query.order_by(desc(col))
        else:
            db_query = db_query.order_by(asc(col))

    return db_query


class ViewSpecificFields:

    """
    returns view specific fields
    """

    def __init__(
        self,
        table,
        shared_with,
        users_group_name,
        query_result,
        users_group_id=None,
    ):
        self.table = table
        self.shared_with = shared_with
        self.users_group_id = users_group_id
        self.users_group_name = users_group_name
        self.query_result = query_result
        self.group_query = db.session.query(Group)

        self.query_result_mapped = {}
        self.ds_query_result = None

    def get_fields(self, table_name):
        """
        helper function to implement a switch case functionality
        """

        # map from react table identifiers to db table identifiers
        mapping = deepcopy(app.config[f"{table_name}_COL_MAPPING"])
        # w/o deepcopy all the other queries will use the modified config

        # change config so this if statement is no longer needed
        if self.users_group_name == "admin" and table_name == "PROJECTS":
            mapping["id"] = "id"

        self.query_result_mapped = {
            k: getattr(self.query_result, v) for k, v in mapping.items()
        }

        # TODO
        # put this in config.py
        if table_name == "PROJECTS":
            extra_cols = [
                "diseases",
                "logo_url",
                "description",
                "dataset_visibility_default",
                "dataset_visibility_changeable",
                "file_dl_allowed",
            ]
        elif table_name == "DATASETS":
            extra_cols = [
                "disease",
                "treatment",
                "molecularInfo",
                "sampleType",
                "dataType",
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
                "file",
                "policy_presigned_url",
                "file2",
                "policy_presigned_url",
            ]
        else:
            # table_name == "FILES"
            extra_cols = ["Comment"]

        json_data = getattr(self.query_result, "extra_cols")
        self.query_result_mapped["extra_cols"] = {}

        for col in extra_cols:
            self.query_result_mapped["extra_cols"][col] = json_data.get(
                col, ""
            )

        # call one of the table specific functions
        (
            view_specific_fields,
            group_query,
            ds_query_result,
            self.query_result_mapped,
        ) = getattr(self, f"table_{table_name}")()

        if table_name != "PROJECTS":
            if len(self.shared_with) == 0:
                self.shared_with = ["ALL GROUPS"]
                group_id = ds_query_result.groups[0].group_id
                if group_id == self.users_group_id and ds_query_result.private:
                    self.shared_with = ["None"]

            owner = group_query.with_entities(
                Group.kc_groupname
            ).one_or_none()[0]

            is_owner = False
            if owner == self.users_group_name:
                is_owner = True

            self.query_result_mapped.update(
                {
                    "submit_date": self.query_result.submission_date.strftime(
                        "%Y/%m/%d, %H:%M:%S"
                    ),
                    "shared_with": ",".join(self.shared_with),
                    "isUserOwner": is_owner,
                    "owner": owner,
                }
            )
        else:
            # table_name == "PROJECTS"

            # TODO
            # check if below would be good to as a general function
            # for all tables

            # TODO
            # define in the config which fields are supposed to
            # return a boolean so below does not need to loop over all fields
            view_specific_fields = {
                k: str(v) for k, v in view_specific_fields.items()
            }

        self.query_result_mapped.update(view_specific_fields)

        return self.query_result_mapped

    def table_PROJECTS(self):
        """
        returns view specific fields for projects
        (only for the admin users)
        """
        view_specific_fields = {}

        owner_ids = self.query_result_mapped["owners"]

        # put this in config.py
        extra_cols = [
            "description",
            "dataset_visibility_default",
            "dataset_visibility_changeable",
            "file_dl_allowed",
            "diseases",
            "logo_url",
        ]

        view_specific_fields = {}
        for col in extra_cols:
            view_specific_fields[col] = self.query_result_mapped[
                "extra_cols"
            ].get(col, "")
            # not implemented yet
            # try:
            #     data[col] = str(getattr(project, "extra_cols")[col])

            # # below is only for a database migration
            # # can only be tested with a database modification
            # # whithin a test run
            # except TypeError as err:
            #     if str(err) != "'NoneType' object is not subscriptable":
            #         raise
            #     else:
            #         data[col] = ""
            # except KeyError:
            #     data[col] = ""

        db_query = (
            db.session.query(Group)
            .filter(Group.id.in_(owner_ids))
            .with_entities(Group.kc_groupname)
            .all()
        )

        owners = [group[0] for group in db_query]
        view_specific_fields["owners"] = ",".join(owners)

        # not implemented yet
        # for col in extra_cols:

        return (
            view_specific_fields,
            self.group_query,
            self.ds_query_result,
            self.query_result_mapped,
        )

    def table_DATASETS(self):
        def regenerate_presigned_url(
            view_specific_fields, file_field, url_field, subkey
        ):
            """
            returns a presigned url for a file
            """

            group_name = group_query.with_entities(
                Group.kc_groupname
            ).one_or_none()[0]
            dataset_id = self.query_result.dataset_id

            # TODO
            # figure out why the file field is an array

            file_name = view_specific_fields[file_field][0]
            presigned_url = view_specific_fields[url_field]

            dataset = (
                Dataset.query.filter(Dataset.id == self.query_result.id)
                .with_for_update()  # locks the row
                .one_or_none()
            )

            # TODO
            # ! needs tests

            renew = False
            if presigned_url == "regenerate":
                renew = True
            else:
                # check if x_amz_date is in the past
                x_amz_date = presigned_url.split("X-Amz-Date=")[1].split("&")[
                    0
                ]
                x_amz_date_dt = datetime.strptime(x_amz_date, "%Y%m%dT%H%M%SZ")
                if x_amz_date_dt + timedelta(days=7) < datetime.utcnow():
                    renew = True

            if renew:
                # renew presigned_url
                presigned_url = create_presigned_url(
                    app.config,
                    "get_object",
                    group_name,
                    dataset_id,
                    file_name,
                    None,
                    subkey=subkey,
                    expiration=604800,
                    # 1 week !longer is not possible
                )
                dataset.extra_cols[url_field] = presigned_url
                flag_modified(dataset, "extra_cols")
                db_commit()

            view_specific_fields[url_field] = presigned_url
            return view_specific_fields

        # this fields are interesting for the analysis field as well
        group_id = self.query_result.groups[0].group_id
        group_query = self.group_query.filter(Group.id == group_id)

        self.ds_query_result = Dataset.find_by_id(self.query_result.id)

        # ! fixme
        # there are two healthyControllsIncluded
        # 'healthyControllsIncluded':'False'
        # 'healthy_control_included':False

        # put this in config.py
        extra_cols = [
            "disease",
            "treatment",
            "molecularInfo",
            "sampleType",
            "dataType",
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
            "file",
            "policy_presigned_url",
            "file2",
            "clinical_presigned_url",
        ]

        view_specific_fields = {}
        for col in extra_cols:
            view_specific_fields[col] = self.ds_query_result.extra_cols.get(
                col, ""
            )

        # return string for healthy Controls Included

        # FIXME
        # fix typo in healthyControllsIncluded
        # should be healthyControlsIncluded
        view_specific_fields["healthyControllsIncluded"] = (
            "True"
            if self.query_result_mapped["extra_cols"].get(
                "healthyControllsIncluded"
            )
            else "False"
        )

        view_specific_fields["visibility"] = (
            "private"
            if self.query_result_mapped["visibility"]
            else "visible to all"
        )

        project_id = (
            db.session.query(Project)
            .filter(Project.id == self.ds_query_result.project_id)
            .with_entities(Project.project_id)
            .one_or_none()
        )
        view_specific_fields["project_id"] = project_id[0]

        # TODO
        # ! add tests for the presigned url regeneration

        # TODO
        # make sure that after the change it is still
        # working on the frontend
        if view_specific_fields["policy_presigned_url"] != "":
            view_specific_fields = regenerate_presigned_url(
                view_specific_fields,
                "file",
                "policy_presigned_url",
                "dataPolicy",
            )

        # TODO
        # better put in a loop

        # TODO
        # all this regeneration stuff is no longer needed
        # because the presigned url should be generated on the fly

        if view_specific_fields["clinical_presigned_url"] != "":
            view_specific_fields = regenerate_presigned_url(
                view_specific_fields,
                "file2",
                "clinical_presigned_url",
                "clinical",
            )

        # TODO
        # would be better to change the name of the field
        # in the database to something more meaningful but not sure
        # if this would still be possible w/o breaking the database
        view_specific_fields["policy_file"] = view_specific_fields["file"]
        view_specific_fields["clinical_file"] = view_specific_fields["file2"]
        del view_specific_fields["file"]
        del view_specific_fields["file2"]

        return (
            view_specific_fields,
            group_query,
            self.ds_query_result,
            self.query_result_mapped,
        )

    def table_FILES(self):

        group_query = (
            self.group_query.join(Groups, Group.id == Groups.group_id)
            .join(Dataset, Dataset.id == Groups.dataset_id)
            .join(self.table, self.table.dataset_id == Dataset.id)
            .filter(self.table.id == self.query_result.id)
        )

        self.ds_query_result = Dataset.find_by_id(self.query_result.dataset_id)

        view_specific_fields = {
            "id": self.query_result_mapped["id"],  # =row id
            "dataset_id": self.ds_query_result.dataset_id,
        }

        view_specific_fields["visibility"] = (
            "private" if self.ds_query_result.private else "visible to all"
        )

        project = (
            db.session.query(Project)
            .join(Dataset, Dataset.project_id == Project.id)
            .filter(Dataset.id == self.ds_query_result.id)
            .with_entities(Project)
            .one_or_none()
        )
        view_specific_fields["project_id"] = project.project_id

        json_data = self.query_result_mapped["extra_cols"]

        # put this in config.py
        FILES_COL_MAPPING_REVERSE = {
            "Comment": "comment",
        }

        # TODO
        # visibility is not shown in the table

        for col in json_data:
            view_specific_fields[FILES_COL_MAPPING_REVERSE[col]] = json_data[
                col
            ]

        return (
            view_specific_fields,
            group_query,
            self.ds_query_result,
            self.query_result_mapped,
        )


def data_view_builder(users_group_name, table, table_name, request, ns):
    """
    2 steps:
        1. get all Datasets shared with that keycloak group or visible to all
        2. generate the object needed for displaying them in the React table
    """

    admin = users_group_name == "admin"

    query = request.get_json()
    if not query and isinstance(request.data, bytes):
        import json
        query = json.loads(request.data)

    group = (
        db.session.query(Group)
        .filter_by(kc_groupname=users_group_name)
        .one_or_none()
    )

    # TODO
    # try to merge this with the admin_view_builder

    # initialize response result
    page = query.get("page", 1)
    page_size = query.get("pageSize", 100)

    res = {
        "items": [],
        "_meta": {
            "total_items": 0,
            "total_pages": 1,
            "page": page,
            "page_size": page_size,
        },
    }

    # 2. get all results which are shared with that keycloak group (group_name)
    # or are visible to all (sql table column private = false)
    db_query = db.session.query(table).with_entities(table)

    users_group_id = None
    if not admin:
        ns.logger.info(
            f"get {table_name} visible for kc group {users_group_name}"
        )
        if table_name == "FILES":
            db_query = (
                db_query.join(Dataset, Dataset.id == table.dataset_id)
                .filter(table.upload_finished.is_(True))
                .filter(table.enabled.is_(True))
            )

        if group is None:
            ns.logger.info(f"add kc group {users_group_name} to db")
            group = Group(kc_groupname=users_group_name)
            db_add(group)

        users_group_id = group.id
        groupid_to_name = {users_group_id: users_group_name}
        conditions = [
            Groups.group_id == users_group_id,
            table.shared_with.contains([users_group_id]),
            Dataset.private.is_(False),
        ]
        db_query = db_query.filter(or_(*conditions))

    if not table_name == "PROJECTS" and not admin:
        db_query = db_query.join(Groups, Groups.dataset_id == Dataset.id).join(
            Group, Group.id == Groups.group_id
        )

    # 3. build the validation schema
    fields_to_types = app.config["VIEW_FIELDS_TYPES"]
    props = {k: {"type": fields_to_types[k]} for k in fields_to_types}

    # w/o deepcopy schema is not garbage collected
    schema = deepcopy(get_obj_schema(props))

    filter_cols = query.get("filtered")
    sort_cols = query.get("sorted")

    if not any([filter_cols, sort_cols]):
        validate_schema(query, schema)
        ns.logger.info("schema validated")

    if filter_cols:
        ns.logger.info("filtering by columns")
        db_query = filter_columns(
            schema, query, db_query, filter_cols, table, table_name
        )

    if sort_cols:
        ns.logger.info("sort columns")
        db_query = sort_columns(
            schema, query, db_query, sort_cols, table, table_name
        )

    # get total number of items
    total_items = len(db_query.all())

    # filter based on page and page_size
    db_query = db_query.offset((page - 1) * page_size).limit(page_size)
    results = db_query.all()

    res["_meta"].update(
        {
            "total_items": total_items,
            "total_pages": math.ceil(total_items / page_size),
        }
    )
    ns.logger.info(f"total results count:{total_items}")
    ns.logger.info(f"query results count:{len(results)}")

    for query_result in results:

        shared_with = []
        if not admin:
            for group_id in query_result.shared_with:
                group_name = groupid_to_name.get(group_id)

                if group_name is None:
                    group_name = Group.find_by_id(group_id).kc_groupname
                    groupid_to_name[group_id] = group_name

                shared_with.append(group_name)

        query_result_mapped = ViewSpecificFields(
            table,
            shared_with,
            users_group_name,
            query_result,
            users_group_id=users_group_id,
        ).get_fields(table_name)

        # remove the extra_cols from the result
        del query_result_mapped["extra_cols"]

        res["items"].append(query_result_mapped)

    # res includes the fileName
    # but it is still not shown on the frontend

    return res
