from fastapi import APIRouter

from app.api.v1.controller.billing_api import router as billing_router
from app.api.v1.controller.contact_api import router as contact_router
from app.api.v1.controller.credential_api import router as credential_router
from app.api.v1.controller.executions_api import router as executions_router
from app.api.v1.controller.export_api import router as export_router
from app.api.v1.controller.health_api import router as health_router
from app.api.v1.controller.organization_api import router as organization_router
from app.api.v1.controller.playground_api import router as playground_router
from app.api.v1.controller.project_api import router as project_router
from app.api.v1.controller.scene_api import router as scene_router
from app.api.v1.controller.source_api import router as source_router
from app.api.v1.controller.target_api import router as target_router
from app.api.v1.controller.user_api import router as user_router
from app.api.v1.controller.voice_api import router as voice_router
from app.api.v1.controller.workflow_api import router as workflow_router
from app.api.v1.controller.workspace_api import router as workspace_router

# Polling lives at /executions/:id (replaces legacy /jobs/:id).

router = APIRouter(prefix="/v1")

router.include_router(health_router)
router.include_router(user_router)
router.include_router(organization_router)
router.include_router(workspace_router)
router.include_router(billing_router)
router.include_router(project_router)
router.include_router(scene_router)
router.include_router(workflow_router)
router.include_router(executions_router)
router.include_router(export_router)
router.include_router(source_router)
router.include_router(target_router)
router.include_router(voice_router)
router.include_router(playground_router)
router.include_router(credential_router)
router.include_router(contact_router)
