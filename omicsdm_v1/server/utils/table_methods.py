from server.app import db
from server.model import Groups, ProjectMapping

from server.utils.decorators import db_exception_handler

# TODO
# put each query into here to have a exeption handler


@db_exception_handler
def db_add(row_obj):
    db.session.add(row_obj)
    db.session.commit()


@db_exception_handler
def db_commit():
    db.session.commit()


@db_exception_handler
def db_update_groups(group_obj, row_obj):

    relationship = Groups(owner=True)
    relationship.group = group_obj
    relationship.group_id = group_obj.id

    row_obj.groups.append(relationship)
    row_obj.save_to_db()

    return True


@db_exception_handler
def db_update_project(row_obj):

    new_row_obj = ProjectMapping()
    new_row_obj.project_id = row_obj.project_id
    new_row_obj.dataset_id = row_obj.id

    new_row_obj.save_to_db()

    return True
