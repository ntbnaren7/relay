"""Instagram plugin package definition."""

from relay.contracts.plugin import Plugin
import plugins.instagram.steps.download
import plugins.instagram.steps.metadata


class InstagramPlugin(Plugin):
    """Official Instagram Downloader & Extractor Plugin for Relay."""

    @property
    def name(self) -> str:
        return "instagram"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Provides steps to download Reels/Posts and extract metadata from Instagram."
