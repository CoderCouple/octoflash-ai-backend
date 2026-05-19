"""
Planner service — Claude-powered translation of natural language to structured
scene specs.

Two entry points wired today:

  plan_from_prompt(prompt) -> list[scene dicts]
      Project-level: turn a freeform prompt into an ordered list of scenes
      (each shaped like a CreateSceneRequest payload).

  instruct_scene(template, params, extra_steps, instruction, prior_instructions)
      Scene-level NL editing. Returns the new full `extra_steps` plus reasoning
      and any warnings.

Both use Anthropic's tool-use API for structured output; both use prompt
caching on the (large, stable) catalog blocks.

Auth comes from settings.anthropic_api_key (i.e. ANTHROPIC_API_KEY env var).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.service.planner_prompts import (
    INSTRUCT_TOOL,
    PLAN_TOOL,
    build_instruct_messages,
    build_plan_messages,
)
from app.settings import settings
from app.templates.loader import is_implemented
from app.templates.schema import StepSpec, TemplateDefinition

logger = logging.getLogger(__name__)


class PlannerNotConfiguredError(RuntimeError):
    """ANTHROPIC_API_KEY is not set."""


class PlannerCallError(RuntimeError):
    """The Anthropic call returned an unusable response (no tool_use, etc.)."""


@dataclass
class InstructionResult:
    extra_steps: list[StepSpec]
    reasoning: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class PlannedScene:
    """One scene as proposed by plan_from_prompt — shape mirrors CreateSceneRequest."""

    template: str
    params: dict[str, Any]
    title: str | None = None
    prompt: str | None = None
    duration: float | None = None
    style: str | None = None


class PlannerService:
    def __init__(self) -> None:
        self.model = settings.planner_model
        self.api_key = settings.anthropic_api_key

    def _client(self):
        """Build the Anthropic client lazily so import-time doesn't require the key."""
        if not self.api_key:
            raise PlannerNotConfiguredError(
                "ANTHROPIC_API_KEY is not set. Add it to .env.local before calling the planner."
            )
        # Lazy import — keeps the anthropic SDK off the import hot path.
        from anthropic import AsyncAnthropic

        return AsyncAnthropic(api_key=self.api_key)

    @staticmethod
    def _extract_tool_input(response: Any, tool_name: str) -> dict[str, Any]:
        """Pull the tool_use input out of an Anthropic response. Raises if missing."""
        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == tool_name:
                return block.input  # type: ignore[no-any-return]
        # Fallback: stringify the response so the caller can debug.
        text_blocks = [
            getattr(b, "text", "") for b in response.content
            if getattr(b, "type", None) == "text"
        ]
        raise PlannerCallError(
            f"Planner returned no `{tool_name}` tool_use block. Text content was: "
            + (" | ".join(text_blocks)[:500] if text_blocks else "(none)")
        )

    # ─── scene-level: NL edit on one scene ────────────────────────────────────

    async def instruct_scene(
        self,
        template: TemplateDefinition,
        params: dict[str, Any],
        current_extra_steps: list[StepSpec],
        instruction: str,
        prior_instructions: list[str] | None = None,
    ) -> InstructionResult:
        client = self._client()
        system_blocks, messages = build_instruct_messages(
            template=template,
            params=params,
            current_extra_steps=[
                s.model_dump(exclude_none=True) for s in current_extra_steps
            ],
            instruction=instruction,
            prior_instructions=prior_instructions or [],
        )

        logger.info(
            "planner.instruct_scene: template=%s instruction=%r", template.id, instruction
        )
        response = await client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_blocks,
            tools=[INSTRUCT_TOOL],
            tool_choice={"type": "tool", "name": INSTRUCT_TOOL["name"]},
            messages=messages,
        )

        tool_input = self._extract_tool_input(response, INSTRUCT_TOOL["name"])
        try:
            extra_steps = [StepSpec.model_validate(s) for s in tool_input.get("extra_steps", [])]
        except Exception as e:
            raise PlannerCallError(f"Planner returned invalid extra_steps: {e}") from e

        return InstructionResult(
            extra_steps=extra_steps,
            reasoning=tool_input.get("reasoning", ""),
            warnings=list(tool_input.get("warnings", []) or []),
        )

    # ─── project-level: prompt → scene plan ───────────────────────────────────

    async def plan_from_prompt(
        self,
        prompt: str,
        style_preference: str | None = None,
        max_scenes: int | None = None,
        target_duration: float | None = None,
    ) -> tuple[list[PlannedScene], str]:
        """Plan a video. Returns (scenes, planner_reasoning).

        Raises `PlannerCallError` if the plan references any template that
        isn't in the implemented set — half-broken plans are surfaced loudly
        per design call rather than silently dropped.
        """
        client = self._client()
        system_blocks, messages = build_plan_messages(
            prompt=prompt,
            style_preference=style_preference,
            max_scenes=max_scenes,
            target_duration=target_duration,
        )

        logger.info(
            "planner.plan_from_prompt: prompt=%r style=%r max=%s dur=%s",
            prompt[:120], style_preference, max_scenes, target_duration,
        )
        response = await client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=system_blocks,
            tools=[PLAN_TOOL],
            tool_choice={"type": "tool", "name": PLAN_TOOL["name"]},
            messages=messages,
        )

        tool_input = self._extract_tool_input(response, PLAN_TOOL["name"])
        raw_scenes = tool_input.get("scenes", [])

        # Validate every proposed template is implemented before accepting.
        bad = [s.get("template") for s in raw_scenes if not is_implemented(s.get("template", ""))]
        if bad:
            raise PlannerCallError(
                f"Planner proposed template(s) that aren't implemented: {bad}. "
                "Retry the request; the model has seen only implemented templates "
                "in its system prompt."
            )

        scenes = [
            PlannedScene(
                template=s["template"],
                params=s.get("params", {}),
                title=s.get("title"),
                prompt=s.get("prompt"),
                duration=s.get("duration"),
                style=s.get("style"),
            )
            for s in raw_scenes
        ]
        return scenes, tool_input.get("reasoning", "")

    async def plan_from_transcript(self, transcript: str) -> list[PlannedScene]:
        """YouTube-transcript path; deferred until the transcribe pipeline lands."""
        raise NotImplementedError(
            "plan_from_transcript not wired yet (needs Whisper output)"
        )
