# The Legend of Zelda: Ocarina of Time (`0400486024DEC000`)

A Switch 2 game: update v131072 over the base, surveyed from the user's `.nup` dump ([android/NUP.md](../../../android/NUP.md)), whose update package (`0400486024DEC800`, v131072) carries the whole game. SDK 22.2.8 built for the Switch 2, NVN2, NPLN 1.55.1. Nintendo EPD's engine (sead / agl / gsys, Phive, Havok, CRIWARE), modules `main` + `subsdk0` (NintendoSDK movie 22.2.8) + `sdk`. **In bring-up:** the profile holds the probe's measured identity and the engine family's memory map and shader layout — nothing of this game's run-time behaviour is measured yet. Its closest relatives here are [Mario Kart World](../0400C3F00006E000/README.md) (the same engine with virtual address memory on, whose memory map this profile starts from) and [Donkey Kong Bananza](../040074A01BF12000/README.md) (the same engine, NVN2, Ampere shader code).

The probe report (2026-11-07, run on the phone with `scripts/nup_probe_termux.sh`): RomFS 186,583 files, 24.43 GB — `TerrainArc/*` scene terrain (Gerudo Fortress, Hyrule Field, Kakariko Village, Zora's Fountain, the Graveyard, Gerudo Valley, Desert Colossus, Haunted Wasteland, Zora's River, Death Mountain trail, ...), `Tex` 8.79 GB, `Model` 2.55 GB, `Sound/Resource/Stream` 1.73 GB, `Bake/Probe/Scene` 1.76 GB, `Event/Movie` 1.53 GB, `Phive/StaticCompoundBody`, `Foliage/Placement`, `Effect`. Code: `main` 60.3 MB text / 12.0 MB ro / 5.0 MB data, bss 1.3 MB; `sdk` 8.5 / 5.8 / 0.4; `subsdk0` 0.5 / 0.2 / 0.1. The `main` and `sdk` modules store their segments as ZBIC (Nintendo's zstd variant, system 22.0.0 on) — `dm/tools/nso.py` reads them through the `zbic` package.

## What it needs

| Setting | Where | Why |
|---|---|---|
| `modules main subsdk0 sdk` | [`game.tsv`](game.tsv) | measured: the probe's module table; `rtld` is not listed, as on the other profiles |
| `sys_resource 0x3000000` | `game.tsv` | measured from main.npdm (48 MB): virtual address memory on, as Mario Kart World — `nninitStartup` sets the heap to the free application memory less a fixed reserve, so the heap request is expected in the bring-up log, not a measured map |
| `mem_reserve 0x300000000`, `mem_alias 0x100000000`, `mem_stack 0x10000000`, `app_pool 0x240000000` | `game.tsv` | **not measured**: Mario Kart World's map (the same engine and path), kept as the bring-up's starting point; the heap request and the alias fills are to be read from the phone's log |
| `shader_groups /Shader/=shader /Effect/=effect /UI/=layout` | `game.tsv` | the engine family's NVN2 layout (`Shader/*.Nin_Ounce_NVN2.bfsha.zs`, as Donkey Kong Bananza and Mario Kart World); `Effect/` is in the RomFS listing, `Shader/` and `UI/` are not among the 20 largest (they would not be) — unconfirmed until the first split |
| `zip_store .zs:.bwav:.webm:.metallib` | `game.tsv` | the engine family's set; the probe reads no file headers, so unmeasured until the first pack |

## Open

- Nothing has booted: the first phone run (Prepare, then the log) measures the memory map, the shader layout and whatever the SDK 22.2.8 host coverage misses — this is the first profile on an SDK 22 build, and `dm/tools/sdk_patches.py`'s cuts are per-SDK-build.
- `romfs_marker` names a file every EPD RomFS carries (`System/Resource/ResourceSizeTable.Product.rsizetable.zs`), but the exact name on this SDK is unconfirmed (the probe's listing holds the 20 largest top folders only); the Android flow does not read the key.
- `romfs_check`: no row yet. Donkey Kong Bananza checks line 4 of `System/RegionLangMask.txt` against main's build ID; whether this game's file carries the same line is unconfirmed.
- The display version is unknown (a `.nup` carries no control data): the build rows say `v131072` on both columns, as Pokémon Pokopia's do.
- The window size getters (`window_fn`), the render-condition and GPU-timestamp behaviour are the bring-up's to find (Mario Kart World needed `render_cond on`; the same engine suggests the same, unconfirmed here).
