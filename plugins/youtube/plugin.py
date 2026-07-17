"""YouTube plugin package definition."""

from relay.contracts.plugin import Plugin
import plugins.youtube.steps.upload


class YouTubePlugin(Plugin):
    """Official YouTube Studio Uploader Plugin for Relay."""

    @property
    def name(self) -> str:
        return "youtube"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Provides steps to upload video media directly to YouTube Studio using isolated browser sessions."
