"""Structural validation for the Board model.

This checks only structure (duplicate ids, dangling connection
references) — it does not know game-specific semantic rules (e.g. that
Lucky/Unlucky/Koopa event rate totals must sum correctly; that check
already exists in ``jamboree_board_studio.legacy.editor_modules.events.EventDataManager`` and is out
of scope here). The intent is to give a future export step a way to flag
an obviously broken board before writing it back into game files.
"""

from __future__ import annotations

from dataclasses import dataclass

from jamboree_board_studio.core.board.models import Board


@dataclass
class ValidationIssue:
    severity: str  # "error" or "warning"
    message: str


def validate_board(board: Board) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    seen_ids: set[str] = set()
    for space in board.spaces:
        if space.id in seen_ids:
            issues.append(ValidationIssue("error", f"Duplicate space id: {space.id!r}"))
        seen_ids.add(space.id)

    for connection in board.connections:
        if connection.source not in seen_ids:
            issues.append(
                ValidationIssue(
                    "error",
                    f"Connection references unknown source space: {connection.source!r}",
                )
            )
        if connection.target not in seen_ids:
            issues.append(
                ValidationIssue(
                    "error",
                    f"Connection references unknown target space: {connection.target!r}",
                )
            )

    return issues


def is_valid(board: Board) -> bool:
    return not any(issue.severity == "error" for issue in validate_board(board))
