# Board Format Research

This document tracks what is actually confirmed about Super Mario Party
Jamboree's board data format, as opposed to what is inferred, guessed, or
still completely unknown. It exists so the new `jamboree_board_studio`
domain layer never silently invents data — if something below is marked
`Unknown` or `Hypothesis`, the code must treat it as such (leave it
`None`/empty, not fabricate a value).

**Provenance note (update)**: the original pass below was written with no
real Super Mario Party Jamboree dump available — the project
intentionally never bundles game files (`CORE/`, `ROMFS/`, `workspace/`
are all gitignored), so everything was inferred from reading the
existing parsers in `editor_modules/`, `editor.py`, and
`bea_archive_manager.py`. A later pass (marked **"(verified against real
dump)"** below) checked the specific `Unknown`/`Probably` claims about
`MapNode`/`MapPath` structure against a real extracted workspace, in an
environment that had the game's files but did not retain or ship them —
only schema-level facts (field names, value inventories, counts, JSON
shapes) came out of that pass, never asset content itself. Anywhere not
marked as verified is still exactly as uncertain as the original pass
left it — treat those as a checklist to verify, not as ground truth.

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

**Status: Known (verified against real dump).**

Each board's `bd{NN}_MapNode.json` has a top-level `MapNode` array.
**Confirmed exhaustive key set** for a `MapNode` entry (union across all
7 boards, real dump — the "whether entries carry fields beyond
`NodeNo`/`MassAttr`/`NpcNodeNo0`" question below is now answered: yes,
and here is the full set):

```
AuxNodeNo0, AuxNodeNo1, AuxParam0, AuxParam1, AuxParam2, AuxParam3,
BranchNodeNo0, BranchNodeNo1, MapNodeNo0, MapNodeNo1,
MarkNodeNo0, MarkNodeNo1, MarkNodeNo2, MarkNodeNo3,
MassAttr, MassFlag, NextNodeNo, NodeNo, NpcNodeNo0, NpcNodeNo1,
PrevNodeNo, SettingTrapEvaluation, Teresa, TrapBoard
```

None of the `AuxParam*`/`BranchNodeNo*`/`MapNodeNo*`/`MarkNodeNo*`/
`MassFlag`/`SettingTrapEvaluation`/`Teresa`/`TrapBoard` fields are read
anywhere in existing code — their meaning is still **Unknown**, only
their existence and name are now confirmed. `NpcNodeNo0`'s *meaning* is
likewise still Unknown (still just "-1 normally, editor treats non–-1 as
read-only"), only its presence in every real node was already known.

**Confirmed `MassAttr` value inventory** (real counts across all 7
boards, most to least common):

| Value | Count | In code's color table? | Editable via right-click cycle? |
|---|---|---|---|
| `""` (empty string) | 1190 | No | No |
| `Plus` | 204 | Yes | Yes |
| `Lucky` | 116 | Yes | Yes |
| `Happening` | 63 | Yes | No |
| `Item` | 56 | Yes | Yes |
| `SpotEvent` | 45 | Yes | No |
| `Minus` | 36 | Yes | Yes |
| `SpotBranch` | 30 | Yes | No |
| `VS` | 20 | Yes | Yes |
| `Unlucky` | 16 | Yes | Yes |
| `Koopa` | 15 | Yes | Yes |
| `Chance` | 13 | Yes | Yes |
| `SpotTeresa` | 10 | Yes | No |
| `SpotItemShopNokonoko` | 8 | Yes | No |
| `Start` | 7 | No | No |
| `SpotItemShopKameck` | 7 | Yes | No |
| `Spot` (no suffix) | 6 | No | No |
| `SpotBranchKey` | 4 | Yes | No |

Two findings not previously documented anywhere in code or this doc:

- The empty string `""` is not a rare edge case — it is the **dominant**
  value (~65% of all spaces across the game). It represents whatever a
  "plain" space is (no modifier), and it is *not* in `mass_attr_list`,
  so the existing right-click cycle can't reach it (a blank space can't
  currently be turned into `Chance`/`Unlucky`/etc. through that
  mechanism; only already-non-blank editable-type spaces can be
  reassigned among each other). Same for `Start` (the board's starting
  space, 1 per board as expected, 7 total) — also absent from both the
  color table and the editable list.
