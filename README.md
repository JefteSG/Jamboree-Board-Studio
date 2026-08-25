# Jamboree Board Studio

**Jamboree Board Studio** is an open-source, community-driven tool for viewing and editing
**Super Mario Party Jamboree** board data, evolving towards a full visual board editor.

## Fork notice

Jamboree Board Studio is a **fork of [SMPJ Map Editor](https://github.com/MH13-YT/SMPJ-Map-Editor)**,
originally created by **[MH13-YT](https://github.com/MH13-YT)** (also published on
[GameBanana](https://gamebanana.com/wips/88664)). All of the original project's data-editing
features are preserved here as the starting point for this fork's longer-term goal: a friendly,
visual board editor conceptually closer to tools like
[Party Studio](https://github.com/MapStudioProject/Party-Studio) — open a board, see its spaces
and connections graphically, edit properties by clicking on them, and, eventually, build boards
from scratch. That vision is being pursued incrementally and only as far as the game's data
formats are actually understood; see [`docs/research/board-format.md`](docs/research/board-format.md)
for what is currently confirmed versus still unknown.

This fork continues under the same license as the original project — **GPLv3** — and remains
fully open-source.

## Disclaimer

This software is a **fan-made tool** developed for educational and modding purposes.
It is **not affiliated with, endorsed by, or sponsored by Nintendo** or the developers of
*Super Mario Party Jamboree*. Use at your own risk.

Jamboree Board Studio **does not distribute any game files**. It only edits data you provide:
you must supply your own **legally obtained** dump of the game. No ROM, ISO, or other
copyrighted game asset is included in this repository or in any release of this tool, and none
will be provided by this project.

**⚠️ THIS TOOL IS NOT (YET) A FULL MAP MAKER**  
> Board space *positions* and map textures are **not** editable today — the underlying data for
> real, authoritative space positions has not been confirmed yet (see the research doc linked
> above). Support for repositioning spaces, editing paths, and importing models/textures is a
> long-term goal, not a current feature.
> Until then, consider this a **rudimentary board data editor** that is gradually growing towards
> that goal, rather than a finished 3D map maker.

---

## Usage in Mods

You are free to use Jamboree Board Studio to create board modifications **without any restrictions**.
The tool outputs are fully yours to distribute in your mods.

**Project credit is greatly appreciated** (though not legally required). As this is a fork, credit
to either project (or both) is welcome:

`Board data edited with SMPJ Map Editor`  
**[GitHub](https://github.com/MH13-YT/SMPJ-Map-Editor)** | **[GameBanana](https://gamebanana.com/wips/88664)**

`Board data edited with Jamboree Board Studio`  
**[GitHub](https://github.com/JefteSG/Jamboree-Board-Studio)**

---

## Features

### ⚠️ WARNING

Since **version 1.1.0**, the software uses **pythonnet** (.NET/Mono) along with **BezelEngineArchive_Lib** to extract and repack Bezel Engine Archive files.
> **Note:**  
> This tool relies on an **external C# library**:  
> [KillzXGaming/BEA-Library-Editor – BezelEngineArchive_Lib](https://github.com/KillzXGaming/BEA-Library-Editor/tree/master/BezelEngineArchive_Lib)  
> This library is **automatically downloaded on the first launch** of the application.
> **Implemented for Windows with .NET 8** (tested and working). **Mono support implemented but untested.**

---

### Current Features

- Edit items obtainable in shops (**Koopa and Kamek shops only**, Rainbow Galleria shops is not supported).  
- Edit items obtainable from **Item Bags**.  
- Edit items obtainable from **Item Cases** (can also remove item minigames).  
- Edit **events** (Lucky, Unlucky, Bowser).  
- Edit **hidden blocks**.  
- Edit **board spaces** (change types such as Blue, Red, Lucky, Unlucky, Bowser, Chance Time, etc.).

---

### Planned Features

No new features are planned at the moment.

---

### Features In Mind

- Change paths.  
- Add support for **Boo spaces**.
- Add support for **Star spaces**.

---

## How to Install

### Prerequistes
- A **complete dump** of the *Super Mario Party Jamboree* romfs folder *(you must obtain this by yourself)*.  
- Internet connection enabled during the first start so the tool can **automatically download the C# library**.

### Option 1 — Using Releases (Recommended)

1. Download the latest version from the project’s **[Releases](https://github.com/.../releases)** page.  
2. Extract the downloaded archive.  
3. Run the included `.exe` file.

> ⚠️ **Note:** builds created with **PyInstaller** can be flagged as **false positives** by some antivirus software.  
> The project is fully open-source — feel free to inspect the code before running it.

---

### Option 2 — Run from Source Code

#### Additional Prerequisites
- **Python** installed with **Tkinter** (required to launch the GUI if running from source).  
  Check the `.python-version` file for the latest supported Python version.  

#### Install dependencies

Use: pip install -r requirements.txt

---

## Architecture & Development

The original editor's logic (`main.py`, `editor.py`, `bea_archive_manager.py`,
`editor_modules/`) is preserved as-is and keeps working unchanged. A new,
format-independent domain layer is being introduced gradually under
`jamboree_board_studio/`, starting with an internal `Board` model
(`jamboree_board_studio/core/board/`) and adapters that convert to/from the
existing game JSON without inventing data the format doesn't confirm — see
[`docs/research/board-format.md`](docs/research/board-format.md) for what is
currently known, probable, or still unknown about the board format.

### Running the tests

```
pip install -r requirements-dev.txt
python -m pytest tests/
```

`tests/core/` covers the domain layer (`Board` model, parser, serializer,
round-trip, validation) and has no Tkinter/pythonnet dependency, so it runs
headlessly anywhere. `tests/integration/` drives the real Tkinter editor
(the Board Workspace tab specifically) and needs a working Tk display — it
skips itself automatically (rather than failing) when Tkinter isn't
installed or no display is available, e.g. `xvfb-run -a python -m pytest
tests/` on headless Linux, or just `python -m pytest tests/` on Windows/macOS
or any desktop with a display.

---

## Credits

- **[MH13-YT](https://github.com/MH13-YT)** - original creator of [SMPJ Map Editor](https://github.com/MH13-YT/SMPJ-Map-Editor) (GPLv3), the project this fork is based on. See the [Fork notice](#fork-notice) above.
- **KillzXGaming** - for [BezelEngineArchive_Lib](https://github.com/KillzXGaming/BEA-Library-Editor/tree/master/BezelEngineArchive_Lib) (GPLv3)

---

### License

This project is licensed under the terms of the **GNU General Public License v3 (GPLv3)**.  
You are free to use, modify, and distribute this software under the same license terms.  
See the file [LICENSE](./LICENSE) for the complete text of the GPLv3.

Because this project interfaces directly with the **BezelEngineArchive_Lib** library (licensed under GPLv3),  
Jamboree Board Studio adopts the same license to maintain compatibility.

---
