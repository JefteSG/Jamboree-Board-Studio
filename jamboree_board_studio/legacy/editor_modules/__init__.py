"""Per-feature Tkinter editors (shops, items, events, hidden blocks, map layout).

Each module here pairs a widget class with load_*/save_* functions for
its slice of the workspace's JSON files. The load_*/save_* functions
increasingly delegate to jamboree_board_studio.core's format-independent
parsers/serializers (see each module's own docstring for which); the
widget classes themselves are unmodified from the original project.
"""
