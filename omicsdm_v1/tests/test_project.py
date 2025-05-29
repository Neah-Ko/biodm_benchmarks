import json
import uuid

from utils import req_get, req_post, add_project, filter_view, del_from_db

# TODO
# add test for empty form submission
# at the moment this runs through in the frontend -> error should be thrown

projects_create_url_suffix = "projects/create"
project_validate_create_url_suffix = "projects/validate"

projects_view_url_suffix = "projects/all"
projects_view2_url_suffix = "projects/admin/view"
projects_modify_url_suffix = "projects/admin/update"
projects_submission_cols_suffix = "projects/submissioncols"


# TODO
# make sure that the disease column is filled

# TODO
# replace json.loads with res.json["message"]


class TestProjectCreate:
    def test_get_project_submission_cols(self, client, header_admin):

        res = req_get(client, header_admin, projects_submission_cols_suffix)
        assert "message" in res.json[0]

        cols = res.json[0]["message"]
        assert len(cols) == 9

        assert [
            "description",
            "id",
            "inputType",
            "mandatory",
            "selection",
            "title",
        ] == list(cols[0].keys())

        assert cols[0]["id"] == "id"
        assert type(cols[0]["mandatory"]) == bool
        assert type(cols[0]["selection"]) == list

    def test_datasets_admin_get_cols_not_admin(self, client, header):

        # TODO
        # figure out why that is a post request
        res = req_get(client, header, "projects/submissioncols")
        response = json.loads(res.data.decode("utf8"))

        assert "Only admin users can create projects" == response["message"]

    def test_projects_create(self, client, header_admin, project_fields):

        project_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            project_id,
            project_fields,
            projects_create_url_suffix,
        )

    def test_projects_duplicate_ids(
        self, client, header_admin, project_fields
    ):

        project_id = str(uuid.uuid4())

        proj_data = add_project(
            client,
            header_admin,
            project_id,
            project_fields,
            projects_create_url_suffix,
            submit=False,
        )
        data = [proj_data] * 2

        res = req_post(client, header_admin, projects_create_url_suffix, data)
        assert "duplicated project_ids not allowed" in res["message"]

    def test_project_already_exist(self, client, header_admin, project_fields):

        project_id = str(uuid.uuid4())

        for error in [None, "project_id already exists"]:
            add_project(
                client,
                header_admin,
                project_id,
                project_fields,
                projects_create_url_suffix,
                expected_error=error,
            )

    def test_project_kc_group_not_valid(
        self, client, header_admin, project_fields
    ):

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
            overwrite_fields={"owners": "ownerX"},
            expected_error="ownerX is not a valid group",
        )

    def test_project_user_is_not_in_admin_group(
        self, client, header, project_fields
    ):
        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header,
            proj_id,
            project_fields,
            projects_create_url_suffix,
            expected_error="Only admin users can create a project",
        )

    def test_project_multiple_owner_groups(
        self, client, header_admin, project_fields
    ):

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
            overwrite_fields={"owners": "3tr,cnag"},
        )

    def test_project_all_kc_groups_are_owner(
        self, client, header_admin, project_fields
    ):

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
            overwrite_fields={"owners": "ALL"},
        )

        res = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )

        response = json.loads(res.data)

        assert "items" in response

        projects = response["items"]
        assert len(projects) == 1

        # TODO
        # the number of groups should not be hardcoded
        # but taken by querying the keycloak server
        assert len(projects[0]["owners"].split(",")) == 20

    def test_projects_payload_not_a_list(self, client, header_admin):

        response = req_post(
            client, header_admin, projects_create_url_suffix, {"id": "test"}
        )

        assert 405 == response["status_code"]
        assert "payload is not " in response["message"]

    def test_projects_create_wrong_fields(
        self, client, header_admin, project_fields
    ):

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
            overwrite_fields={"field1": "test1", "field2": "test2"},
            expected_error="Additional properties are not allowed",
        )

    def test_projects_create_id_empty(
        self, client, header_admin, project_fields
    ):
        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
            expected_error="an empty string not accepted",
            overwrite_fields={"id": ""},
        )

    def test_projects_create_missing_field(
        self, client, header_admin, project_fields
    ):

        for field, _ in project_fields:
            proj_id = str(uuid.uuid4())

            expected_error = "At least one required field is empty/unselected"

            if field == "id":
                expected_error = "id not in request data"

            add_project(
                client,
                header_admin,
                proj_id,
                project_fields,
                projects_create_url_suffix,
                expected_error=expected_error,
                field_to_be_deleted=field,
            )

    def test_projects_create_field_is_empty(
        self, client, header_admin, project_fields
    ):
        expected_err = "At least one required field is empty/unselected"

        non_mandatory_fields = ["name", "description", "logoUrl"]

        for field, data_type in project_fields:
            proj_id = str(uuid.uuid4())

            if data_type == "bool":
                continue

            if field == "id" or field in non_mandatory_fields:
                continue

            add_project(
                client,
                header_admin,
                proj_id,
                project_fields,
                projects_create_url_suffix,
                expected_error=expected_err,
                overwrite_fields={field: ""},
            )

    def test_projects_create_logoUrl_wrong_format(
        self, client, header_admin, project_fields
    ):

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
            overwrite_fields={"logoUrl": "www.test.com"},
            expected_error="does not match '^(http|https)://.*$'",
        )

    def test_projects_create_wrong_enums(
        self, client, header_admin, project_fields
    ):

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
            overwrite_fields={"datasetVisibilityDefault": "public"},
            expected_error=(
                "'public' is not one of ['private', 'visible to all']"
            ),
        )

    def test_project_create_validate_success(
        self, client, header_admin, project_fields
    ):

        # scenario: validate that the project can be created
        # this will not add it to the db

        project_id = str(uuid.uuid4())

        res = add_project(
            client,
            header_admin,
            project_id,
            project_fields,
            project_validate_create_url_suffix,
        )

        assert "projects can be inserted" == res


