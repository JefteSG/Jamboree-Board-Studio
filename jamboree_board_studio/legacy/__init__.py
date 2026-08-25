"""The original SMPJ Map Editor implementation, kept working as-is.

Everything under here (``editor_modules/``) predates the
``jamboree_board_studio`` domain layer and is being migrated onto it
gradually rather than rewritten — see ``core/`` for the format-independent
models/adapters and ``ui/`` for the new widgets that consume them.
Nothing in ``legacy`` should gain new features; it stays here as the
proven, working baseline while ``core``/``services``/``ui`` grow around it.
"""
