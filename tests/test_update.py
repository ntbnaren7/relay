import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from cli.update import _get_platform_identifier, check_for_updates
from cli.version import __version__


def test_platform_identifier():
    with patch("platform.system", return_value="Darwin"), patch("platform.machine", return_value="arm64"):
        assert _get_platform_identifier() == "macos-arm64"
        
    with patch("platform.system", return_value="Windows"), patch("platform.machine", return_value="AMD64"):
        assert _get_platform_identifier() == "windows-x64"


def test_check_for_updates_caches_result(tmp_path):
    temp_cache = tmp_path / "update_cache.json"
    
    with patch("cli.update.CACHE_FILE", temp_cache), patch("cli.update.httpx.Client") as MockClient:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"tag_name": "v99.9.9"}
        
        mock_client_instance = MockClient.return_value.__enter__.return_value
        mock_client_instance.get.return_value = mock_resp
        
        latest = check_for_updates()
        assert latest == "v99.9.9"
        MockClient.assert_called_once()
        
        assert temp_cache.exists()
        cache_data = json.loads(temp_cache.read_text())
        assert cache_data["latest_version"] == "v99.9.9"
        
        # Second call hits cache (call count should remain 1)
        latest_cached = check_for_updates()
        assert latest_cached == "v99.9.9"
        assert MockClient.call_count == 1
