import sys
from os import path
import pytest
from io import BytesIO

# sys.path.append(path.join(path.dirname(__file__), "server"))
from server.app import app
from server.model import db

from server.config.config_test import DevelopmentConfig
from server.config.config_3tr_client import ClientConfig

sys.path.append(path.join(path.dirname(__file__), "helpers"))
from utils import get_header, MyTester  # noqa: E402

FAKE_PUBLIC_KEY = "-----BEGIN PUBLIC KEY-----\nMIIB-----END PUBLIC KEY-----\n"
FAKE_PAYLOAD = {
    "iat": 1619824766,
    "preferred_username": "test",
    "group": ["cnag"],
}


@pytest.fixture()
def fake_public_key():
    return FAKE_PUBLIC_KEY


@pytest.fixture()
def fake_payload():
    return FAKE_PAYLOAD


@pytest.fixture(scope="module")
def header():
    return get_header("test", DevelopmentConfig)


@pytest.fixture(scope="module")
def header_2():
    return get_header("test2", DevelopmentConfig)


@pytest.fixture(scope="module")
def header_3():
    return get_header("test3", DevelopmentConfig)


@pytest.fixture(scope="module")
def header_4():
    return get_header("test4", DevelopmentConfig)


@pytest.fixture(scope="module")
def header_5():
    return get_header("test5", DevelopmentConfig)


@pytest.fixture(scope="module")
def header_6():
    return get_header("test6", DevelopmentConfig)


@pytest.fixture(scope="module")
def header_admin():
    return get_header("admin", DevelopmentConfig)


@pytest.fixture(scope="module")
def client(request):
    app.testing = True  # propagate exceptions to the test client
    # ! overwrite app.config set in run.py
    # ! not working as expected
    # it is overwriting but regarding the
    # the IDRSA too late because it still takes the
    # IDRSA from config.py and not from config_test.py
    # So before this is fixed the tests cannot be run on the master branch
    # maybe it is a race condition
    app.config.from_object(DevelopmentConfig)
    test_client = app.test_client()

    db.create_all()

    def teardown():
        db.drop_all()
        db.session.remove()

    request.addfinalizer(teardown)
    return test_client


def mock_client(mocker):
    app.testing = True  # propagate exceptions to the test client
    app.config.from_object(DevelopmentConfig)
    mocker.patch(
        "server.security.get_public_key", return_value=FAKE_PUBLIC_KEY
    )
    mocker.patch("jwt.decode", return_value=FAKE_PAYLOAD)
    yield app.test_client()


@pytest.fixture(params=["mock_client", "client"])
def test_client(request):
    client_fixture = request.getfixturevalue(request.param)
    yield client_fixture


@pytest.fixture()
def project_fields():
    return [
        ("id", "str"),
        ("name", "str"),
        ("description", "str"),
        ("owners", "list(str)"),
        ("datasetVisibilityDefault", "str"),
        ("datasetVisibilityChangeable", "bool"),
        ("fileDlAllowed", "bool"),
        ("diseases", "list(str)"),
        ("logoUrl", "str"),
    ]


@pytest.fixture()
def dataset_fields_old():
    return [
        "id",
        "name",
        "description",
        "tags",
        "responsible_partner",
        "disease",
        "treatment",
        "category",
        "visibility",
    ]


@pytest.fixture()
def dataset_fields():

    # TODO
    # return all the fields
    # similar to fields below

    # fields = ClientConfig.SUBMIT_DATASETS_HEADERS

    return [
        "id",
        "project_id",
        "name",
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
        "visibility",
    ]


@pytest.fixture()
def datasets_fields_mandatory_and_string():

    fields = ClientConfig.SUBMIT_DATASETS_HEADERS

    mandatory_fields = [
        field["id"]
        for field in fields
        if field["mandatory"] is True and field["inputType"] == "text"
    ]

    mandatory_fields.append("project_id")

    for field in ["samplesCount", "featuresCount"]:
        mandatory_fields.remove(field)

    return mandatory_fields


@pytest.fixture()
def file_fields():
    return ["projectId", "DatasetID", "fileName", "Comment"]


@pytest.fixture()
def view_query():
    return {"page": 1, "pageSize": 100, "sorted": None, "filtered": None}


@pytest.fixture()
def empty_file():
    script_dir = path.dirname(__file__)
    with open(path.join(script_dir, "data/emptyfile.csv"), "rb") as fh:
        return BytesIO(fh.read())


@pytest.fixture
def tester(request):
    """Create tester object"""
    return MyTester(request.param)


@pytest.fixture
def db_uri():
    return DevelopmentConfig.SQLALCHEMY_DATABASE_URI
