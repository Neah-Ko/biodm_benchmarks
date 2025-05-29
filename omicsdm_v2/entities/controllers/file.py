from typing import List, Any

from biodm import config
from biodm.components.controllers import S3Controller, HttpMethod
from biodm.components.services import S3Service
from biodm.exceptions import UnauthorizedError, FailedUpdate
from biodm.utils.security import UserInfo
from biodm.routing import Route
from biodm.managers.dbmanager import DatabaseManager
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse

from entities import tables


class CustomFileService(S3Service):
    @DatabaseManager.in_session
    async def delete(
        self,
        pk_val: List[Any],
        session: AsyncSession,
        user_info: UserInfo | None = None
    ) -> None:
        """Files are not actually deleted, so we just updated 'enabled' flag.

        Files are versioned entity, so they are supposedly not updatable.
        This custom method bypasses that verification.
        """
        await self._check_permissions(
            "write", user_info, dict(zip(self.pk, pk_val)), session=session
        )

        stmt = update(self.table).where(self.gen_cond(pk_val)).returning(self.table)
        stmt = stmt.values(enabled=False)
        item = await session.scalar(stmt)

        if not item:
            raise FailedUpdate("Could not disable File.")


class FileController(S3Controller):
    def _infer_svc(self):
        return CustomFileService

    def routes(self, **_):
        """Adds a /files/id/visualize route.

        :return: Extended route list.
        :rtype: List[Mount | Route] | List[Mount] | List[BaseRoute]
        """
        return [
            Route(f"{self.prefix}/{self.qp_id}/visualize", self.visualize, methods=[HttpMethod.POST])
        ] + super().routes(**_)

    async def visualize(self, request: Request) -> Response:
        """

        ---

        description: Starts a visualizer instance for this file.
        parameters:
          - in: path
            name: id
        responses:
            200:
                description: Visualizer instance url
                content:
                    text/plain:
                        schema:
                            type: string
            400:
                description: File has not been uploaded yet, or File not in h5ad format
            403:
                description: Non authenticated request
            404:
                description: Not Found
        """
        vis_svc = tables.Visualization.svc

        vis_data = {
            'file_id': int(request.path_params.get('id')),
            'file_version': int(request.path_params.get('version'))
        }

        user_info = await UserInfo(request)

        if not user_info.info:
            raise UnauthorizedError("Visualizing requires authentication.")

        vis_data["user_username"] = user_info.display_name

        vis = await vis_svc.write(data=vis_data, stmt_only=False, user_info=user_info)

        return PlainTextResponse(f"http://{config.K8_HOST}/{vis.name}/")
