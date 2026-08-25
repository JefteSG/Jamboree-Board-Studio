"""Pure, testable orchestration logic pulled out of the Tkinter entry points.

``main.py`` cannot be imported by this project's test suite at all — it
unconditionally initializes a pythonnet/.NET runtime at module load (via
``bea_archive_manager``), which this environment doesn't have. Anything
in ``main.py`` that is genuinely just file-system bookkeeping (no
Tkinter dialogs, no BEA archive calls) belongs here instead, where it
can be tested headlessly; ``main.py`` stays the thin shell that wires
these functions to buttons and dialogs.
"""
