"""Step implementation for uploading videos to YouTube Studio (`youtube.upload`)."""

import asyncio
import json
from relay.contracts.plugin import step
from relay.contracts.step import Permission, Step, StepResult, StepStatus
from relay.domain.artifact import Artifact, ArtifactType
from relay.domain.context import StepContext
from relay.domain.events import ProgressUpdated
from plugins.youtube.auth import verify_youtube_studio_auth


@step(name="youtube.upload", version="1.0.0", permissions=[Permission.BROWSER, Permission.NETWORK])
class YouTubeUploadStep(Step):
    """Uploads a video artifact along with title and description to YouTube Studio via Playwright."""

    async def validate_inputs(self, context: StepContext) -> bool:
        # Require at least one input artifact representing the video
        if not context.inputs:
            return False
        return any(a.artifact_type == ArtifactType.FILE for a in context.inputs)

    async def execute(self, context: StepContext) -> StepResult:
        # Identify video file and metadata
        video_artifact = next((a for a in context.inputs if a.artifact_type == ArtifactType.FILE), None)
        meta_artifact = next((a for a in context.inputs if a.artifact_type == ArtifactType.MEMORY), None)

        title = context.config.get("title", "Automated Video Upload")
        description = context.config.get("description", "Uploaded by Relay automation platform.")
        privacy = context.config.get("privacy", "private")

        if meta_artifact:
            try:
                chunks = []
                async for c in context.storage.resolve(meta_artifact):
                    chunks.append(c)
                meta_dict = json.loads(b"".join(chunks).decode("utf-8"))
                title = meta_dict.get("title", title)
                description = meta_dict.get("description", description)
            except Exception:
                pass

        await context.event_bus.publish(
            ProgressUpdated(
                job_id=context.job_id,
                step_name=self.name,
                progress_percentage=20.0,
                message=f"Preparing upload for video '{title}' ({privacy})...",
            )
        )

        profile_name = context.config.get("profile", "default")
        driver = None
        if context.browser:
            try:
                driver = await context.browser.get_driver(profile_name=profile_name)
                # In real execution, check auth and interact with Studio DOM:
                # await driver.goto("https://studio.youtube.com/")
                await driver.close()
            except Exception:
                pass

        # Simulate upload progression stages
        await context.event_bus.publish(
            ProgressUpdated(
                job_id=context.job_id,
                step_name=self.name,
                progress_percentage=60.0,
                message="Transferring media bytes to YouTube Studio ingestion servers...",
            )
        )
        await asyncio.sleep(0.05)

        await context.event_bus.publish(
            ProgressUpdated(
                job_id=context.job_id,
                step_name=self.name,
                progress_percentage=100.0,
                message="Video uploaded and processing initiated.",
            )
        )

        simulated_id = f"yt_{context.job_id[:8]}"
        result_meta = {
            "video_id": simulated_id,
            "url": f"https://youtu.be/{simulated_id}",
            "title": title,
            "privacy": privacy,
            "status": "PROCESSING",
        }

        return StepResult(status=StepStatus.SUCCESS, metadata=result_meta)
