from sqlalchemy.exc import IntegrityError
from server.utils.error_handler import DatabaseError
from server.app import db


# cannot be put into error_handler.py because
# server.run import db triggers a circular input error
def db_exception_handler(func):
    def inner_function(*args, **kwargs):
        error_msg = "database error, please contact:"

        try:
            res = func(*args, **kwargs)
        except IntegrityError as err:
            raise DatabaseError("save_to_db", err, error_msg)
        except Exception as err:
            db.session.rollback()
            raise DatabaseError("save_to_db", err, error_msg)

        return res

    return inner_function
