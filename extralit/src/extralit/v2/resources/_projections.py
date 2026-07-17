from extralit.v2.models import ProjectionView
from extralit.v2.resources._base import ResourceBase


class Projections(ResourceBase):
    async def get(self, workspace_id, reference: str) -> ProjectionView:
        """Response-or-suggestion per question for every record sharing this reference.
        Slashes stay raw: the server route is /projection/references/{reference:path}."""
        payload = await self._transport.request(
            "GET", f"/projection/references/{reference}", params={"workspace_id": str(workspace_id)}
        )
        return ProjectionView.model_validate(payload)