- `Spot` (the bare word, no `Event`/`Branch`/`Teresa`/`ItemShop*` suffix)
  is a real, distinct value seen 6 times — it does not match anything in
  `editor_modules/map_layout.py`'s tables at all, not even as a
  recognized-but-uneditable color entry. Its meaning is Unknown.

**Confirmed absent**: `Star` and `Boo` do not appear as `MassAttr`
values anywhere in the real dump checked. The README's "Features In
Mind: Star/Boo spaces, not yet supported" note is consistent with
this — if those exist in-game at all, they are not represented as a
static `MassAttr` string on a `MapNode`, at least not under those exact
names.

## Space position

**Status: `MapNode` has no position field — confirmed against real dump.
A real candidate field for actual 3D position exists on `MapPath`
Bezier data, previously undocumented; whether it's authoritative is
still Hypothesis.**

Files inspected: `bd{NN}_MapNode.json`, `bd{NN}_MapPath.json`, all of
`editor_modules/map_layout.py`.

The exhaustive `MapNode` key list confirmed in the section above has no
X/Y/Z or transform field of any kind — this is now a confirmed fact
about real data, not just "not read by any code we found". What the
existing "Map Layout" viewer displays as node positions is **not**
stored per-node — it's inferred, once per node, as a side effect of
walking `MapPath` segments (see below), using only the first `Bezier`
control point touching that node, and only its X/Z components.

**Update**: "no height/Y at all" (the original claim here) is **wrong**
— see the Connections/Paths section below. The real `Bezier` structure
has full X/Y/Z for two *different* kinds of point (`Position0/1` and
`Anchor0/1`), only the existing code has only ever read
`Position0X`/`Position0Z`. This means real 3D position data — including
height — exists somewhere in the file the visual layer already parses;
it's just never been extracted or interpreted as such. Whether
`Anchor`/`Position` correspond to "the actual point on the curve" vs.
"a control handle" (standard Bezier terminology would suggest `Anchor`
= on-curve, `Position` = control point, but this is a guess from the
field names alone, not verified against rendering behavior) — and
whether either one is a trustworthy stand-in for "where this node really
is in 3D space" as opposed to being purely local to that one path
segment's curve shape — is **Hypothesis, not Known**. Worth a follow-up
pass: compare `Anchor`/`Position` values from *every* edge touching a
given `NodeNo` — if they agree closely across edges, that's real
evidence the node has one true position; if they diverge, they're
probably just curve-local geometry.

This is why `jamboree_board_studio.core.board.models.BoardSpace.position`
is left `None` by the parser: even with the above, it is not yet a
*confirmed* real position, only a promising unverified lead. Treating it
as authoritative position data before that follow-up would risk baking a
wrong assumption into the new domain model. The approximation already in
use is instead exposed separately as `BoardSpace.visual_position`,
computed by presentation code, explicitly never written back to game
files.

**Potential candidates for a future search**, still not investigated:
any 3D model/level files that would need to reference actual node
placement for rendering purposes (course meshes, collision data). These
are entirely outside `editor_modules/`'s current scope.

## Connections / Paths

