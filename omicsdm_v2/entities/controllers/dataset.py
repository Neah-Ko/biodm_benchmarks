from typing import TYPE_CHECKING

from biodm.components.controllers import ResourceController, overload_docstring
from biodm.components.services import UnaryEntityService, CompositeEntityService

from entities.tables import Tag
#, FileCollection

if TYPE_CHECKING:
    from biodm.api import Api


class DatasetController(ResourceController):
    def __init__(self, app: 'Api') -> None:
        super().__init__(app=app)
        # Instance headless services.
        Tag.svc = UnaryEntityService(app=app, table=Tag)
#        FileCollection.svc = CompositeEntityService(app=app, table=FileCollection)

    @overload_docstring
    async def create(**kwargs):
        """
        requestBody:
            description: payload.
            required: true
            content:
                application/json:
                    schema: DatasetSchema
        responses:
            201:
                description: Create Dataset.
                content:
                    application/json:
                        schema: DatasetSchema
            204:
                description: Empty Payload.
        """

    @overload_docstring
    async def read(**kwargs):
        """
        parameters:
            - in: path
              name: id
              description: Dataset id
            - in: path
              name: version
              description: Dataset version
        responses:
            200:
                description: Found matching Dataset.
                examples: |
                    {"id": "1", "version": "1", "name": "instant_sc_1234"}
                content:
                    application/json:
                        schema: DatasetSchema
            404:
                description: Dataset not found.
        """
