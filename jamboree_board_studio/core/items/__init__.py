"""Format-independent models and adapters for the game's "loot table" style
data: Hidden Blocks, Item Bag, Item Mass (Item Case).

Each submodule follows the same shape as ``core.board``: a small
dataclass, a ``parse_*`` function (file -> model, raising a dedicated
``*ParseError`` rather than silently returning empty data), and a
``serialize_*`` function (model -> file) that writes every entry's
``game_data`` back with only the known fields synced, so unrecognized
keys survive a parse -> edit -> serialize cycle.

These are additive: the existing widgets in ``editor_modules/`` are
untouched and keep doing their own file IO exactly as before.
"""
