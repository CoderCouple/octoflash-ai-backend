from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.response.scene_response import SceneResponse
from app.common.exceptions import EntityNotFoundError, InvalidStateTransitionError
from app.db.repository.scene_repository import SceneRepository
from app.model.scene_model import Scene


class SceneService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.scene_repo = SceneRepository(db)

    async def add_scene(
        self,
        project_id: str,
        template: str,
        title: str | None = None,
        prompt: str | None = None,
        params: dict[str, Any] | None = None,
        duration: float | None = None,
        style: str | None = None,
        motion: str | None = None,
        n: int | None = None,
    ) -> SceneResponse:
        slot = n if n is not None else await self.scene_repo.next_n_for_project(project_id)
        scene = Scene(
            project_id=project_id,
            n=slot,
            template=template,
            title=title,
            prompt=prompt,
            params=params or {},
            duration=duration,
            style=style,
            motion=motion,
        )
        scene = await self.scene_repo.create(scene)
        return SceneResponse.model_validate(scene)

    async def get_scene(self, scene_id: str) -> SceneResponse:
        scene = await self.scene_repo.get_by_id(scene_id)
        if not scene:
            raise EntityNotFoundError("Scene", scene_id)
        return SceneResponse.model_validate(scene)

    async def update_scene(
        self,
        scene_id: str,
        title: str | None = None,
        template: str | None = None,
        prompt: str | None = None,
        params: dict[str, Any] | None = None,
        duration: float | None = None,
        style: str | None = None,
        motion: str | None = None,
        force: bool = False,
    ) -> SceneResponse:
        scene = await self.scene_repo.get_by_id(scene_id)
        if not scene:
            raise EntityNotFoundError("Scene", scene_id)

        if title is not None:
            scene.title = title
        if template is not None and template != scene.template:
            # Template switch nukes the per-scene NL divergence — refuse silently
            # unless the caller passed force=true, in which case we clear it.
            if scene.extra_steps and not force:
                raise InvalidStateTransitionError(
                    current_state=f"advanced (extra_steps len={len(scene.extra_steps)})",
                    action=f"switch template from {scene.template!r} to {template!r}",
                )
            if scene.extra_steps and force:
                scene.extra_steps = []
                scene.mode = "structured"
            scene.template = template
        if prompt is not None:
            scene.prompt = prompt
        if params is not None:
            scene.params = params
        if duration is not None:
            scene.duration = duration
        if style is not None:
            scene.style = style
        if motion is not None:
            scene.motion = motion
        scene.updated_at = datetime.now(timezone.utc)
        scene = await self.scene_repo.update(scene)
        return SceneResponse.model_validate(scene)

    async def delete_scene(self, scene_id: str) -> None:
        scene = await self.scene_repo.get_by_id(scene_id)
        if not scene:
            raise EntityNotFoundError("Scene", scene_id)
        await self.scene_repo.delete(scene)

    async def select_variation(self, scene_id: str, variation_id: str) -> SceneResponse:
        scene = await self.scene_repo.get_by_id(scene_id)
        if not scene:
            raise EntityNotFoundError("Scene", scene_id)
        scene.selected_variation_id = variation_id
        scene.updated_at = datetime.now(timezone.utc)
        scene = await self.scene_repo.update(scene)
        return SceneResponse.model_validate(scene)
