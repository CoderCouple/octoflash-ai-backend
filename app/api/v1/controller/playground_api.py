"""/playground — preset catalog, ad-hoc ManimGL render, render output stream.

Powers the `/playground` page on the Vite frontend. Renders run inline
(synchronous request) inside an isolated Docker container by default
(`PLAYGROUND_SANDBOX_MODE=docker`) — see PlaygroundService for the security
model. Setting `PLAYGROUND_SANDBOX_MODE=local` runs `manimgl` directly on
the host (dev only, no isolation). Short, throwaway scenes; no Temporal
involvement.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.api.tags import Tags
from app.api.v1.request.playground_request import PlaygroundRenderRequest
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.playground_response import (
    PlaygroundPresetResponse,
    PlaygroundRenderResponse,
)
from app.service.playground_service import (
    PlaygroundRenderError,
    PlaygroundRuntimeUnavailable,
    PlaygroundService,
    PlaygroundValidationError,
)

router = APIRouter(tags=[Tags.Playground])


def get_playground_service() -> PlaygroundService:
    return PlaygroundService()


@router.get(
    "/playground/presets",
    response_model=BaseResponse[list[PlaygroundPresetResponse]],
)
async def list_presets(
    service: PlaygroundService = Depends(get_playground_service),
):
    """Built-in scene presets that match the frontend dropdown."""
    presets = [
        PlaygroundPresetResponse(
            id=p.id,
            label=p.label,
            duration=p.duration,
            preview=p.preview,
            code=p.code,
        )
        for p in service.list_presets()
    ]
    return success_response(presets, "Presets fetched")


@router.post(
    "/playground/render",
    response_model=BaseResponse[PlaygroundRenderResponse],
    status_code=201,
)
async def render(
    body: PlaygroundRenderRequest,
    service: PlaygroundService = Depends(get_playground_service),
):
    """Render a user-supplied Manim scene synchronously."""
    try:
        result = await service.render(
            code=body.code,
            scene_name=body.scene_name,
            quality=body.quality,
        )
    except PlaygroundValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except PlaygroundRuntimeUnavailable as exc:
        # The sandbox runtime (Docker) isn't reachable — operators need to
        # bring it up. Returning 503 is correct: not the caller's fault.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except PlaygroundRenderError as exc:
        # Render failed inside the container — surface as 422 so the FE can
        # distinguish "your code is bad" from a 5xx server error.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    payload = PlaygroundRenderResponse(
        render_id=result.render_id,
        video_url=result.video_url,
        scene_class=result.scene_class,
        quality=result.quality,
        took_ms=result.took_ms,
        log_lines=result.log_lines,
        sandbox_mode=result.sandbox_mode,
    )
    return success_response(payload, "Render complete", 201)


@router.get("/playground/renders/{render_id}/output")
async def render_output(
    render_id: str,
    service: PlaygroundService = Depends(get_playground_service),
):
    """Stream the rendered MP4 for the given render id."""
    path = service.output_path(render_id)
    if not path or not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No render found for id '{render_id}'",
        )
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=path.name,
        headers={"Cache-Control": "no-cache"},
    )
