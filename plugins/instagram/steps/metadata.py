"""Step implementation for extracting Instagram post metadata (`instagram.extract_metadata`)."""

import json
from typing import AsyncIterator
from relay.contracts.plugin import step
from relay.contracts.step import Permission, Step, StepResult, StepStatus
from relay.domain.artifact import Artifact, ArtifactType
from relay.domain.context import StepContext
from plugins.instagram.extractor import extract_media_info


@step(name="instagram.extract_metadata", version="1.0.0", permissions=[Permission.BROWSER, Permission.NETWORK])
class InstagramExtractMetadataStep(Step):
    """Extracts caption, title, and author metadata from an Instagram URL into a memory artifact."""

    async def validate_inputs(self, context: StepContext) -> bool:
        url = context.config.get("url")
        if not url and context.inputs:
            return True
        return bool(url)

    async def execute(self, context: StepContext) -> StepResult:
        url = context.config.get("url")
        if not url and context.inputs:
            url = context.inputs[0].metadata.get("url") or context.inputs[0].metadata.get("source_url")

        driver = None
        if context.browser:
            try:
                driver = await context.browser.get_driver()
            except Exception:
                driver = None

        info = await extract_media_info(str(url or "https://instagram.com/p/default"), driver=driver)
        if driver:
            await driver.close()

        artifact = Artifact(
            id=f"ig_meta_{context.job_id[:8]}",
            artifact_type=ArtifactType.MEMORY,
            name="metadata.json",
            metadata=info,
        )

        payload = json.dumps(info, indent=2).encode("utf-8")
        async def _stream() -> AsyncIterator[bytes]:
            yield payload

        await context.storage.save(artifact, _stream())
        return StepResult(status=StepStatus.SUCCESS, output_artifacts=[artifact], metadata=info)
