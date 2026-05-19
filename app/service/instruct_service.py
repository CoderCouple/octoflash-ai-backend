"""
InstructService — orchestrates one `POST /scenes/{id}/instruct` call.

Pipeline:
  1. Load scene + template def.
  2. Fetch prior instructions (last N) for LLM context.
  3. Call PlannerService.instruct_scene(...) → InstructionResult.
  4. Validate each returned StepSpec against the primitive registry.
  5. Persist:
       - Append a SceneInstruction row capturing instruction + diff (before/after).
       - Update Scene.extra_steps + Scene.mode.
  6. Return the updated SceneResponse.

Does *not* trigger a render. That's a separate `POST /scenes/{id}/variations`
call (two-step by design — see CLAUDE.md "NL scene editing").
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.response.scene_response import SceneResponse
from app.common.exceptions import EntityNotFoundError, RenderError
from app.db.repository.scene_instruction_repository import SceneInstructionRepository
from app.db.repository.scene_repository import SceneRepository
from app.model.scene_instruction_model import SceneInstruction
from app.service.planner_service import PlannerService
from app.templates.loader import TemplateNotImplementedError, load
from app.templates.primitives.registry import PRIMITIVES
from app.templates.renderer import PrimitiveNotRegisteredError
from app.templates.schema import StepSpec


# How many prior instructions to feed Claude for context. Hard cap to keep
# context-window costs predictable; the full history still lives in the DB.
_PRIOR_INSTRUCTIONS_WINDOW = 10


class InstructService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.scene_repo = SceneRepository(db)
        self.instruction_repo = SceneInstructionRepository(db)
        self.planner = PlannerService()

    async def instruct(
        self,
        scene_id: str,
        instruction: str,
        applied_by: str | None = None,
    ) -> SceneResponse:
        scene = await self.scene_repo.get_by_id(scene_id)
        if not scene:
            raise EntityNotFoundError("Scene", scene_id)

        try:
            template = load(scene.template)
        except TemplateNotImplementedError as e:
            raise RenderError(
                f"Scene references template {scene.template!r} which has no def file."
            ) from e

        # Hydrate current extra_steps from the DB jsonb back into StepSpec objects
        # so the planner gets a typed view of the scene's divergence.
        current_extra_steps = [StepSpec.model_validate(s) for s in (scene.extra_steps or [])]

        prior = await self.instruction_repo.list_by_scene(scene_id)
        prior_window = [p.instruction for p in prior[-_PRIOR_INSTRUCTIONS_WINDOW:]]

        result = await self.planner.instruct_scene(
            template=template,
            params=dict(scene.params or {}),
            current_extra_steps=current_extra_steps,
            instruction=instruction,
            prior_instructions=prior_window,
        )

        # Validate every step references a known primitive — Pydantic typing
        # alone won't catch unknown primitive ids.
        unknown = [s.primitive for s in result.extra_steps if s.primitive not in PRIMITIVES]
        if unknown:
            raise PrimitiveNotRegisteredError(
                f"Planner returned unknown primitives: {sorted(set(unknown))}"
            )

        new_extra_steps_jsonb = [
            json.loads(s.model_dump_json(exclude_none=True)) for s in result.extra_steps
        ]
        before = list(scene.extra_steps or [])

        # Persist the audit row first so we capture the attempt even if the
        # scene write somehow fails.
        await self.instruction_repo.create(
            SceneInstruction(
                scene_id=scene_id,
                instruction=instruction,
                applied_by=applied_by,
                diff={
                    "extra_steps_before": before,
                    "extra_steps_after": new_extra_steps_jsonb,
                    "reasoning": result.reasoning,
                    "warnings": result.warnings,
                },
            )
        )

        # Apply the new divergence to the scene.
        scene.extra_steps = new_extra_steps_jsonb
        scene.mode = "advanced" if new_extra_steps_jsonb else "structured"
        scene.updated_at = datetime.now(timezone.utc)
        scene = await self.scene_repo.update(scene)

        return SceneResponse.model_validate(scene)

    async def collapse(self, scene_id: str) -> SceneResponse:
        """Wipe instruction history; keep current `extra_steps` as the new baseline.

        Stacking semantics (per design): each instruction layers on top of the
        prior ones. Over time the history grows. `collapse` resets the slate so
        the next instruction starts from "this is the new normal" without
        Claude having to re-reason about every prior edit.
        """
        scene = await self.scene_repo.get_by_id(scene_id)
        if not scene:
            raise EntityNotFoundError("Scene", scene_id)
        await self.instruction_repo.delete_for_scene(scene_id)
        return SceneResponse.model_validate(scene)

    async def discard_divergence(self, scene_id: str) -> SceneResponse:
        """Drop all NL edits and return to pure template baseline.

        Wipes both `extra_steps` (back to []) and history. Used by the
        frontend's "Revert to template" action.
        """
        scene = await self.scene_repo.get_by_id(scene_id)
        if not scene:
            raise EntityNotFoundError("Scene", scene_id)
        await self.instruction_repo.delete_for_scene(scene_id)
        scene.extra_steps = []
        scene.mode = "structured"
        scene.updated_at = datetime.now(timezone.utc)
        scene = await self.scene_repo.update(scene)
        return SceneResponse.model_validate(scene)

    async def list_instructions(self, scene_id: str) -> list[SceneInstruction]:
        return await self.instruction_repo.list_by_scene(scene_id)
