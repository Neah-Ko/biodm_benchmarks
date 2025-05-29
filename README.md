# biodm_benchmarks

Benchmark comparisons for BioDM product https://github.com/bag-cnag/biodm/ against Django REST and FastApi

## Setup

### Venv
Create virtual environments, one for each server.

```sh
python3 -m venv venv_fastapi
source venv_fastapi/bin/activate
pip3 install -r requirements_fastapi.txt
```

```sh
python3 -m venv venv_django
source venv_django/bin/activate
pip3 install -r requirements_django.txt
```

```sh
python3 -m venv venv_omicsdmv1
source venv_omicsdmv1/bin/activate
pip3 install -r requirements_omicsdmv1.txt
```

```sh
python3 -m venv venv_omicsdmv2
source venv_omicsdmv2/bin/activate
pip3 install -r requirements_omicsdmv2.txt
cd omicsdm_v2/
pip3 install .
```

### Start dependencies

```sh 
docker compose up -d --build 
```

### FastAPI : Setup keycloak

From the admin interface, normally at https://10.10.0.3:8443/

Create a `master-realm` client in `3TR` realm, enable authentication and all flows, copy credentials
and put its value to `ADMIN_CLI_SECRET` in `fastApi/main.py`

Also, go to `Service Account Roles` tab of that client and use `Assign Role` and `Filter by clients`
to give it all permissions.

Finally, create a `3tr` group.

### Django

Apply the migrations

```sh
(venv_django)$ python3 manage.py migrate
```


Those should be sufficient for the `.vscode/launch.json` entries to run.
