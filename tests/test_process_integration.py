"""Integration tests for ProcessManager with real FRP binary."""

import os
import shutil
import tempfile

import pytest

from frp_wrapper.client.process import ProcessManager


@pytest.mark.integration
class TestProcessManagerIntegration:
    """Integration tests requiring actual FRP binary"""

    def test_real_frp_process(self):
        """Test with real FRP binary if available"""
        frp_binary = self._find_frp_binary()
        if not frp_binary:
            pytest.skip("FRP binary not found")

        config_content = """
        [common]
        server_addr = "127.0.0.1"
        server_port = 7000
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            pm = ProcessManager(frp_binary, config_path)
            assert pm.start()
            assert pm.is_running()
            assert pm.pid is not None

            old_pid = pm.pid
            assert pm.restart()
            assert pm.pid != old_pid

            assert pm.stop()
            assert not pm.is_running()

        finally:
            os.unlink(config_path)

    def test_frp_process_with_invalid_config(self):
        """Test FRP process with invalid configuration"""
        frp_binary = self._find_frp_binary()
        if not frp_binary:
            pytest.skip("FRP binary not found")

        config_content = """
        [common]
        invalid_config = "this should fail"
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            pm = ProcessManager(frp_binary, config_path)
            pm.start()

            assert not pm.wait_for_startup(timeout=2.0)

        finally:
            if pm.is_running():
                pm.stop()
            os.unlink(config_path)

    def test_frp_process_startup_detection(self):
        """Test process startup detection with real binary"""
        frp_binary = self._find_frp_binary()
        if not frp_binary:
            pytest.skip("FRP binary not found")

        config_content = """
        [common]
        server_addr = "127.0.0.1"
        server_port = 7000
        log_level = "info"
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            pm = ProcessManager(frp_binary, config_path)
            assert pm.start()

            startup_success = pm.wait_for_startup(timeout=2.0)

            assert startup_success or not pm.is_running()

            if pm.is_running():
                assert pm.stop()

        finally:
            os.unlink(config_path)

    def _find_frp_binary(self) -> str | None:
        """Find FRP binary in system PATH or common locations"""
        binary_names = ["frpc", "frpc.exe"]

        for binary_name in binary_names:
            binary_path = shutil.which(binary_name)
            if binary_path:
                return binary_path

        common_paths = [
            "/usr/local/bin/frpc",
            "/usr/bin/frpc",
            "./frpc",
            "../frpc",
            "../../frpc",
        ]

        for path in common_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path

        return None
