from marshmallow import validates_schema, Schema
from marshmallow.fields import String, Nested, Integer, Boolean, Date#, List
from marshmallow.validate import OneOf, Range
from marshmallow.exceptions import ValidationError

from biodm import config
from biodm.schemas import UploadSchema
from .dataset import DatasetSchema


MOL_EXTS = ['tsv', 'csv', 'txt', 'gz', 'rds', 'rda', 'h5ad', 'h5']
CLI_EXTS = ['tsv', 'csv', 'json', 'yaml', 'yml', 'xml']


class DumpDatasetSchema(DatasetSchema):
    class Meta:
        exclude=('files', 'project')


class FileSchema(Schema):
    # Keys
    id = Integer()
    version = Integer()

    #  Versioned
    is_latest = Boolean(dump_only=True)

    # File management
    filename     = String(required=True)
    extension    = String(required=True,
                          validate=OneOf(MOL_EXTS + CLI_EXTS + ['pdf']))
    size         = Integer(required=True,
                           validate=Range(min=24, max=config.S3_FILE_SIZE_LIMIT * 1024 ** 3))
    ready        = Boolean(dump_only=True)
    dl_count     = Integer(dump_only=True)
    emited_at    = Date(dump_only=True)
    validated_at = Date(dump_only=True)

    # Use case related
    type = String(required=True,
                  validate=OneOf(['molecular', 'clinical', 'licence']))
    enabled = Boolean()
    description = String()

    # FK
    submitter_username = String() # auto-filled
    dataset_id = Integer(required=True)
    dataset_version = Integer(required=True)

    dataset = Nested(DumpDatasetSchema)
    # datasets = List(Nested(DumpDatasetSchema))
    upload = Nested(UploadSchema, dump_only=True)


    @validates_schema
    def extension_validator(self, data, **_):
        """Validates files extensions according to file type."""
        ext = data.get('extension', "")
        match data.get('type', None):
            case 'molecular':
                if not ext in MOL_EXTS:
                    raise ValidationError(
                        "Molecular files should have one of the following"
                        f" extensions: {MOL_EXTS}"
                    )
            case 'clinical':
                if not ext in CLI_EXTS:
                    raise ValidationError(
                        "Clinical files should have one of the following"
                        f" extensions: {CLI_EXTS}"
                    )
            case 'licence':
                if ext != 'pdf':
                    raise ValidationError(
                        "Licence should be a pdf file"
                    )
            case _:
                pass


# gen_schema output for reference.
# id <class 'int'> required: False
# version <class 'int'> required: False
# type <class 'str'> required: True

# enabled <class 'bool'> required: False
# comment <class 'str'> required: False
# filename <class 'str'> required: True
# extension <class 'str'> required: True
# ready <class 'bool'> required: False
# size <class 'int'> required: True
# dl_count <class 'int'> required: False
# emited_at <class 'datetime.datetime'> required: False
# validated_at <class 'datetime.datetime'> required: False

# upload_id <class 'int'> required: False
# submitter_username <class 'str'> required: True
# dataset_id <class 'int'> required: True
# dataset_version <class 'int'> required: True
# ---
# dataset
# upload
