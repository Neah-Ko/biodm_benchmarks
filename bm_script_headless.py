import requests
from statistics import fmean
from uuid import uuid4
from lib import (
    run_timed_method, json_bytes, add_project, project_fields, filter_view,
    django_logged_session, keycloak_token_header
)
import sys
import ast


"""Benchmark script with csv/matplotlib output and averaged runs"""

M = 3 # Number of runs to average on.
threaded = True

# -------------

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
fa_bin_payload = json_bytes(bin_create_payload.copy())
odm_bin_payload = json_bytes(bin_create_payload.copy())

# ------- SETUP ------------

# 1 - 2000 with steps 100
X = [i-1 for i in list(range(1, 2002, 100))]
X[0] = 1

# 1-100 with steps 10
X = [i-1 for i in list(range(1, 102, 10))]
X[0] = 1

# Script parameters
if len(sys.argv) > 2:
    X = ast.literal_eval(sys.argv[2])

# --------------------------

print("-------------------")
print("-- benchmark run --")
print("X : ", X)

if len(sys.argv) > 1:
    print("Saving results to: ", sys.argv[1])
    try:
        with open(sys.argv[1], "w+") as f:
            f.write("# -------------------\n")
            f.write("# -- benchmark run --\n")
            f.write(f"X={X}\n")
            f.write("# -------------------\n")
    except Exception as e:
        print(f"File error : {e}")

print("-------------------")


# name gen helpers
short_name = lambda sid, m, i: f"{SHORT_NAME}_{sid}_{m}_{i}"
short_name_query = lambda sid, m: f"{sid}_{m}"


