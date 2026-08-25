"""Format-independent internal representation of a Super Mario Party Jamboree board.

These dataclasses are deliberately conservative about what they claim to
know. See ``docs/research/board-format.md`` for what is actually confirmed
about the underlying game format versus what is inferred or unknown.

Round-trip safety rule: every field of the original game JSON that this
model does not explicitly understand must still survive a
parse -> edit -> serialize cycle. That is what ``game_data`` is for on
both ``BoardSpace`` and ``BoardConnection`` — it holds the original raw
dict (or a copy of it) for that entity, so unknown keys are preserved
even though this model does not interpret them.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BoardSpace:
    """A single space ("node") on a board.

    Attributes:
        id: Stable identifier for this space. Currently the string form
            of the game's ``NodeNo``.
        type: The space's known type/category. Currently the game's
            ``MassAttr`` string (e.g. "Lucky", "Unlucky", "Chance").
            Not all values the game uses are editable yet — see the
            research doc.
        game_data: The original, untouched game record for this space
            (e.g. the full ``MapNode`` entry). Edits made through this
            model should be written back into this dict so unrecognized
            fields are preserved on save.
        position: The space's real, authoritative position in the game's
            coordinate space, if and when that is confirmed. As of this
            writing no per-node position/transform field has been
            positively identified in the parsed data, so this stays
            ``None`` — it must never be fabricated from inferred data.
        visual_position: A 2D position used *only* for on-screen layout
            in the Board Studio canvas. It may be inferred (e.g. from
            path geometry) or computed by a layout algorithm. It is a
            presentation concern, not game data, and must never be
            written back to game files.
    """

    id: str
    type: str
    game_data: dict = field(default_factory=dict)
    position: tuple[float, float, float] | None = None
    visual_position: tuple[float, float] | None = None


@dataclass
class BoardConnection:
    """A directed connection ("path segment") from one space to another.

    Attributes:
        source: id of the origin ``BoardSpace``.
        target: id of the destination ``BoardSpace``.
        game_data: The original raw path-segment record (e.g. a ``Path``
            entry, including its ``Bezier`` control points), preserved
            so unknown fields survive a save.
    """

    source: str
    target: str
    game_data: dict = field(default_factory=dict)


@dataclass
class Board:
    """A full board (one in-game map/course).

    ``spaces`` and ``connections`` may legitimately be empty: when the
    underlying data for a board cannot be parsed, or a given game format
    has no confirmed notion of connections yet, this model does not
    invent placeholder data — it represents "unknown" as an empty list,
    not as guessed content.
    """

    id: str
    name: str
    spaces: list[BoardSpace] = field(default_factory=list)
    connections: list[BoardConnection] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def get_space(self, space_id: str) -> BoardSpace | None:
        for space in self.spaces:
            if space.id == space_id:
                return space
        return None

    def connections_from(self, space_id: str) -> list[BoardConnection]:
        return [c for c in self.connections if c.source == space_id]
