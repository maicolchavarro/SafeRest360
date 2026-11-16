"""Filesystem safety checks; no server, database or Telegram connection."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from fastapi import HTTPException
from app.api.v1.alerts import _delete_snapshot
from app.config import settings


class SnapshotCleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = patch.object(settings, "SNAPSHOT_LOCAL_PATH", str(self.root))
        self.config.start()
        self.addCleanup(self.config.stop)
        self.snapshot = self.root / "restaurant-a" / "alert.jpg"
        self.snapshot.parent.mkdir()
        self.snapshot.write_bytes(b"snapshot")
        self.alert = SimpleNamespace(restaurant_id="restaurant-a", snapshot_path=str(self.snapshot))

    def test_deletes_own_snapshot(self):
        self.assertTrue(_delete_snapshot(self.alert))
        self.assertFalse(self.snapshot.exists())

    def test_missing_snapshot_is_idempotent(self):
        self.snapshot.unlink()
        self.assertFalse(_delete_snapshot(self.alert))

    def test_other_restaurant_cannot_be_deleted(self):
        self.alert.restaurant_id = "restaurant-b"
        with self.assertRaises(HTTPException) as error:
            _delete_snapshot(self.alert)
        self.assertEqual(error.exception.status_code, 409)
        self.assertTrue(self.snapshot.exists())

    def test_permission_error_is_not_silenced(self):
        with patch.object(Path, "unlink", side_effect=PermissionError("test")):
            with self.assertRaises(HTTPException) as error:
                _delete_snapshot(self.alert)
        self.assertEqual(error.exception.status_code, 503)
        self.assertTrue(self.snapshot.exists())

    def test_empty_path_has_no_file(self):
        self.alert.snapshot_path = None
        self.assertFalse(_delete_snapshot(self.alert))