for threaded in (False,):# (True, False):
    # Results lists
    Y_django_cr = []
    Y_django_ls = []

    Y_fastapi_cr = []
    Y_fastapi_ls = []

    Y_odmv1_cr = []
    Y_odmv1_ls = []

    Y_omdv2_cr = []
    Y_omdv2_ls = []

    for n in X:
        session_id = str(uuid4())[:8]

        # Temp Results
        y_avg_django_cr = []
        y_avg_django_ls = []

        y_avg_fastapi_cr = []
        y_avg_fastapi_ls = []

        y_avg_odmv1_cr = []
        y_avg_odmv1_ls = []

        y_avg_odmv2_cr = []
        y_avg_odmv2_ls = []

        for m in range(M):
            # Django
            with django_logged_session(url=DJANGO_SRV + '/admin/login', username=DJANGO_USER, password=DJANGO_PASS) as s:
                def django_post(i):
                    create_payload['short_name'] = short_name(session_id, m, i)
                    new = s.post(DJANGO_SRV + '/customer/create/', data=create_payload)
                    assert new.status_code == 201

                def django_get(_):
                    ls = s.get(DJANGO_SRV + '/customer/' + f"?short_name=*{short_name_query(session_id, m)}*")
                    assert ls.status_code == 200

            y_avg_django_cr.append(run_timed_method(django_post, n, threaded))
            y_avg_django_ls.append(run_timed_method(django_get, n, threaded))

            # Fastapi
            KC_ADMIN_HEADER = keycloak_token_header(f'{FASTAPI_SRV}/login', KC_USER_ADMIN_USERNAME, KC_USER_ADMIN_PASSWORD)

            def fastapi_post(i):
                global fa_bin_payload
                fa_bin_payload = fa_bin_payload[:-1] + b', "short_name":"' + bytes(short_name(session_id, m, i), 'utf-8') + b'"}'
                new = requests.post(FASTAPI_SRV + '/projects', data=fa_bin_payload, headers=KC_ADMIN_HEADER, verify=False)
                assert new.status_code == 201

            def fastapi_get(_):
                ls = requests.get(FASTAPI_SRV + '/projects' + f"?short_name=*{short_name_query(session_id, m)}*", headers=KC_ADMIN_HEADER, verify=False)
                assert ls.status_code == 200

            y_avg_fastapi_cr.append(run_timed_method(fastapi_post, n, threaded))
            y_avg_fastapi_ls.append(run_timed_method(fastapi_get, n, threaded))

            # Odmv1
            KC_ADMIN_HEADER = keycloak_token_header(f'{FASTAPI_SRV}/login', KC_USER_ADMIN_USERNAME, KC_USER_ADMIN_PASSWORD)

            def odmv1_post(i):
                add_project(
                    url=ODMV1_SRV + "/api/",
                    header=KC_ADMIN_HEADER,
                    project_fields=project_fields(),
                    projects_create_url_suffix="projects/create",
                    payload={
                        "id": short_name(session_id, m, i),
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
                    header=KC_ADMIN_HEADER,
                    view_url_suffix="projects/admin/view", #"projects/all",
                    page_size=n,
                    query=[{"id": "project_id", "value": '*' + short_name_query(session_id, m) + '*'}],
                )
            
            y_avg_odmv1_cr.append(run_timed_method(odmv1_post, n, threaded))
            y_avg_odmv1_ls.append(run_timed_method(odmv1_get, n, threaded))

            # OdmV2
            KC_ADMIN_HEADER = keycloak_token_header(f'{FASTAPI_SRV}/login', KC_USER_ADMIN_USERNAME, KC_USER_ADMIN_PASSWORD)

            def odmv2_post(i):
                global odm_bin_payload
                odm_bin_payload = odm_bin_payload[:-1] + b', "short_name":"' + bytes(short_name(session_id, m, i), 'utf-8') + b'"}'
                new = requests.post(f"{ODMV2_SRV}/projects", data=odm_bin_payload, headers=KC_ADMIN_HEADER, verify=False)
                assert new.status_code == 201

            def odmv2_get(_):
                ls = requests.get(f"{ODMV2_SRV}/projects" + f"?short_name=*{short_name_query(session_id, m)}*", headers=KC_ADMIN_HEADER, verify=False)
                assert ls.status_code == 200

            y_avg_odmv2_cr.append(run_timed_method(odmv2_post, n, threaded))
            y_avg_odmv2_ls.append(run_timed_method(odmv2_get, n, threaded))


        Y_django_cr.append(fmean(y_avg_django_cr))
        Y_django_ls.append(fmean(y_avg_django_ls))
        Y_fastapi_cr.append(fmean(y_avg_fastapi_cr))
        Y_fastapi_ls.append(fmean(y_avg_fastapi_ls))
        Y_odmv1_cr.append(fmean(y_avg_odmv1_cr))
        Y_odmv1_ls.append(fmean(y_avg_odmv1_ls))
        Y_omdv2_cr.append(fmean(y_avg_odmv2_cr))
        Y_omdv2_ls.append(fmean(y_avg_odmv2_ls))

    if len(sys.argv) > 1:
        try:
            with open(sys.argv[1], "a") as f:
                suffix = ""
                if threaded:
                    suffix = "_p"
                    f.write(f"-- Mode : parallel --\n")
                else:
                    suffix = "_s"
                    f.write(f"-- Mode : sequencial --\n")
                suffix = "_p" if threaded else "_s"
                f.write(f"# ----- POST\n")
                f.write(f"Y_django_cr{suffix}={Y_django_cr}\n")
                f.write(f"Y_fastapi_cr{suffix}={Y_fastapi_cr}\n")
                f.write(f"Y_odmv1_cr{suffix}={Y_odmv1_cr}\n")
                f.write(f"Y_odmv2_cr{suffix}={Y_omdv2_cr}\n")
                f.write(f"# ---- GET\n")
                f.write(f"Y_django_ls{suffix}={Y_django_ls}\n")
                f.write(f"Y_fastapi_ls{suffix}={Y_fastapi_ls}\n")
                f.write(f"Y_odmv1_ls{suffix}={Y_odmv1_ls}\n")
                f.write(f"Y_odmv2_ls{suffix}={Y_omdv2_ls}\n")
                f.write(f"# ---------------\n")
        except Exception as e:
            print(f"File error : {e}")
    else:
        print("-- Mode : ", "parallel" if threaded else "sequencial", " --")
        print("----- POST")
        print("Y django : ", Y_django_cr)
        print("Y fastapi : ", Y_fastapi_cr)
        print("Y odmv1 : ", Y_odmv1_cr)
        print("Y odmv2 : ", Y_omdv2_cr)
        print("---- GET")
        print("Y django : ", Y_django_ls)
        print("Y fastapi : ", Y_fastapi_ls)
        print("Y odmv1 : ", Y_odmv1_ls)
        print("Y odmv2 : ", Y_omdv2_ls)
        print("---------------")
print("Done.")
