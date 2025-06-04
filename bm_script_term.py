import requests
from uuid import uuid4
from lib import (
    run_timed_method, json_bytes, keycloak_login, add_project, project_fields, filter_view,
    django_logged_session
)


"""Benchmark script with terminal output"""


# Session config
N = 1
THREADED = True
session_id = str(uuid4())[:4]


print(f"API Benchmark session: {session_id} - THREADED : {THREADED}")


# Servers
DJANGO_SRV = "http://127.0.0.1:8000"
FASTAPI_SRV = "http://0.0.0.0:8002"
ODMV1_SRV = "http://0.0.0.0:8003"
ODMV2_SRV = "http://0.0.0.0:8001"


# Login credentials
KC_USER_ADMIN_USERNAME = 'admin'
KC_USER_ADMIN_PASSWORD = '12345'
DJANGO_USER='admin'
DJANGO_PASS='1234'


# Payloads : one project
SHORT_NAME = 'bla'
create_payload = {
    'long_name': 'bla bla',
    'description': 'test',
    'created_at': '2025-05-21T00:00',
    'logo_url': 'https://cdn.pixabay.com/photo/2016/11/07/13/04/yoga-1805784_960_720.png',

}


bin_create_payload = create_payload.copy()
del bin_create_payload['created_at']

# Django ------------------------

print("-- Django REST")

with django_logged_session(url=DJANGO_SRV + '/admin/login', username=DJANGO_USER, password=DJANGO_PASS) as s:
    def django_post(i):
        create_payload['short_name'] = f"{SHORT_NAME}_{session_id}_{i}"
        new = s.post(DJANGO_SRV + '/customer/create/', data=create_payload)
        assert new.status_code == 201

    def django_get(_):
        ls = s.get(DJANGO_SRV + '/customer/' + f"?short_name=*{session_id}*")
        assert ls.status_code == 200


    print(f"\tCreating {N} projects : ", run_timed_method(django_post, N, THREADED))
    print(f"\tListing projects {N} times : ", run_timed_method(django_get, N, THREADED))
    # ----------------

# FastAPI ------------------------

print("-- FastApi")


FA_TOKEN = keycloak_login(f'{FASTAPI_SRV}/login', KC_USER_ADMIN_USERNAME, KC_USER_ADMIN_PASSWORD)
FA_ADMIN_HEADER = {'Authorization': f'Bearer {FA_TOKEN}'}


fa_bin_payload = json_bytes(bin_create_payload.copy())


def fastapi_post(i):
    fa_bin_payload = fa_bin_payload[:-1] + b', "short_name":"' + bytes(f"{SHORT_NAME}_{session_id}_{i}", 'utf-8') + b'"}'
    new = requests.post(FASTAPI_SRV + '/projects', data=fa_bin_payload, headers=FA_ADMIN_HEADER, verify=False)
    assert new.status_code == 201


def fastapi_get(_):
    ls = requests.get(FASTAPI_SRV + '/projects' + f"?short_name=*{session_id}*", headers=FA_ADMIN_HEADER, verify=False)
    assert ls.status_code == 200


print(f"\tCreating {N} projects : ", run_timed_method(fastapi_post, N, THREADED))
print(f"\tListing projects {N} times : ", run_timed_method(fastapi_get, N, THREADED))


# OMICSDM V1 ------------------------
print("-- OmicsDM V1")


def odmv1_post(i):
    project_id = f"{SHORT_NAME}_{session_id}_{i}"
    add_project(
        url=ODMV1_SRV + "/api/",
        header=FA_ADMIN_HEADER,
        project_fields=project_fields(),
        projects_create_url_suffix="projects/create",
        payload={
            "id": project_id,
            "owners": "3tr",
            "name": create_payload['long_name'],
            "description": create_payload['description'],
            "logoUrl": create_payload['logo_url'],
            "diseases": "COPD,ASTHMA,CD,UC,MS,SLE,RA",
        }
    )


def odmv1_get(_):
    filter_view(
        url=ODMV1_SRV + "/api/",
        header=FA_ADMIN_HEADER,
        view_url_suffix="projects/admin/view", #"projects/all",
        page_size=N,
        query=[{"id": "project_id", "value": '*' + session_id + '*'}],
    )


print(f"\tCreating {N} projects : ", run_timed_method(odmv1_post, N, THREADED))
print(f"\tListing projects {N} times : ", run_timed_method(odmv1_get, N, THREADED))

# OMICSDM V2 ------------------------

print("-- BioDM (OmicsDM v2)")


ODM_TOKEN = keycloak_login(f'{ODMV2_SRV}/login', KC_USER_ADMIN_USERNAME, KC_USER_ADMIN_PASSWORD)
ODM_ADMIN_HEADER = {'Authorization': f'Bearer {ODM_TOKEN}'}


odm_bin_payload = json_bytes(bin_create_payload.copy())


def odmv2_post(i):
    odm_bin_payload = odm_bin_payload[:-1] + b', "short_name":"' + bytes(f"{SHORT_NAME}_{session_id}_{i}", 'utf-8') + b'"}'
    new = requests.post(f"{ODMV2_SRV}/projects", data=odm_bin_payload, headers=ODM_ADMIN_HEADER, verify=False)
    assert new.status_code == 201


def odmv2_get(_):
    ls = requests.get(f"{ODMV2_SRV}/projects" + f"?short_name=*{session_id}*", headers=ODM_ADMIN_HEADER, verify=False)
    assert ls.status_code == 200


print(f"\tCreating {N} projects : ", run_timed_method(odmv2_post, N, THREADED))
print(f"\tListing projects {N} times : ", run_timed_method(odmv2_get, N, THREADED))


pass # bp
