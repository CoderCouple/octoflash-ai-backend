"""TranscribeSourceWorkflow — YouTube URL → Whisper → planner-ready transcript."""

from __future__ import annotations

from temporalio import workflow


@workflow.defn
class TranscribeSourceWorkflow:
    @workflow.run
    async def run(self, *, job_id: str, project_id: str, source_url: str) -> str:
        # TODO: download_audio_activity → transcribe_audio_activity → persist transcript,
        # signal planner workflow when ready.
        raise NotImplementedError("Transcribe workflow body pending")
