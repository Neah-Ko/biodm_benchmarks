from pathlib import Path
import requests

import json
import gzip
from io import BytesIO

import jwt

import uuid

from sqlalchemy import create_engine, Column
from sqlalchemy.orm import Session

file_upload_suffixes = ["files/startupload", "files/finishupload"]
file_view_url_suffix = "files/all"

url_root = "/api/"


def val_in_list(val, iterable, key, key_for_loop, key_for_if):
    return [e[key] for e in iterable[key_for_loop] if e[key_for_if] == val][
        0
    ] == val


def exception_handler(func):
    def inner_function(*args, **kwargs):

        res = func(*args, **kwargs)
        if res.status_code in [200, 400, 404, 405]:
            return res

        return json.loads(res.data.decode("utf8"))

    return inner_function


@exception_handler
def req_get(client, header, url_suffix):
    return client.get(url_root + url_suffix, headers=header)


@exception_handler
def req_post(client, header, url_suffix, data):
    return client.post(
        url_root + url_suffix, headers=header, data=json.dumps(data)
    )


@exception_handler
def req_del(client, header, url_suffix, data):
    return client.delete(
        url_root + url_suffix, headers=header, data=json.dumps(data)
    )


@exception_handler
def req_put(client, header, url_suffix, args):

    for e in args:
        url_suffix += "&" + e

    return client.put(url_root + url_suffix, headers=header)


# @exception_handler
# def req_post_file(client, header, data):
#     return client.post(
#         "/api/file?arg=upload",
#         headers=header,
#         data=data,
#         content_type="multipart/form-data",
#     )


def modify_db(
    cfg, cmd, table, filter_field_to_val, col_to_subcol, current_val
):
    engine = create_engine(cfg)

    with Session(engine) as session:
        session.execute(cmd)
        session.commit()

        # check if the command was successful
        col, subcol = col_to_subcol
        query = (
            session.query(table)
            .filter_by(**filter_field_to_val)
            .with_entities(Column(col))
            .one_or_none()
        )
        if subcol:
            assert query[0][subcol] != current_val
        else:
            assert query[0] != current_val


def del_from_db(cfg, cmd):
    engine = create_engine(cfg)
    with Session(engine) as session:
        session.execute(cmd)
        session.commit()


def get_token(user, cfg):
    payload = (
        f"client_id={cfg.CLIENT}&grant_type=password&"
        f"username={user}&password={cfg.PASSWORD}"
    )
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(  # nosec (don't need to verify on localhost)
        cfg.TOKEN_URL, data=payload, headers=headers, verify=False
    )
    return response.json()["access_token"]


def get_kc_groups(token, cfg):

    sep = f"{'-'*5}"

    public_key = (
        f"{sep}BEGIN PUBLIC KEY{sep}\n{cfg.IDRSA}\n{sep}END PUBLIC KEY{sep}"
    )

    try:
        decoded = jwt.decode(
            token, public_key, algorithms="RS256", options=cfg.JWT_OPTIONS
        )
    except Exception as e:
        return {
            "message": f"Something went wrong {e} {e.__class__.__name__}"
        }, 500

    return [s.replace("/", "") for s in decoded.get("group")]


def get_header(user, cfg):

    token = get_token(user, cfg)

    return {
        "Content-Type": "application/json",
        "Authorization": token,
        "groups": get_kc_groups(token, cfg),
    }


def add_project(
    client,
    header,
    project_id,
    project_fields,
    projects_create_url_suffix,
    submit=True,
    overwrite_fields=None,
    expected_error=None,
    field_to_be_deleted=None,
):
    """test
    only works with a user which is in the admin group
    """
    # projects_create_url_suffix = "projects/create"

    project = {}
    for key, data_type in project_fields:
        val = "test"
        if data_type == "list(str)":
            val = "test"
            # val = "test,test2"

        elif data_type == "bool":
            val = True

        if key == "datasetVisibilityDefault":
            val = "private"
        project[key] = val

    project.update(
        {
            "id": project_id,
            "owners": "3tr",
            "logoUrl": "",
            "diseases": "COPD,ASTHMA,CD,UC,MS,SLE,RA",
        }
    )

    project = {key: project[key] for key, _ in project_fields}

    if field_to_be_deleted:
        del project[field_to_be_deleted]

    if overwrite_fields:
        project.update(overwrite_fields)

    if not submit:
        return project

    # TODO
    # logic below in a function
    # because it is the same for add_dataset and add_file
    res = req_post(client, header, projects_create_url_suffix, [project])

    if expected_error:
        try:
            res = json.loads(res.data.decode("utf8"))
        except Exception:
            pass

        try:
            assert expected_error in res["message"]
        except AssertionError:
            raise AssertionError(res["message"])
        return

    try:
        response = json.loads(res.data.decode("utf8"))

        if projects_create_url_suffix == "projects/create":
            assert "project inserted" in response["message"]
        else:
            return response

    except AssertionError:
        raise AssertionError(res.data.decode("utf8"))


