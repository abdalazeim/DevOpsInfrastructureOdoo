"""
Safe archive extraction helpers.

Python's ``tarfile.extractall`` trusts member names by default, which allows
path traversal (``../../etc/passwd``) and link-based escapes. These helpers
validate every member before anything is written to disk.
"""
import os
import tarfile
from typing import List


class UnsafeArchiveError(ValueError):
    """Raised when an archive contains an entry that could escape the target."""


def _is_within(base: str, candidate: str) -> bool:
    """Returns True when ``candidate`` is inside ``base`` (both normalized)."""
    try:
        return os.path.commonpath([base, candidate]) == base
    except ValueError:
        # Different drives / invalid paths on some platforms.
        return False


def safe_extractall(archive: tarfile.TarFile, target_dir: str) -> None:
    """
    Extract ``archive`` into ``target_dir`` while rejecting:
      * absolute member names,
      * ``..`` path traversal,
      * symbolic / hard links,
      * device, FIFO, and other special files.
    """
    base = os.path.realpath(os.path.abspath(target_dir))
    os.makedirs(base, exist_ok=True)

    safe_members: List[tarfile.TarInfo] = []
    for member in archive.getmembers():
        name = member.name.replace("\\", "/")
        if name.startswith("/") or name.startswith("../") or "/../" in name:
            raise UnsafeArchiveError(f"Unsafe archive member path: {member.name!r}")

        destination = os.path.realpath(os.path.join(base, name))
        if not _is_within(base, destination):
            raise UnsafeArchiveError(f"Archive member escapes target directory: {member.name!r}")

        if member.issym() or member.islnk():
            raise UnsafeArchiveError(f"Archive links are not allowed: {member.name!r}")

        if not (member.isfile() or member.isdir()):
            raise UnsafeArchiveError(f"Unsupported archive member type: {member.name!r}")

        safe_members.append(member)

    archive.extractall(path=base, members=safe_members)