class TestProjectList:
    # TODO
    # test missing to make sure that only the projects are shown
    # in which the user is owner

    def test_projects_list(
        self, client, header, header_admin, project_fields, view_query
    ):

        for _ in range(2):
            proj_id = str(uuid.uuid4())
            add_project(
                client,
                header_admin,
                proj_id,
                project_fields,
                projects_create_url_suffix,
            )

        res = req_post(client, header, projects_view_url_suffix, view_query)

        response = json.loads(res.data.decode("utf8"))
        assert len(response["projects"]) > 1

    def test_project_list_group_not_exist(self, client, header_5, db_uri):

        # test only works if group5 is not in the database
        cmd = "DELETE FROM public.group WHERE kc_groupname='group5'"
        del_from_db(db_uri, cmd)

        data = {"dataset_id": ""}
        res = req_post(client, header_5, projects_view_url_suffix, data)
        response = json.loads(res.data.decode("utf8"))

        assert len(response["projects"]) == 0


class TestProjectView:
    # TODO
    # test view_projects_extra_cols_null
    # is not yet implemented

    def test_datasets_admin_get_cols(self, client, header_admin):

        # TODO
        # figure out why that is a post request
        res = req_post(client, header_admin, "projects/adminviewcols", {})
        response = json.loads(res.data.decode("utf8"))

        assert "headers" in response[0]
        assert 10 == len(response[0]["headers"])

    def test_datasets_admin_get_cols_not_admin(self, client, header):

        # TODO
        # figure out why that is a post request
        res = req_post(client, header, "projects/adminviewcols", {})
        response = json.loads(res.data.decode("utf8"))

        assert "Only admin users can view the projects" == response["message"]

    def test_view_projects(
        self, client, header_admin, project_fields, view_query
    ):

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
        )

        res = req_post(
            client, header_admin, projects_view2_url_suffix, view_query
        )
        response = json.loads(res.data.decode("utf8"))

        assert len(response["items"]) > 0

    def test_view_projects_extra_cols_null(
        self, client, header_admin, project_fields
    ):
        #     proj_id = str(uuid.uuid4())

        #     data = add_project(
        #         client,
        #         header_admin,
        #         proj_id,
        #         project_fields,
        #         projects_create_url_suffix,
        #         submit=False,
        #     )

        #     # TODO
        #     # try if extra_cols can be set to null

        #     # not working when trying to create a new project
        #     # so maybe they need to be set to null in the database
        #     # with an extra sqlalchemy command

        #     # not sure if this is possible from a pytest test
        #     # or if it has to be done somewhere else
        #     # using raw SQL ?

        #     data["logoUrl"] = None

        #     res = req_post(
        #         client, header_admin, projects_create_url_suffix, [data]
        #     )

        #     assert res.status_code == 200

        #     res = filter_view(
        #         client,
        #         header_admin,
        #         projects_view2_url_suffix,
        #         [{"id": "project_id", "value": proj_id}],
        #     )
        #     response = json.loads(res.data.decode("utf8"))
        #     assert len(response["items"]) > 0
        pass

    def test_view_projects_no_admin(
        self, client, header, header_admin, project_fields, view_query
    ):

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
        )

        res = req_post(client, header, projects_view2_url_suffix, view_query)
        response = json.loads(res.data.decode("utf8"))

        assert "Only admin users can view projects" in response["message"]

    def test_view_projects_filter_by_proj_id(
        self, client, header_admin, project_fields, view_query
    ):

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
        )

        res = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )
        response = json.loads(res.data.decode("utf8"))

        assert len(response["items"]) == 1
        assert response["items"][0]["project_id"] == proj_id

    # def test_view_projects_filter_by_any_other_col(
    #     self, client, header_admin, project_fields, view_query
    # ):

    #     proj_id = str(uuid.uuid4())

    #     add_project(
    #         client,
    #         header_admin,
    #         proj_id,
    #         project_fields,
    #         projects_create_url_suffix,
    #         submit=True,
    #     )

    #     res = filter_view(
    #         client,
    #         header_admin,
    #         projects_view2_url_suffix,
    #         [{"id": "description", "value": "hello world"}],
    #     )
    #     response = json.loads(res.data.decode("utf8"))

    #     assert (
    #         "the selected field cannot be used for filtering"
    #         in response["message"]
    #     )


