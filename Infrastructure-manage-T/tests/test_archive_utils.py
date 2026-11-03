"""
Security tests for archive_utils.safe_extractall.

These cover the classic tar-slip vectors: parent traversal, absolute paths,
symlinks/hardlinks, and special files. Every case must be rejected before
anything is written outside the extraction root.
"""
import io
import os
import tarfile
import tempfile
import unittest

from app.services.archive_utils import UnsafeArchiveError, safe_extractall


class TestSafeExtractall(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.target = os.path.join(self.temp_dir, "target")
        os.makedirs(self.target, exist_ok=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _archive(self, members):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            for name, data in members:
                info = tarfile.TarInfo(name=name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
        buffer.seek(0)
        return tarfile.open(fileobj=buffer, mode="r:gz")

    def test_safe_member_is_extracted(self):
        archive = self._archive([("config/odoo.conf", b"admin_passwd = secret\n")])
        safe_extractall(archive, self.target)
        extracted = os.path.join(self.target, "config", "odoo.conf")
        self.assertTrue(os.path.isfile(extracted))
        with open(extracted, "rb") as handle:
            self.assertIn(b"admin_passwd", handle.read())

    def test_parent_traversal_is_rejected(self):
        archive = self._archive([("../escaped.txt", b"owned")])
        with self.assertRaises(UnsafeArchiveError):
            safe_extractall(archive, self.target)
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir, "escaped.txt")))

    def test_absolute_path_is_rejected(self):
        archive = self._archive([("/etc/passwd", b"owned")])
        with self.assertRaises(UnsafeArchiveError):
            safe_extractall(archive, self.target)

    def test_symlink_is_rejected(self):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            info = tarfile.TarInfo(name="link")
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/passwd"
            archive.addfile(info)
        buffer.seek(0)
        with tarfile.open(fileobj=buffer, mode="r:gz") as archive:
            with self.assertRaises(UnsafeArchiveError):
                safe_extractall(archive, self.target)

    def test_hardlink_is_rejected(self):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            info = tarfile.TarInfo(name="hardlink")
            info.type = tarfile.LNKTYPE
            info.linkname = "/etc/passwd"
            archive.addfile(info)
        buffer.seek(0)
        with tarfile.open(fileobj=buffer, mode="r:gz") as archive:
            with self.assertRaises(UnsafeArchiveError):
                safe_extractall(archive, self.target)

    def test_device_file_is_rejected(self):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            info = tarfile.TarInfo(name="device")
            info.type = tarfile.CHRTYPE
            archive.addfile(info)
        buffer.seek(0)
        with tarfile.open(fileobj=buffer, mode="r:gz") as archive:
            with self.assertRaises(UnsafeArchiveError):
                safe_extractall(archive, self.target)


if __name__ == "__main__":
    unittest.main()
