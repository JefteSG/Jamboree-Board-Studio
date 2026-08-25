# Board Format Research

This document tracks what is actually confirmed about Super Mario Party
Jamboree's board data format, as opposed to what is inferred, guessed, or
still completely unknown. It exists so the new `jamboree_board_studio`
domain layer never silently invents data — if something below is marked
`Unknown` or `Hypothesis`, the code must treat it as such (leave it
`None`/empty, not fabricate a value).

**Important limitation of this pass**: no real Super Mario Party Jamboree
dump is present in this repository or in the environment this research
was done in — the project intentionally never bundles game files
(`CORE/`, `ROMFS/`, `workspace/` are all gitignored), and none of this
document's authors have run the tool against a real dump while writing
it. Everything here comes from reading the existing parsers in
`editor_modules/`, `editor.py`, and `bea_archive_manager.py`. Field
*names*, *shapes*, and *observed behavior in code* are Known; their
*meaning* and *completeness* are frequently only Probably or Unknown.
Anyone with an actual extracted workspace should treat this doc as a
checklist to verify, not as ground truth.

## File layout

Known. Every board-related JSON file lives under a workspace at:

```
<workspace>/bd~bd{NN}.nx/bd/bd{NN}/data/bd{NN}_<FileType>.json
```

where `NN` is a zero-padded archive index `00`–`07`. `bd~bd00.nx` holds
data shared across all 7 boards (`ItemShop`, `ItemBag`, `ItemMass`,
`LuckyMass`, `UnluckyMass`, `HiddenBlock`, `PlayerMove`, and the
`KoopaMass` shared default under key `Map00`), while `bd~bd01.nx`
through `bd~bd07.nx` hold `MapNode`/`MapPath` for boards Map01–Map07
respectively (`editor.py`, `editor_modules/map_layout.py:get_file_path`).

The mapping from archive index to board name is:

| Archive | Map name | Board (in-game name) |
|---|---|---|
| bd01 | Map01 | Goomba Lagoon |
| bd02 | Map02 | Western Land |
| bd03 | Map03 | Mario's Rainbow Castle |
| bd04 | Map04 | Roll 'em Raceway |
| bd05 | Map05 | Rainbow Galleria |
| bd06 | Map06 | King Bowser's Keep |
| bd07 | Map07 | Mega Wiggler's Tree Party |

(`editor.py:map_items`)

## Space types ("MassAttr")

**Status: Known (partially).**

Each board's `bd{NN}_MapNode.json` has a top-level `MapNode` array. Each
entry observed in code has at least:

- `NodeNo` (int) — the space's id, referenced everywhere else as an
  adjacency/foreign key.
- `MassAttr` (string) — the space's type/category.
- `NpcNodeNo0` (int) — `-1` normally; some other value marks the node as
  "NPC-linked" and the existing editor treats it as read-only (drawn as
  a square instead of a circle, right-click edit refused). What exactly
  an NPC-linked node *is* in-game (an actual NPC's position? a
  special/blocked tile?) is **Unknown** — only its editing consequence
  in the current tool is documented in code.

Confirmed `MassAttr` values seen in `editor_modules/map_layout.py`'s
color/legend tables:

```
Item, Happening, Chance, Plus, Minus, Lucky, Unlucky, VS, Koopa,
SpotTeresa, SpotItemShopNokonoko, SpotItemShopKameck, SpotBranch,
SpotEvent, SpotBranchKey
```

Of these, only `Item, Chance, Plus, Minus, Lucky, Unlucky, VS, Koopa` are
currently editable through the tool's right-click cycle
(`mass_attr_list`); the rest are recognized (drawn/colored) but not
editable, presumably because their game-side meaning/constraints aren't
understood well enough yet to expose editing safely.

**Probably**: `MassAttr` values not in the color table at all would
still round-trip through this project's new `BoardSpace.game_data`
(nothing is dropped), but would show with a generic/default color and
type label in any new visual layer, since they aren't in the known list.

**Unknown**: whether `MapNode` entries carry any fields beyond `NodeNo`,
`MassAttr`, `NpcNodeNo0` — the existing code only ever reads those three,
so anything else present in a real file has never been inspected.
`Star`/`Boo` spaces (which the SMPJ Map Editor README lists under
"Features In Mind" as *not yet supported*) may already exist as
`MassAttr` string values in real data, or may not exist as a `MassAttr`
concept at all — needs verification against a real dump.

## Space position

**Status: Unknown (no confirmed authoritative field found).**

Files inspected: `bd{NN}_MapNode.json`, `bd{NN}_MapPath.json`, all of
`editor_modules/map_layout.py`.

No per-`MapNode` X/Y/Z or transform field is read anywhere in the
current code. What the existing "Map Layout" viewer displays as node
positions is **not** stored per-node — it's inferred, once per node, as
a side effect of walking `MapPath` segments (see below), using only the
first `Bezier` control point touching that node, and only its X/Z
components (no height/Y at all, no rotation, no scale).