# TODO
# There is still a test missing for checking
# if e.g. the number of total_pages calculated works as expected


def filter_view(client, header, view_url_suffix, query=None):
    res = req_post(
        client,
        header,
        view_url_suffix,
        {
            "page": 1,
            "pageSize": 100,
            "sorted": None,
            "filtered": query,
        },
    )
    return res


def upload_file_complete(
    client,
    header_admin,
    header,
    project_id,
    dataset_id,
    project_fields,
    dataset_fields,
    file_name,
    group="3tr",
    dataset_private=True,
    create_dataset=True,
    file_dl_allowed=True,
):
    """
    Before being able to upload a file
    (1. a project has to be created)
    2. a dataset has to be created

    return file_ids
    """

    if project_id is None:
        project_id = str(uuid.uuid4())

    if dataset_id is None:
        dataset_id = str(uuid.uuid4())

    proj_overwrite_fields = None
    if file_dl_allowed is False:
        proj_overwrite_fields = {"fileDlAllowed": False}

    if create_dataset:
        add_dataset(
            client,
            header_admin,
            header,
            project_fields,
            dataset_fields,
            dataset_id=dataset_id,
            project_id=project_id,
            private=dataset_private,
            proj_overwrite_fields=proj_overwrite_fields,
        )

    res = upload_file(
        client,
        header,
        project_id,
        dataset_id,
        file_upload_suffixes,
        file_name,
        group_name=group,
    )
    response = json.loads(res.data.decode("utf8"))
    assert "File upload finished" in response["message"]

    # get file ids from the view
    res = filter_view(
        client,
        header,
        file_view_url_suffix,
        [
            {"id": "dataset_id", "value": dataset_id},
            {"id": "name", "value": file_name},
        ],
    )

    response = json.loads(res.data.decode("utf8"))
    assert "items" in response

    file_id = response["items"][0]["id"]
    assert isinstance(file_id, int)

    file_ids = [file_id]
    return file_ids


def do_filtering(args, table, query, expected_count=1):

    # TODO
    # try to establish this
    # as a general function to test the filtering
    # for all views

    client = args["client"]
    header_admin = args["header_admin"]
    header = args["header"]
    project_fields = args["project_fields"]
    dataset_fields = args["dataset_fields"]
    dataset_id = args["dataset_id"]
    project_id = args["project_id"]
    file_name = args["file_name"]

    if table == "file":
        endpoint = file_view_url_suffix
        file_id = upload_file_complete(
            client,
            header_admin,
            header,
            project_id,
            dataset_id,
            project_fields,
            dataset_fields,
            file_name,
            dataset_private=True,
        )[0]

    # initital file view
    res = filter_view(
        client,
        header,
        endpoint,
        [{"id": query["col"], "value": query["val"]}],
    )
    response = json.loads(res.data.decode("utf8"))

    if expected_count == 0:
        assert 0 == len(response["items"])
        return response

    assert file_id == response["items"][0]["id"]
    assert dataset_id == response["items"][0]["dataset_id"]
    assert expected_count == len(response["items"])

    return response


