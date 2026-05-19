from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.scene_instruction_model import SceneInstruction


class SceneInstructionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_scene(self, scene_id: str) -> list[SceneInstruction]:
        result = await self.db.execute(
            select(SceneInstruction)
            .where(SceneInstruction.scene_id == scene_id)
            .order_by(SceneInstruction.applied_at.asc())
        )
        return list(result.scalars().all())

    async def create(self, instruction: SceneInstruction) -> SceneInstruction:
        self.db.add(instruction)
        await self.db.flush()
        return instruction

    async def delete_for_scene(self, scene_id: str) -> int:
        """Wipe an entire scene's instruction history (used by `collapse`)."""
        result = await self.db.execute(
            delete(SceneInstruction).where(SceneInstruction.scene_id == scene_id)
        )
        await self.db.flush()
        return result.rowcount or 0
