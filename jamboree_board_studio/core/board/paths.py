"""Shared workspace file-path convention for board layout data.

Mirrors the convention already used by ``editor_modules.map_layout``
(``get_file_path``): ``bd~bdXX.nx/bd/bdXX/data/bdXX_<FileType>.json``.
Kept here, independent of that module, so ``core.board`` does not pull in
its tkinter/matplotlib dependencies (see parser.py for why).
"""

from __future__ import annotations

import os


def map_layout_file_path(workspace_path: str, map_name: str, file_type: str) -> str:
    map_index = int(map_name.replace("Map", ""))
    return os.path.join(
        workspace_path,
        f"bd~bd{map_index:02d}.nx",
        "bd",
        f"bd{map_index:02d}",
        "data",
        f"bd{map_index:02d}_{file_type}.json",
    )
