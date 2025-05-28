# biodm_benchmarks

Benchmark comparisons for BioDM product https://github.com/bag-cnag/biodm/ against Django REST and FastApi

## Setup

### Venv
Create both virtual environments

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

Those should be sufficient for the `.vscode/launch.json` to run both those servers.


### BioDM


Tested biodm server can be found at `https://github.com/bag-cnag/omicsdm_v2/` under `server/`


### (optional) Edit script configuration

Top of the script contains some variables you may edit such as N: the number of iterations.
