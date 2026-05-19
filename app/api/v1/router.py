from fastapi import APIRouter

from app.api.v1.controller.channel_api import router as channel_router
from app.api.v1.controller.export_api import router as export_router
from app.api.v1.controller.health_api import router as health_router
from app.api.v1.controller.job_api import router as job_router
from app.api.v1.controller.project_api import router as project_router
from app.api.v1.controller.scene_api import router as scene_router
from app.api.v1.controller.template_api import router as template_router
from app.api.v1.controller.variation_api import router as variation_router
from app.api.v1.controller.workflow_api import router as workflow_router

router = APIRouter(prefix="/v1")

router.include_router(health_router)
router.include_router(project_router)
router.include_router(scene_router)
router.include_router(variation_router)
router.include_router(workflow_router)
router.include_router(job_router)
router.include_router(export_router)
router.include_router(template_router)
router.include_router(channel_router)