def add_dataset(
    client,
    header_admin,
    header,
    proj_fields,
    ds_fields,
    dataset_id=None,
    project_id=None,
    private=True,
    submit=True,
    overwrite_fields=None,
    create_project=True,
    proj_overwrite_fields=None,
    expected_error=None,
    add_to_db=True,
    field_to_be_deleted=None,
):
    """
    Before being able to create a dataset
    a project has to be created
    """

    if project_id is None:
        project_id = str(uuid.uuid4())

    # TODO
    # pass owner information to add_project

    if create_project:
        add_project(
            client,
            header_admin,
            project_id,
            proj_fields,
            "projects/create",
            submit=True,
            overwrite_fields=proj_overwrite_fields,
        )

    if dataset_id is None:
        dataset_id = str(uuid.uuid4())

    d = {"disease": "CD", "visibility": "private"}

    row = {k: d.get(k, "test") for k in ds_fields}
    row.update(
        {
            "project_id": project_id,
            "id": dataset_id,
            "samplesCount": "1",
            "featuresCount": "1",
            # TODO
            # fix wrong spelling
            "healthyControllsIncluded": True,
            "visibility": "private" if private else "visible to all",
            "file": [],
            "file2": [],
        }
    )

    if field_to_be_deleted is not None:
        del row[field_to_be_deleted]

    if overwrite_fields:
        row.update(overwrite_fields)

    if not submit:
        return row

    url = "datasets/create"

    if add_to_db is False:
        url = "datasets/validate"
        row = [row]

    # TODO
    # in a function
    # because it is the same logic for
    # add_project and add_file
    res = req_post(
        client,
        header,
        url,
        row,
    )

    if expected_error:
        try:
            res = json.loads(res.data.decode("utf8"))
        except Exception:
            pass

        try:
            assert expected_error in res["message"]
            return
        except AssertionError:
            raise AssertionError(res["message"])

    try:
        response = json.loads(res.data.decode("utf8"))

        if add_to_db is False:
            assert response["message"] == "datasets can be inserted"
            return response

        assert "dataset inserted" in response["message"]
        return response
    except AssertionError:
        raise AssertionError(res.data.decode("utf8"))


def sign_url(
    client,
    header_admin,
    header,
    project_fields,
    dataset_fields,
    file_signer_suffix,
    file_name,
    kc_group="3tr",
    bucket="bucketdevel3tropal",
    project_id=None,
    dataset_id=None,
    expected_error=None,
    create_dataset=True,
    ds_private=True,
):

    if project_id is None:
        project_id = str(uuid.uuid4())

    if dataset_id is None:
        dataset_id = str(uuid.uuid4())

    if create_dataset:

        overwrite_fields = None
        if file_name == "dataPolicy.pdf":
            overwrite_fields = {"file": ["dataPolicy.pdf"]}

        if file_name == "clinicalData.csv":
            overwrite_fields = {"file2": ["clinicalData.csv"]}

        add_dataset(
            client,
            header_admin,
            header,
            project_fields,
            dataset_fields,
            dataset_id=dataset_id,
            project_id=project_id,
            overwrite_fields=overwrite_fields,
            private=ds_private,
        )

    version = 1
    upload_dt = "Tue, 08 Feb 2022 19:54:42 GMT"
    file_key = f"{file_name}_uploadedVersion_{version}.tsv"
    s3_key = f"/{bucket}/{kc_group}/{dataset_id}/{file_key}"

    if file_name == "dataPolicy.txt":
        s3_key = f"/{bucket}/{kc_group}/{dataset_id}/dataPolicy/{file_name}"
    if file_name == "clinicalData.csv":
        s3_key = f"/{bucket}/{kc_group}/{dataset_id}/clinical/{file_name}"

    url = f"{file_signer_suffix} x-amz-date:{upload_dt} {s3_key}?uploads"
    res = req_get(client, header, url)

    # TODO
    # in the api replace "error" by "message"
    if expected_error:
        response = json.loads(res.data.decode("utf8"))
        try:
            assert expected_error in response["error"]
        except AssertionError:
            raise AssertionError(response["error"])
        return

    assert res.status_code == 200
    assert "=" in res.data.decode("utf8")


def start_file_upload(
    client,
    header_admin,
    header,
    project_fields,
    dataset_fields,
    file_upload_suffix,
    file_name,
    project_id=None,
    dataset_id=None,
    expected_error=None,
    create_dataset=True,
    overwrite_fields=None,
    field_to_be_deleted=None,
):
    if project_id is None:
        project_id = str(uuid.uuid4())

    if dataset_id is None:
        dataset_id = str(uuid.uuid4())

    if create_dataset:
        add_dataset(
            client,
            header_admin,
            header,
            project_fields,
            dataset_fields,
            dataset_id=dataset_id,
            project_id=project_id,
        )

    data = {
        "projectId": project_id,
        "DatasetID": dataset_id,
        "Comment": "",
        "fileName": file_name,
    }

    if field_to_be_deleted:
        del data[field_to_be_deleted]

    if overwrite_fields:
        data.update(overwrite_fields)

    res = req_post(client, header, file_upload_suffix, data)

    if expected_error:
        try:
            res = json.loads(res.data.decode("utf8"))
        except Exception:
            pass

        try:
            assert expected_error in res["message"]
        except AssertionError:
            raise AssertionError(res["message"])