This is why `jamboree_board_studio.core.board.models.BoardSpace.position`
is left `None` by the parser: it is not a confirmed real position, it's
a geometric approximation of one, derived from path data that exists for
a different purpose (drawing connections). Treating it as authoritative
position data would risk baking a wrong assumption into the new domain
model. The approximation is instead exposed separately as
`BoardSpace.visual_position`, computed by presentation code, explicitly
never written back to game files.

**Potential candidates for a future search**, not yet investigated:
files this project has never parsed at all — e.g. any 3D model/level
files that would need to reference actual node placement for rendering
purposes (course meshes, collision data). These are entirely outside
`editor_modules/`'s current scope and were not present to inspect in
this environment.

## Connections / Paths

**Status: Known structure, semantics probably correct, unverified against real game.**

`bd{NN}_MapPath.json` has a top-level `MapPath` array. Each entry has:

- `NodeNo` (int) — the source node.
- `Path` (array) — outgoing edges from that node. Each element has at
  least `NodeNo` (the **target** node for that edge) and a `Bezier`
  array.

Each `Bezier` array element observed has `Position0X`, `Position0Z`,
`Position1X`, `Position1Z` (floats) — presumably the curve's start/end
control points for that segment, only ever indexed at `[0]` by existing
code. **Unknown**: what a second/third `Bezier` array element would mean
(additional curve control points for a bent path? unused?), and whether
`Y`/height components exist alongside X/Z anywhere in this structure.

This `NodeNo -> Path[].NodeNo` structure is a real, directed adjacency
graph — already parsed, already drawn as arrows in the existing Map
Layout viewer (`FancyArrowPatch`). It is the strongest known lead for
`BoardConnection.source`/`target`, and is what
`jamboree_board_studio.core.board.parser.parse_board` uses to populate
`Board.connections`. Both the per-node `Path` entries and the per-segment
records are preserved through `BoardConnection.game_data` /
`Board.metadata["map_path_extra"]` so any field this project doesn't yet
interpret is not lost on save.

**Probably**: a `Path` array with more than one element per source node
represents branching (e.g. `SpotBranch`/`SpotBranchKey` node types,
which exist in the `MassAttr` list above) — plausible given the names,
not verified.

**Unknown**: whether edges are meant to be read as strictly directed
(A→B only) or whether the game also expects/relies on a matching reverse
entry (B→A) somewhere for bidirectional movement — current code only
ever draws single directed arrows and never checks for a reverse
counterpart.

## Events (Lucky / Unlucky / Bowser-Koopa)

**Status: Known and fully round-tripped already** (pre-existing feature,
not part of this project's new model yet). `bd00_LuckyMass_MapXX.json`,
`bd00_UnluckyMass_MapXX.json`, `bd00_KoopaMass_Map00.json` (Koopa/Bowser
events are shared across all boards except Map06/King Bowser's Keep,
which is stored under `Map06` specifically and not synced —
`editor_modules/events.py:EventDataManager.get_linked_maps`). Each entry
has `Rate0..Rate3` (float, per-turn-count independent probability
weight) and `Result` (string, drawn from a fixed known list per event
type). These are **not** currently linked to specific `MapNode` entries
in the code — i.e. no evidence yet of e.g. "this Lucky event pool
applies to node N specifically" as opposed to "this pool applies
board-wide whenever a Lucky space is landed on." This project's `Board`
model does not yet attempt to attach event pools to individual
`BoardSpace`s for that reason — doing so would be a Hypothesis, not a
Known fact.

## Hidden Blocks

**Status: Known and fully round-tripped already** (pre-existing feature).
`bd00_HiddenBlock.json`, global across all boards (not per-map), with
`No` (lot number 0–5), `Result` (int reward code — `-1` = 1 Star,
positive values = coin amounts), `Rate` (int weight). As with events, no
evidence found linking a specific hidden block entry to a specific
`MapNode` — treated as board-independent by the existing code, so not
modeled as per-space data here either.

## Shops / Item Bag / Item Mass (Item Case)

**Status: Known and fully round-tripped already** (pre-existing feature).
Not investigated further for this pass since they are unrelated to
space/path/position research and are already fully understood — see
`editor_modules/item_shop.py`, `item_bag.py`, `item_mass.py`.

## Summary table

| Structure | Status |
|---|---|
| Space id (`NodeNo`) | Known |
| Space type (`MassAttr`) | Known (partial — 8/15 seen values are editable) |
| NPC-linked flag (`NpcNodeNo0`) | Known field, Unknown meaning |
| Space real position/transform | Unknown — no field found |
| Space visual position (inferred) | Known technique, explicitly an approximation, X/Z only |
| Connections/paths (`MapPath`) | Known structure, Probably correct semantics |
| Bezier curve meaning beyond `[0]` | Unknown |
| Branching paths | Probably (plausible, unverified) |
| Directionality requirement (need reverse edge?) | Unknown |
| Event-to-space linkage | Unknown / no evidence found — treated as board-wide, not per-space |
| Hidden-block-to-space linkage | Unknown / no evidence found — treated as board-wide, not per-space |
| Models/textures/environment assets | Not investigated — out of scope this phase |
