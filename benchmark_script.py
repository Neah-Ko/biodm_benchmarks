import requests
from bs4 import BeautifulSoup
import time
import json
from typing import Dict, Any
from uuid import uuid4


# Session config
N = 1
session_id = str(uuid4())[:4]


# Servers
ODMV1_SRV = "http://0.0.0.0:8003"
ODMV2_SRV = "http://0.0.0.0:8001"
DJANGO_SRV = "http://0.0.0.0:8000"
FASTAPI_SRV = "http://0.0.0.0:8002"


# KC creds
KC_USER_ADMIN_USERNAME = 'admin'
KC_USER_ADMIN_PASSWORD = '12345'


# Helper functions
def json_bytes(d: Dict[Any, Any]) -> bytes:
    """Encodes python Dict as utf-8 bytes."""
    return json.dumps(d).encode('utf-8')


def keycloak_login(login_url, username, password, access_only=True):
    # Get and Parse form with bs
    # Courtesy of: https://www.pythonrequests.com/python-requests-keycloak-login/
    with requests.sessions.Session() as s:
        login_url = s.get(login_url)
        if login_url.text.startswith('<!DOCTYPE html>'):
            form_response = login_url
        else:
            form_response = s.get(login_url.text)

        soup = BeautifulSoup(form_response.content, 'html.parser')
        form = soup.find('form')
        action = form['action']
        other_fields = {
            i['name']: i.get('value', '')
            for i in form.find_all('input', {'type': 'hidden'})
        }
        response = s.post(action, data={
            'username': username,
            'password': password,
            **other_fields,
        }, allow_redirects=True)

        assert response.status_code == 200

        token = json.loads(response.text)
        if access_only:
            return token['access_token']
        return token


# Django ------------------------

print("-- Django REST")

LOGIN_URL='http://127.0.0.1:8000/admin/login/'
USER='admin'
PASS='1234'
BASE_URL = 'http://127.0.0.1:8000/customer/'

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
}

# Request page
response = requests.get(LOGIN_URL, headers=headers, verify=False)

# Extract CRSF token
soup = BeautifulSoup(response.text, 'html.parser')
crsf = soup.find('input',attrs = {'name':'csrfmiddlewaretoken'})['value']

# Build payload
payload = {
    'username': USER,
    'password': PASS,
    'csrfmiddlewaretoken': crsf,
    'next': '/admin/'
}

# Set headers
headers['Cookie'] = response.headers['Set-Cookie'].split(';')[0]
headers['Content-Type'] = 'application/x-www-form-urlencoded'

# Define one project
SHORT_NAME = 'bla'
create_payload = {
    'csrfmiddlewaretoken': crsf,
    'long_name': 'bla bla',
    'description': 'test',
    'created_at': '2025-05-21T00:00',
    'logo_url': 'https://cdn.pixabay.com/photo/2016/11/07/13/04/yoga-1805784_960_720.png',

}

# Login and check Django
with requests.sessions.Session() as s:
    login_response = s.post(LOGIN_URL, data=payload, headers=headers, verify=False)
    login_soup = BeautifulSoup(login_response.content, 'html.parser')
    # assert login_soup.find('form', attrs = {'id': 'logout-form'}) is not None

    # DoStuff
    # ----------------
    start = time.time()
    for i in range(N):
        create_payload['short_name'] = f"{SHORT_NAME}_{session_id}_{i}"
        new = s.post(BASE_URL + 'create/', data=create_payload, headers=headers, verify=False)
        assert new.status_code == 201
    end = time.time()
    print(f"\tCreating {N} projects : ", end - start)

    start = time.time()
    for i in range(N):
        ls = s.get(BASE_URL + f"?short_name=*{session_id}*", headers=headers, verify=False)
        assert ls.status_code == 200
        pass
    end = time.time()
    print(f"\tListing projects {N} times : ", end - start)
    # ----------------

# FastAPI ------------------------

print("-- FastApi")

SRV_FASTAPI = 'http://0.0.0.0:8002'
FA_TOKEN = keycloak_login(f'{SRV_FASTAPI}/login', KC_USER_ADMIN_USERNAME, KC_USER_ADMIN_PASSWORD)
FA_ADMIN_HEADER = {'Authorization': f'Bearer {FA_TOKEN}'}

fa_create_payload = create_payload.copy()
del fa_create_payload['csrfmiddlewaretoken']
del fa_create_payload['created_at']
del fa_create_payload['short_name']
fa_create_payload = json_bytes(fa_create_payload)


