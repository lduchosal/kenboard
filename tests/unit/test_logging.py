"""Unit tests for logging setup (rotation safety + SIGHUP handling)."""

import logging
import logging.handlers
import os
import signal

import pytest

from dashboard import logging as dashboard_logging


@pytest.fixture()
def isolated_log_dir(tmp_path, monkeypatch):
    """Point LOG_DIR / LOG_FILE at a tmp dir for the test."""
    monkeypatch.setattr(dashboard_logging, "LOG_DIR", tmp_path)
    monkeypatch.setattr(dashboard_logging, "LOG_FILE", tmp_path / "dashboard.log")
    yield tmp_path
    # Reset root logger so other tests aren't affected
    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)
        h.close()


class TestRotationSafety:
    """Make sure newsyslog can rotate the log file under us without crashing."""

    def test_uses_watched_file_handler(self, isolated_log_dir):
        """The file handler must be a WatchedFileHandler so a rename or unlink of the
        underlying file is detected and the handle reopened on the next emit.

        A plain FileHandler would keep writing to the deleted inode forever (silent log
        loss after newsyslog rotates).
        """
        dashboard_logging.setup_logging(debug=False)
        root = logging.getLogger()
        file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1
        assert isinstance(file_handlers[0], logging.handlers.WatchedFileHandler)

    def test_log_reopens_after_rename(self, isolated_log_dir):
        """Simulate newsyslog: rename the file, write a new message, the
        handler must reopen the original path and write into the new file."""
        dashboard_logging.setup_logging(debug=False)
        log = dashboard_logging.get_logger("test")
        log.info("before_rotate")
        # Force the buffer to flush
        for h in logging.getLogger().handlers:
            h.flush()
        original = isolated_log_dir / "dashboard.log"
        rotated = isolated_log_dir / "dashboard.log.0"
        os.rename(original, rotated)
        # After rename: original path no longer exists, but next emit
        # should recreate it.
        log.info("after_rotate")
        for h in logging.getLogger().handlers:
            h.flush()
        assert original.exists(), "WatchedFileHandler should reopen the file"
        new_content = original.read_text()
        old_content = rotated.read_text()
        assert "after_rotate" in new_content
        assert "before_rotate" in old_content


class TestSighupHandling:
    """Make sure SIGHUP from the rc.d reload script doesn't kill the process."""

    def test_sighup_is_ignored_after_setup(self, isolated_log_dir):
        """``setup_logging`` must install SIG_IGN for SIGHUP so the daemon doesn't die
        when newsyslog signals it after rotation.
        """
        if not hasattr(signal, "SIGHUP"):
            pytest.skip("SIGHUP not available on this platform")
        # Save and restore in case other tests need a different handler
        previous = signal.getsignal(signal.SIGHUP)
        try:
            dashboard_logging.setup_logging(debug=False)
            assert signal.getsignal(signal.SIGHUP) == signal.SIG_IGN
        finally:
            signal.signal(signal.SIGHUP, previous)
