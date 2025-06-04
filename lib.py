import json
import time
import requests
import concurrent.futures
from contextlib import contextmanager
from typing import Dict, Any
from bs4 import BeautifulSoup


# Helper functions
def run_timed_method(method, n: int, threaded: bool):
    start = time.time()
    if threaded:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            res = [executor.submit(method, i) for i in list(range(n))]
            concurrent.futures.wait(res)
    else:
        for i in range(n):
            method(i)
    end = time.time()
    return end - start


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


def keycloak_token_header(url, username, password):
    token = keycloak_login(url, username, password)
    return {'Authorization': f'Bearer {token}'}


# Django login
@contextmanager
def django_logged_session(url, username, password):
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    }

    # Request page
    response = requests.get(url, headers=headers, verify=False)


    # Extract CRSF token
    soup = BeautifulSoup(response.text, 'html.parser')
    crsf = soup.find('input',attrs = {'name':'csrfmiddlewaretoken'})['value']


    # Build login payload
    django_login_payload = {
        'username': username,
        'password': password,
        'csrfmiddlewaretoken': crsf,
        'next': '/admin/'
    }


    # Set headers
    headers['Cookie'] = response.headers['Set-Cookie'].split(';')[0]
    headers['Content-Type'] = 'application/x-www-form-urlencoded'


    with requests.sessions.Session() as s:
        s.headers = headers
        s.verify = False
        login_response = s.post(url, data=django_login_payload)
        assert login_response.status_code == 200

        # DoStuff within the session as a logged in user
        # ----------------
        # Is session thread safe ? : https://github.com/psf/requests/issues/2766
        # Running those requests in a threaded way does improve performances.
        # The methods are not mutating the object, so it should be fine.
        # ----------------
        yield s


# OmicsDM v1 testing functions
def exception_handler(func):
    def inner_function(*args, **kwargs):

        res = func(*args, **kwargs)
        if res.status_code in [200, 400, 404, 405]:
            return res

        return json.loads(res.data.decode("utf8"))

    return inner_function


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

@exception_handler
def req_post(url, header, url_suffix, data):
    return requests.post(url + url_suffix, headers=header, data=json.dumps(data))


def filter_view(url, header, view_url_suffix, page_size, query=None):
    res = req_post(
        url,
        header,
        view_url_suffix,
        {
            "page": 1,
            "pageSize": page_size,
            "sorted": None,
            "filtered": query,
        },
    )
    assert res.status_code == 200


def add_project(
    url,
    header,
    project_fields,
    projects_create_url_suffix,
    payload,
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

    project.update(payload)

    project = {key: project[key] for key, _ in project_fields}

    if field_to_be_deleted:
        del project[field_to_be_deleted]

    if overwrite_fields:
        project.update(overwrite_fields)

    if not submit:
        return project

    res = req_post(url, header, projects_create_url_suffix, [project])

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
            assert res.status_code == 200
        else:
            return response

    except AssertionError:
        raise AssertionError(res.data.decode("utf8"))