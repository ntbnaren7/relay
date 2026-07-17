"""Common utility plugin package definition."""

from relay.contracts.plugin import Plugin
import plugins.common.steps.ffmpeg_step
import plugins.common.steps.notify_step


class CommonPlugin(Plugin):
    """Official Common Utilities Plugin for Relay (FFmpeg, Webhooks, Notifications)."""

    @property
    def name(self) -> str:
        return "common"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Provides essential utility steps like FFmpeg transcoding and webhook notifications."
