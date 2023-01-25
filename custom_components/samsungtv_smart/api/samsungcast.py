"""Smartthings TV integration cast tube."""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

from casttube import YouTubeSession
import requests

_LOGGER = logging.getLogger(__name__)


def _format_url(host: str, app: str) -> str:
    """Return URL used to retrieve screen id."""
    return f"http://{host}:8080/ws/app/{app}"


class CastTubeNotSupported(Exception):
    """Error during cast."""


class SamsungCastTube:
    """Class to cast video to youtube TV app."""

    def __init__(self, host: str):
        """Initialize the class."""
        self._host = host
        self._cast_api: YouTubeSession | None = None

    @staticmethod
    def _get_screen_id(host: str) -> str:
        """Retrieve screen id from the TV."""
        url = _format_url(host, "YouTube")
        try:
            response = requests.get(url, timeout=5)
        except requests.ConnectionError as exc:
            _LOGGER.warning(
                "Failed to retrieve YouTube screenID for host %s: %s", host, exc
            )
            raise CastTubeNotSupported() from exc

        screen_id = None
        tree = ET.fromstring(response.content.decode("utf8"))
        for elem in tree.iter():
            if elem.tag.endswith("screenId"):
                _LOGGER.debug("YouTube ScreenID: %s", screen_id)
                screen_id = elem.text

        if screen_id is None:
            _LOGGER.warning("Failed to retrieve YouTube screenID for host %s", host)
            raise CastTubeNotSupported()

        return screen_id

    def _get_api(self) -> YouTubeSession:
        """Get the API to cast video."""
        if not self._cast_api:
            screen_id = self._get_screen_id(self._host)
            self._cast_api = YouTubeSession(screen_id)
        return self._cast_api

    def play_video(self, video_id: str) -> None:
        """Play video_id immediatly."""
        self._get_api().play_video(video_id)

    def play_next(self, video_id: str) -> None:
        """Play video_id after the currently playing video.."""
        self._get_api().play_next(video_id)

    def add_to_queue(self, video_id: str) -> None:
        """Add a video to the video queue."""
        self._get_api().add_to_queue(video_id)

    def clear_queue(self) -> None:
        """Clear the video queue."""
        self._get_api().clear_playlist()