class TestProjectAdminMode:
    def test_modify_project(self, client, header_admin, project_fields):

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
        )

        # initial value for the field description
        res = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )
        response = json.loads(res.data.decode("utf8"))

        # update the value of the field description
        data = {
            "dbRowIds": [response["items"][0]["id"]],
            "field": "description",
            "value": "hello world",
        }

        res2 = req_post(client, header_admin, projects_modify_url_suffix, data)

        response2 = json.loads(res2.data.decode("utf8"))
        assert "project updated" in response2["message"]

        # view the projects to make sure the change was made
        res3 = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )
        response3 = json.loads(res3.data.decode("utf8"))

        assert "" in response["items"][0]["description"]
        assert "hello world" in response3["items"][0]["description"]

        for field in response3["items"][0]:
            assert not isinstance(response3["items"][0][field], bool)

    def test_modify_project_no_admin(
        self, client, header_admin, header, project_fields
    ):

        # TODO
        # this test cannot pass yet because the project view is missing
        # the functionality to be filtered by project_id

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
        )

        data = {
            "dbRowIds": proj_id,
            "field": "description",
            "value": "hello world",
        }

        res = req_post(client, header, projects_modify_url_suffix, data)

        response = json.loads(res.data.decode("utf8"))

        assert "Only admin users can update a project" in response["message"]

    def test_modify_project_col_cannot_be_modified(
        self, client, header_admin, project_fields
    ):

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
        )

        data = {
            "dbRowIds": [1],
            "field": "project_id",
            "value": "hello world",
        }

        res = req_post(client, header_admin, projects_modify_url_suffix, data)
        assert "'project_id' is not one of" in res["message"]

    def test_modify_project_not_exist(
        self, client, header_admin, project_fields
    ):

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
        )

        data = {
            "dbRowIds": [0],
            "field": "description",
            "value": "hello world",
        }

        res = req_post(client, header_admin, projects_modify_url_suffix, data)

        response = json.loads(res.data.decode("utf8"))

        assert "Project not found" in response["message"]

    def test_modify_project_new_url(
        self, client, header_admin, project_fields
    ):

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
        )

        # initial value for the field logo url
        res = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )
        response = json.loads(res.data.decode("utf8"))

        data = {
            "dbRowIds": [response["items"][0]["id"]],
            "field": "logo_url",
            "value": "https://www.google.com",
        }

        res2 = req_post(client, header_admin, projects_modify_url_suffix, data)
        response2 = json.loads(res2.data.decode("utf8"))
        assert "project updated" in response2["message"]

        res3 = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )

        response3 = json.loads(res3.data.decode("utf8"))

        assert "" in response["items"][0]["logo_url"]
        assert "https://www.google.com" in response3["items"][0]["logo_url"]

    def test_modify_project_new_url_wrong_format(
        self, client, header_admin, project_fields
    ):

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
        )

        res = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )
        response = json.loads(res.data.decode("utf8"))

        data = {
            "dbRowIds": [response["items"][0]["id"]],
            "field": "logo_url",
            "value": "www.google.com",
        }

        res = req_post(client, header_admin, projects_modify_url_suffix, data)
        assert "does not match '^(http|https)://.*$'" in res["message"]

    def test_modify_project_change_owner(
        self, client, header_admin, project_fields
    ):

        # scenario:
        # change the owner of a project
        # whereby the owner (=kc_groupname) is already in the group database

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
        )

        # initial value for the field logo url
        res = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )
        response = json.loads(res.data.decode("utf8"))

        data = {
            "dbRowIds": [response["items"][0]["id"]],
            "field": "owners",
            "value": "cnag",
        }

        res2 = req_post(client, header_admin, projects_modify_url_suffix, data)
        response2 = json.loads(res2.data.decode("utf8"))
        assert "project updated" in response2["message"]

        res3 = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )

        response3 = json.loads(res3.data.decode("utf8"))

        assert "3tr" in response["items"][0]["owners"]
        assert "cnag" in response3["items"][0]["owners"]

    def test_modify_project_new_owner(
        self, client, header_admin, project_fields
    ):

        # note:
        # the definition of a new owner is a kc_groupname
        # that is not yet in the database

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
        )

        # initial value for the field logo url
        res = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )
        response = json.loads(res.data.decode("utf8"))

        data = {
            "dbRowIds": [response["items"][0]["id"]],
            "field": "owners",
            "value": "granada",
        }

        res2 = req_post(client, header_admin, projects_modify_url_suffix, data)
        response2 = json.loads(res2.data.decode("utf8"))
        assert "project updated" in response2["message"]

        res3 = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )

        response3 = json.loads(res3.data.decode("utf8"))

        assert "3tr" in response["items"][0]["owners"]
        assert "granada" in response3["items"][0]["owners"]

    def test_modify_project_multiple_owners(
        self, client, header_admin, project_fields
    ):

        # sceanario:
        # one owner is new (not in the group database)
        # and one owner is already in the group database

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
        )

        # initial value for the field logo url
        res = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )
        response = json.loads(res.data.decode("utf8"))

        data = {
            "dbRowIds": [response["items"][0]["id"]],
            "field": "owners",
            "value": "granada,crg",
        }

        res2 = req_post(client, header_admin, projects_modify_url_suffix, data)
        response2 = json.loads(res2.data.decode("utf8"))
        assert "project updated" in response2["message"]

        res3 = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )

        response3 = json.loads(res3.data.decode("utf8"))

        assert "3tr" in response["items"][0]["owners"]
        assert "granada" in response3["items"][0]["owners"].split(",")
        assert "crg" in response3["items"][0]["owners"].split(",")

    def test_modify_project_owner_invalid(
        self, client, header_admin, project_fields
    ):

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
        )

        res = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )
        response = json.loads(res.data.decode("utf8"))

        data = {
            "dbRowIds": [response["items"][0]["id"]],
            "field": "owners",
            "value": "tiger",
        }

        res2 = req_post(client, header_admin, projects_modify_url_suffix, data)
        response2 = json.loads(res2.data.decode("utf8"))
        assert "at least one of the owners is invalid" in response2["message"]

    def test_modify_project_owner_valid(
        self, client, header_admin, project_fields, db_uri
    ):

        # test only works if group5 is not in the database
        cmd = "DELETE FROM public.group WHERE kc_groupname='group5'"
        del_from_db(db_uri, cmd)

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
        )

        res = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )
        response = json.loads(res.data.decode("utf8"))

        data = {
            "dbRowIds": [response["items"][0]["id"]],
            "field": "owners",
            "value": "group5",
        }

        res2 = req_post(client, header_admin, projects_modify_url_suffix, data)
        response2 = json.loads(res2.data.decode("utf8"))
        assert "project updated" in response2["message"]

    def test_modify_project_owner_group_already_exist(
        self, client, header_admin, project_fields
    ):

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
        )

        res = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )
        response = json.loads(res.data.decode("utf8"))

        data = {
            "dbRowIds": [response["items"][0]["id"]],
            "field": "owners",
            "value": "group5",
        }

        res2 = req_post(client, header_admin, projects_modify_url_suffix, data)
        response2 = json.loads(res2.data.decode("utf8"))
        assert "project updated" in response2["message"]

    def test_modify_project_new_name(
        self, client, header_admin, project_fields
    ):

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
        )

        # initial value for project name
        res = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )
        response = json.loads(res.data.decode("utf8"))

        data = {
            "dbRowIds": [response["items"][0]["id"]],
            "field": "name",
            "value": "projectY",
        }

        res2 = req_post(client, header_admin, projects_modify_url_suffix, data)
        response2 = json.loads(res2.data.decode("utf8"))
        assert "project updated" in response2["message"]

        res3 = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )

        response3 = json.loads(res3.data.decode("utf8"))

        assert response["items"][0]["name"] == "test"
        assert "projectY" in response3["items"][0]["name"]

    def test_modify_project_dataset_visibility_changeable(
        self, client, header_admin, project_fields
    ):

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
        )

        # initial value for project name
        res = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )
        response = json.loads(res.data.decode("utf8"))

        data = {
            "dbRowIds": [response["items"][0]["id"]],
            "field": "dataset_visibility_changeable",
            "value": "False",
        }

        res2 = req_post(client, header_admin, projects_modify_url_suffix, data)
        response2 = json.loads(res2.data.decode("utf8"))
        assert "project updated" in response2["message"]

        res3 = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )

        response3 = json.loads(res3.data.decode("utf8"))

        # TODO: check why this is not working

        assert response["items"][0]["dataset_visibility_changeable"] == "True"
        assert (
            response3["items"][0]["dataset_visibility_changeable"] == "False"
        )

    def test_modify_project_dataset_visibility_changeable_wrong_format(
        self, client, header_admin, project_fields
    ):

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
        )

        res = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )
        response = json.loads(res.data.decode("utf8"))

        data = {
            "dbRowIds": [response["items"][0]["id"]],
            "field": "dataset_visibility_changeable",
            "value": False,
        }

        res2 = req_post(client, header_admin, projects_modify_url_suffix, data)
        assert "False is not of type 'string'" in res2["message"]

    def test_modify_project_dataset_visibility_default(
        self, client, header_admin, project_fields
    ):

        field = "dataset_visibility_default"

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
        )

        # initial value for project name
        res = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )
        response = json.loads(res.data.decode("utf8"))

        data = {
            "dbRowIds": [response["items"][0]["id"]],
            "field": field,
            "value": "visible to all",
        }

        res2 = req_post(client, header_admin, projects_modify_url_suffix, data)
        response2 = json.loads(res2.data.decode("utf8"))
        assert "project updated" in response2["message"]

        res3 = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )

        response3 = json.loads(res3.data.decode("utf8"))

        # FIXME
        # check if the dataset visibility default is correct
        # it should not be test

        assert "private" == response["items"][0][field]
        assert "visible to all" == response3["items"][0][field]

    def test_modify_project_dataset_visibility_default_wrong_enum(
        self, client, header_admin, project_fields
    ):

        proj_id = str(uuid.uuid4())

        add_project(
            client,
            header_admin,
            proj_id,
            project_fields,
            projects_create_url_suffix,
        )

        res = filter_view(
            client,
            header_admin,
            projects_view2_url_suffix,
            [{"id": "project_id", "value": proj_id}],
        )
        response = json.loads(res.data.decode("utf8"))

        data = {
            "dbRowIds": [response["items"][0]["id"]],
            "field": "dataset_visibility_default",
            "value": "public",
        }

        res2 = req_post(client, header_admin, projects_modify_url_suffix, data)
        assert "'public' is not one of" in res2["message"]