def upload_file(
    client,
    header,
    project_id,
    dataset_id,
    file_upload_suffixes,
    file_name,
    group_name="3tr",
):
    # upload a file for datasetID test
    # /startUpload is called
    res = req_post(
        client,
        header,
        file_upload_suffixes[0],
        {
            "projectId": project_id,
            "DatasetID": dataset_id,
            "fileName": file_name,
            "Comment": "test",
        },
    )

    # TODO
    # add extra cols to the file upload

    response = json.loads(res.data.decode("utf8"))
    assert f"{group_name}/{dataset_id}/{file_name}" in response["awsKey"]

    # /finishUpload is called
    res2 = req_post(
        client,
        header,
        file_upload_suffixes[1],
        {"aws_key": response["awsKey"]},
    )

    return res2


def upload_data_policy_file(
    client,
    header_admin,
    header,
    project_fields,
    dataset_fields,
    ds_private=True,
):

    ds_id = str(uuid.uuid4())
    file_signer_suffix = "/files?to_sign=POST"
    file_name = "dataPolicy.pdf"
    kc_group = "3tr"

    sign_url(
        client,
        header_admin,
        header,
        project_fields,
        dataset_fields,
        file_signer_suffix,
        file_name,
        kc_group=kc_group,
        dataset_id=ds_id,
        ds_private=ds_private,
    )

    # /finishUpload is called
    aws_key = f"{kc_group}/{ds_id}/dataPolicy/{file_name}"

    res2 = req_post(
        client,
        header,
        "datasets/extrafile/uploadfinish",
        {"aws_key": aws_key},
    )

    response2 = json.loads(res2.data.decode("utf8"))
    assert "File upload finished" in response2["message"]

    return ds_id, aws_key


def upload_clinical_data_file(
    client,
    header_admin,
    header,
    project_fields,
    dataset_fields,
    ds_private=True,
):

    # TODO
    # below is qute similar to upload_data_policy_file
    # better put this two in a function

    ds_id = str(uuid.uuid4())
    file_signer_suffix = "/files?to_sign=POST"
    kc_group = "3tr"
    file_name = "clinicalData.csv"

    sign_url(
        client,
        header_admin,
        header,
        project_fields,
        dataset_fields,
        file_signer_suffix,
        file_name,
        kc_group=kc_group,
        dataset_id=ds_id,
        ds_private=ds_private,
    )

    # /finishUpload is called
    aws_key = f"{kc_group}/{ds_id}/clinical/{file_name}"

    res2 = req_post(
        client,
        header,
        "datasets/extrafile/uploadfinish",
        {"aws_key": aws_key},
    )

    response2 = json.loads(res2.data.decode("utf8"))
    assert "File upload finished" in response2["message"]

    return ds_id, aws_key


def filter_by(
    col,
    val,
    client,
    header_admin,
    header,
    header_2,
    project_fields,
    dataset_fields,
    dataset_view_url_suffix,
    dataset_ids=[],
    project_ids=[],
    dataset_private=[],
    create_dataset=True,
    partial_match=False,
    expected_error=None,
    overwrite_fields=None,
):

    query = [{"id": col, "value": val}]

    if create_dataset:
        i = 0
        for head in [header, header_2]:

            project_id = str(uuid.uuid4())
            dataset_id = str(uuid.uuid4())
            private = False
            overwrite = None

            if dataset_ids:
                dataset_id = dataset_ids[i]

            if project_ids:
                project_id = project_ids[i]

            if dataset_private:
                private = dataset_private[i]

            if overwrite_fields is not None:
                overwrite = overwrite_fields[i]

            add_dataset(
                client,
                header_admin,
                head,
                project_fields,
                dataset_fields,
                project_id=project_id,
                dataset_id=dataset_id,
                private=private,
                overwrite_fields=overwrite,
            )
            i += 1

    # before filtering
    res = filter_view(
        client,
        header,
        dataset_view_url_suffix,
    )

    response = json.loads(res.data.decode("utf8"))
    assert len(response["items"]) > 0
    all_items = [item[col] for item in response["items"]]
    assert len(response["items"]) > 1
    assert len(set(all_items)) > 0

    # filtering
    if col == "owner":
        query = [{"id": "checkbox", "value": val}]

    res2 = filter_view(client, header, dataset_view_url_suffix, query)

    if expected_error:
        assert expected_error in res2["message"]
        return

    response2 = json.loads(res2.data.decode("utf8"))
    assert len(response2["items"]) > 0

    items = [item[col] for item in response2["items"]]
    if partial_match:
        assert any(val in item for item in items)
    else:
        assert {val} == set(items)


