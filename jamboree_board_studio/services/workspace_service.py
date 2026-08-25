"""Pure workspace file-system logic extracted from main.py.

Every function here is plain ``os``/``shutil``/``hashlib``/``filecmp``
work with no Tkinter or pythonnet dependency, so — unlike ``main.py``
itself — it can be tested headlessly. See ``jamboree_board_studio.services``'s
own docstring for why that split exists.
"""

from __future__ import annotations

import filecmp
import hashlib
import os


def calculate_checksum_for_directory(directory: str) -> str:
    """SHA-256 over every file's contents under directory, in a stable (sorted) order."""
    sha256 = hashlib.sha256()
    for root, _, files in sorted(os.walk(directory)):
        for file in sorted(files):
            file_path = os.path.join(root, file)
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
    return sha256.hexdigest()


def is_valid_workspace_name(name: str) -> bool:
    """A workspace name must be a plain directory name, not a path.

    Rejects anything that would let ``os.path.join(workspace_dir, name)``
    escape ``workspace_dir`` — a path separator, ``"."``, ``".."``, or an
    empty (post-strip) name.
    """
    name = name.strip()
    return bool(name) and os.path.basename(name) == name and name not in (".", "..")


def list_workspaces(workspace_dir: str) -> list[str]:
    """Names of every existing workspace (subdirectories of workspace_dir)."""
    return [
        d for d in os.listdir(workspace_dir) if os.path.isdir(os.path.join(workspace_dir, d))
    ]


def compute_repack_instructions(workspace_path: str, core_dir: str) -> dict[str, list[dict]]:
    """Find every file in workspace_path that differs from its CORE_DIR original.

    Returns ``{bea_archive_name: [{"source": ..., "destination": ...}, ...]}``,
    grouped by the top-level ``"bd~bdXX.nx"``-style directory each changed
    file lives under — ``bea_archives_repacker``'s own grouping
    convention. This is exactly what ``export_workspace`` needs to decide
    what to repack; pulling it out of that function's body makes it
    directly testable instead of only reachable through the full,
    untestable-here export flow.
    """
    instructions: dict[str, list[dict]] = {}
    for current_root, _, file_list in os.walk(workspace_path):
        for file_name in file_list:
            modified_file_path = os.path.join(current_root, file_name)
            relative_file_path = os.path.relpath(modified_file_path, workspace_path)
            original_file_path = os.path.join(core_dir, relative_file_path)

            if not os.path.exists(original_file_path) or not filecmp.cmp(
                original_file_path, modified_file_path, shallow=False
            ):
                parts = relative_file_path.split(os.sep)
                bea_name = parts[0]
                inner_rel = os.path.join(*parts[1:])
                instructions.setdefault(bea_name, []).append(
                    {"source": modified_file_path, "destination": inner_rel}
                )
    return instructions


def export_package_paths(output_path: str, workspace_name: str) -> list[str]:
    """Standard mod-manager install locations a successful export copies romfs/ into."""
    return [
        os.path.join(
            output_path,
            "Simple Mod Manager (SMM)",
            "mods",
            "Super Mario Party Jamboree",
            workspace_name,
            "contents",
            "0100965017338000",
            "romfs",
        ),
        os.path.join(
            output_path,
            "RYUJINX",
            "mods",
            "contents",
            "0100965017338000",
            workspace_name,
            "romfs",
        ),
        os.path.join(
            output_path, "YUZU", "load", "0100965017338000", workspace_name, "romfs"
        ),
    ]
