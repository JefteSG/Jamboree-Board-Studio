"""Validate every board in a workspace before it is exported.

This is the domain-layer piece of "before export: validate the data,
detect invalid references, detect missing files" — kept free of Tkinter
so it can run and be tested headlessly. The UI layer (``main.py``) is
responsible only for presenting the result and deciding whether to abort
the export.
"""

from __future__ import annotations

from dataclasses import dataclass

from jamboree_board_studio.core.board.parser import (
    KNOWN_MAP_NAMES,
    BoardParseError,
    parse_board,
)
from jamboree_board_studio.core.board.validator import validate_board


@dataclass
class WorkspaceValidationResult:
    map_name: str
    messages: list[str]


def validate_workspace_boards(workspace_path: str) -> list[WorkspaceValidationResult]:
    """Validate MapNode/MapPath data for every known board in a workspace.

    Returns one ``WorkspaceValidationResult`` per map that has at least
    one problem — either its data couldn't be read at all (missing or
    invalid MapNode/MapPath file) or it read fine but failed structural
    validation (duplicate space ids, dangling connection references).
    Maps with no problems are omitted, so an empty list means "all clear".
    """
    results: list[WorkspaceValidationResult] = []

    for map_name in KNOWN_MAP_NAMES:
        try:
            board = parse_board(workspace_path, map_name)
        except BoardParseError as error:
            results.append(
                WorkspaceValidationResult(
                    map_name=map_name,
                    messages=[f"Could not read board data: {error}"],
                )
            )
            continue

        issues = validate_board(board)
        if issues:
            results.append(
                WorkspaceValidationResult(
                    map_name=map_name,
                    messages=[issue.message for issue in issues],
                )
            )

    return results