def modify_ds_data(
    client,
    header,
    header_admin,
    project_fields,
    dataset_fields,
    field,
    value,
    proj_overwrite_fields=None,
    expected_error=None,
):
    dataset_admin_view_suffix = "datasets/admin/view"
    dataset_admin_mode_suffix = "datasets/admin/update"

    project_id = str(uuid.uuid4())
    dataset_id = str(uuid.uuid4())

    add_dataset(
        client,
        header_admin,
        header,
        project_fields,
        dataset_fields,
        dataset_id=dataset_id,
        project_id=project_id,
        proj_overwrite_fields=proj_overwrite_fields,
    )

    res = filter_view(
        client,
        header_admin,
        dataset_admin_view_suffix,
        [{"id": "project_id", "value": project_id}],
    )

    response = json.loads(res.data.decode("utf8"))
    assert len(response["items"]) > 0

    # FIXME
    # if in admin mode
    # dataset_admin_view_suffix endpoint
    # should return the id (int) of the dataset
    # and not the dataset_id (=string)

    ds_ids = [response["items"][0]["id"]]

    res = req_post(
        client,
        header_admin,
        dataset_admin_mode_suffix,
        {"dbRowIds": ds_ids, "field": field, "value": value},
    )

    try:
        res = json.loads(res.data.decode("utf8"))
    except Exception:
        pass

    if expected_error:
        assert expected_error in res["message"]
        return

    assert res["message"] == "dataset updated"

    res2 = filter_view(
        client,
        header_admin,
        dataset_admin_view_suffix,
        [{"id": "project_id", "value": project_id}],
    )

    response2 = json.loads(res2.data.decode("utf8"))
    assert response2["items"][0][field] == value

    # TODO
    # get the old value
    # and compare it with the new value
    # assert old val != new val


class MyTester:
    """
    example how to pass a parameter to a fixture function
    see:
    https://stackoverflow.com/questions/18011902/pass-a-parameter-to-a-fixture-function
    uses True as dummy param
    """

    # TODO
    # write all tests a self contained
    # use pytest.mark.parametrize to pass parameters
    # like share/unshare groups etc.

    def __init__(self, dummy_param):
        self.param = dummy_param

    def dothis(self, client, header, project, dataset, groups, view_query):
        assert self.param

        file_view_url_suffix = "files/all"
        # dataset_view_url_suffix = "datasets/all"
        # dataset_add_group_url_suffix = "datasets?arg=addGroup"
        dataset_remove_group_url_suffix = "datasets?arg=removeGroup"

        res = req_put(
            client,
            header,
            dataset_remove_group_url_suffix,
            [f"project={project}", f"dataset={dataset}", f"group={groups}"],
        )
        response = json.loads(res.data.decode("utf8"))
        assert "groups updated" in response["message"]

        # verify file view
        res2 = req_post(
            client,
            header,
            file_view_url_suffix,
            view_query,
        )
        response2 = json.loads(res2.data.decode("utf8"))
        assert "None" == response2["items"][0]["shared_with"]


def read_test_file(fn):
    script_dir = Path(__file__)
    test_files_path = f"{script_dir.parents[1]}/data/{fn}"

    def is_gzipped(path):
        with open(path, "rb") as f:
            return f.read(2) == b"\x1f\x8b"

    try:
        open_fn = gzip.open if is_gzipped(test_files_path) else open
        with open_fn(test_files_path, "rb") as fh:
            return BytesIO(fh.read())
    except FileNotFoundError:
        print(f"file {test_files_path} does not exist")


# def upload_files(meta_data, client, header):

#     data = {"file": []}
#     for meta in meta_data:
#         for file_name in meta["File"]:
#             test_file = read_test_file(file_name)
#             data["file"].append(
#                 FileStorage(
#                     stream=test_file, filename=file_name, content_type="text"
#                 )
#             ),

#     data["metaData"] = json.dumps(meta_data)

#     res = req_post_file(client, header, data)
#     try:
#         response = json.loads(res.data.decode("utf8"))
#     except AttributeError as e:
#         print(e)
#         # error handler already returns a json
#         return res, res["status_code"]

#     return response, res.status_code
