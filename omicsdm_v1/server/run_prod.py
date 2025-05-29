#!/usr/bin/env python
import subprocess  # pragma no cover

try:
    subprocess.check_call(
        [
            "gunicorn",
            "--access-logfile=-",
            "--timeout",
            "600",
            "--reload",
            "--workers",
            "2",
            "-b",
            "0.0.0.0:8003",
            "server.app:app",
        ],
        shell=False,
    )  # pragma no cover
except Exception as err:
    print(err)