**Status: Structure confirmed against real dump (including two fields
this doc previously didn't know existed); semantics still probably
correct but unverified against real game behavior.**

`bd{NN}_MapPath.json` has a top-level `MapPath` array. Each entry has:

- `NodeNo` (int) — the source node.
- `Path` (array) — outgoing edges from that node.

**Confirmed exhaustive key set for a `Path[]` edge** (real dump, all 7
boards): `NodeNo, Attribute, Length, Bezier`. `Attribute` and `Length`
were not previously documented here at all — the existing code only
ever reads `NodeNo` and `Bezier`.

- `Attribute` (int): real values are `0` (736 edges, ~72%), `1` (214,
  ~21%), `2` (79, ~7%) across the whole game. This is a real, common
  category, not a rare/degenerate case — meaning of each value is
  Unknown, but `2` is common enough that it should not be assumed
  invalid or a "special/broken" marker by default.
- `Length` (number): present on every edge; not yet cross-checked
  against the actual geometric length implied by its `Bezier` data —
  Unknown whether it's derived/redundant or authoritative.

**Confirmed exhaustive key set for a `Bezier` array element**: `Anchor0X,
Anchor0Y, Anchor0Z, Anchor1X, Anchor1Y, Anchor1Z, Position0X, Position0Y,
Position0Z, Position1X, Position1Y, Position1Z, Length, Ratio`. This
corrects the original claim in this doc — see Space Position above:
`Y` components exist for **both** `Position` and a previously
undocumented second point pair, `Anchor`. The existing visual layer only
ever reads `Position0X`/`Position0Z`, ignoring `Position0Y`,
`Position1*`, all of `Anchor*`, and the edge-level `Ratio`.

**Confirmed: the `Bezier` array is (almost) never more than 1 element.**
Real distribution across all 1029 edges in the game: exactly 1028 edges
have a 1-element `Bezier` array, and exactly **1** edge has a 0-element
(empty) array. That one edge is also the sole dangling connection found
during this pass (see callout below) — so in practice, "what would a
2nd/3rd Bezier element mean" is moot for this real dump: it never
happens. The array wrapper may just be this format's way of nesting a
single struct, or a leftover from a differently-shaped format elsewhere.

**Known real-data anomaly, worth carrying forward**: exactly one edge in
the entire game (found on the Map03/Mario's Rainbow Castle board) has
`Attribute: 2`, `Length: 0`, an empty `Bezier` array, and a target
`NodeNo` that does not exist in that board's own `MapNode` list — i.e. a
genuinely dangling reference, present in the untouched original game
data (not introduced by this project's tooling). This is exactly the
kind of edge case `jamboree_board_studio.core.board.validator` is
designed to catch, and it does — `validate_workspace_boards` correctly
flags it before export. Whether the game itself silently ignores such
edges at runtime (most likely, since the game obviously runs fine) or
whether `Attribute: 2` + zero-length + empty-Bezier is itself a
recognized "this edge is inert, don't render/traverse it" pattern worth
special-casing in the validator is Unknown — for now this is correctly
treated as a real (if harmless) data quirk, not a project bug.

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
| `MapNode` full key set (23 fields) | **Known, verified** — 19 of 23 fields still have Unknown meaning |
| Space type (`MassAttr`) | **Known, verified** — 18 real values inventoried; 8 editable, 2 (`""`, `Start`) common but unreachable via the tool, 1 (`Spot`) undocumented anywhere |
| `Star`/`Boo` as `MassAttr` | **Confirmed absent** from real dump under those names |
| NPC-linked flag (`NpcNodeNo0`) | Known field, Unknown meaning |
| Space real position/transform on `MapNode` | **Confirmed absent** — no field found in the exhaustive real key set |
| 3D position candidate on `MapPath` Bezier (`Anchor`/`Position`, incl. Y) | **New finding** — fields confirmed to exist; whether authoritative is Hypothesis |
| Space visual position (inferred, current code) | Known technique, explicitly an approximation, X/Z only (leaves `Y`/`Anchor*` on the table) |
| Connections/paths (`MapPath`) top-level | Known structure, Probably correct semantics |
| `Path[]` edge full key set (`NodeNo, Attribute, Length, Bezier`) | **Known, verified** — `Attribute`/`Length` newly documented, meaning still Unknown |
| Bezier array element count | **Confirmed**: 1 element in 1028/1029 real edges, 0 in exactly 1 (the dangling Map03 edge) |
| Dangling connection (Map03 → nonexistent node `301`) | **Confirmed real, pre-existing game-data quirk**, correctly caught by `validate_workspace_boards` |
| Branching paths | Probably (plausible, unverified) |
| Directionality requirement (need reverse edge?) | Unknown |
| Event-to-space linkage | Unknown / no evidence found — treated as board-wide, not per-space |
| Hidden-block-to-space linkage | Unknown / no evidence found — treated as board-wide, not per-space |
| Models/textures/environment assets | Not investigated — out of scope this phase |