start = time.time()
for i in range(N):
    fa_create_payload = fa_create_payload[:-1] + b', "short_name":"' + bytes(f"{SHORT_NAME}_{session_id}_{i}", 'utf-8') + b'"}'
    new = requests.post(SRV_FASTAPI + '/projects', data=fa_create_payload, headers=FA_ADMIN_HEADER, verify=False) # headers=ADMIN_HEADER,
    assert new.status_code == 201
end = time.time()
print(f"\tCreating {N} projects : ", end - start)


start = time.time()
for i in range(N):
    ls = requests.get(SRV_FASTAPI + '/projects' + f"?short_name=*{session_id}*", headers=FA_ADMIN_HEADER, verify=False) # headers=ADMIN_HEADER,
    assert ls.status_code == 200
    pass
end = time.time()
print(f"\tListing projects {N} times : ", end - start)



# OMICSDM V1 ------------------------
# Taken from https://github.com/bag-cnag/omicsdm_server/
#     -> tests

print("-- OmicsDM V1")

SRV_ODM_V1 = "http://0.0.0.0:8003/api/"

def exception_handler(func):
    def inner_function(*args, **kwargs):

        res = func(*args, **kwargs)
        if res.status_code in [200, 400, 404, 405]:
            return res

        return json.loads(res.data.decode("utf8"))

    return inner_function

import requests

@exception_handler
def req_get(client, header, url_suffix):
    return client.get(SRV_ODM_V1 + url_suffix, headers=header)


@exception_handler
def req_post(client, header, url_suffix, data):
    return client.post(
        SRV_ODM_V1 + url_suffix, headers=header, data=json.dumps(data)
    )

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
            "name": create_payload['long_name'],
            "description": create_payload['description'],
            "logoUrl": create_payload['logo_url'],
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
        response = json.loads(res.text)

        if projects_create_url_suffix == "projects/create":
            pass
            # assert "project inserted" in response["message"]
        else:
            return response

    except AssertionError:
        raise AssertionError(res.data.decode("utf8"))

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

def filter_view(client, header, view_url_suffix, query=None):
    res = req_post(
        client,
        header,
        view_url_suffix,
        {
            "page": 1,
            "pageSize": N,
            "sorted": None,
            "filtered": query,
        },
    )
    return res



start = time.time()
for i in range(N):
    project_id = f"{SHORT_NAME}_{session_id}_{i}"
    add_project(
        client=requests,
        header=FA_ADMIN_HEADER,
        project_id=project_id,
        project_fields=project_fields(),
        projects_create_url_suffix="projects/create",
        submit=True,
        overwrite_fields=None,
        expected_error=None,
        field_to_be_deleted=None,
    )
end = time.time()
print(f"\tCreating {N} projects : ", end - start)

start = time.time()
for i in range(N):
    res = filter_view(
        client=requests,
        header=FA_ADMIN_HEADER,
        view_url_suffix="projects/admin/view", #"projects/all",
        query=[{"id": "project_id", "value": '*' + session_id + '*'}],
    )
    pass
end = time.time()
print(f"\tListing projects {N} times : ", end - start)

# OMICSDM V2 ------------------------

print("-- BioDM (OmicsDM v2)")

SRV_URL = 'http://0.0.0.0:8001'
ODM_PROJECTS_URL = f"{SRV_URL}/projects"
ODM_TOKEN = keycloak_login(f'{SRV_URL}/login', KC_USER_ADMIN_USERNAME, KC_USER_ADMIN_PASSWORD)
ODM_ADMIN_HEADER = {'Authorization': f'Bearer {ODM_TOKEN}'}

odm_create_payload = create_payload.copy()
del odm_create_payload['csrfmiddlewaretoken']
del odm_create_payload['created_at']
del odm_create_payload['short_name']
odm_create_payload = json_bytes(odm_create_payload)

start = time.time()
for i in range(N):
    odm_create_payload = odm_create_payload[:-1] + b', "short_name":"' + bytes(f"{SHORT_NAME}_{session_id}_{i}", 'utf-8') + b'"}'
    new = requests.post(ODM_PROJECTS_URL, data=odm_create_payload, headers=ODM_ADMIN_HEADER, verify=False)
    assert new.status_code == 201
end = time.time()
print(f"\tCreating {N} projects : ", end - start)


start = time.time()
for i in range(N):
    ls = requests.get(ODM_PROJECTS_URL + f"?short_name=*{session_id}*", headers=ODM_ADMIN_HEADER, verify=False)
    assert ls.status_code == 200
end = time.time()
print(f"\tListing projects {N} times : ", end - start)


pass # bp
