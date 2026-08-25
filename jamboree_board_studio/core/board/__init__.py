"""Internal Board domain model, plus adapters to/from the original game JSON format.

``models`` defines the format-independent representation. ``parser`` and
``serializer`` are adapters that convert between that representation and
the existing on-disk workspace layout (``bd~bdXX.nx/bd/bdXX/data/*.json``),
reusing the already-understood loaders in ``jamboree_board_studio.legacy.editor_modules.map_layout``
rather than re-implementing them.
"""

from jamboree_board_studio.core.board.models import Board, BoardConnection, BoardSpace

__all__ = ["Board", "BoardConnection", "BoardSpace"]
