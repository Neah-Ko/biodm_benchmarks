#!/usr/bin/env python
"""
create flask app
"""
import traceback
import logging

from flask import Flask
from flask_restx import Api
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

from server.utils.error_handler import ApiException

# from server.utils.template_generators import generate_template

# configure root logger
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)


app.config.from_object("server.config.config.Config")
app.config.from_object("server.config.config_3tr.GeneralConfig")
app.config.from_object("server.config.config_3tr_client.ClientConfig")

# https://github.com/python-restx/flask-restx/issues/160
app.url_map.strict_slashes = False

api = Api(app, doc="/doc")
db = SQLAlchemy(app)


@app.before_first_request
def create_tables():
    """Create all sql tables"""
    db.create_all()


# below does not seem to be used at the moment?
# @app.before_first_request
# def create_templates():
#     generate_template("dataset", app.config["DATASET_EXAMPLE"])
#     generate_template("file", app.config["FILE_EXAMPLE"])


@api.errorhandler
def handle_general_exception(err):
    """Return JSON instead of HTML for any other server error"""

    # better log them somewhere?
    print(f"Unknown Exception: {str(err)}")
    print(
        "".join(
            traceback.format_exception(
                etype=type(err), value=err, tb=err.__traceback__
            )
        )
    )
    return {
        "message": "Sorry, that error is on our side, please contact:"
    }, 500


@api.errorhandler(ApiException)
def handle_raised_exception(err):
    """
    Return custom JSON when APIException is raised
    """
    return err.to_dict()


if app.debug:  # pragma: no cover

    # for database migrations
    from flask_migrate import Migrate

    migrate = Migrate(app, db)

    cors = CORS(app, resources={r"/*": {"origins": "*"}})

    from server.dev.debug import sql_debug

    # from flask_debugtoolbar import DebugToolbarExtension

    app.after_request(sql_debug)
    # toolbar = DebugToolbarExtension(app)

    @app.route("/debug")
    def hello_world():
        # import pdb; pdb.set_trace()
        return 'return "<html><body>debug</body></html>"'


# have to be imported here otherwise circular import error
from server.apis.test import ns as ns_test  # noqa: E402
from server.apis.project import ns as ns_project  # noqa: E402
from server.apis.dataset import ns as ns_dataset  # noqa: E402
from server.apis.template import ns as ns_template  # noqa: E402
from server.apis.file import ns as ns_file  # noqa: E402

api.add_namespace(ns_test, path="/api")
api.add_namespace(ns_template, path="/api/template")
api.add_namespace(ns_project, path="/api/projects")
api.add_namespace(ns_dataset, path="/api/datasets")
api.add_namespace(ns_file, path="/api/files")

if __name__ == "__main__":  # pragma: no cover
    app.run(host="0.0.0.0", port=5000, threaded=True)
