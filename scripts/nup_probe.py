#!/usr/bin/env python3
# A first look at a game's .nup dump (android/NUP.md) whose title has no profile yet (docs/agents/README.md "Checklist for a new title", step 1):
# the packages it holds, the surveyed package's code modules with their build IDs, main.npdm's program ID and system resource, the SDK and engine
# markers dm/games/profile_guess.py finds in the code, a RomFS top-level listing (paths and sizes; no file contents are read), and a draft
# dm/games/<title ID>/game.tsv with the measured rows (the bring-up fills the rest: memory, shaders, window — every number is measured, not assumed).
# The .nup is only ever read, and no keys are needed (a .nup is a user's decrypted dump). Run it from a repository checkout.
#
# Usage: nup_probe.py <file>.nup [--version N] [--no-romfs] [--out FILE]   (exit 1 on error)
#   --version N  survey that update's NCM version (e.g. 131072); default: the highest update, else the base
#   --no-romfs   skip the RomFS walk (a huge update on a slow disk)
#   --out FILE   also write the report there
# Facts come from profile_guess.facts_of run in place on the .nup's ExeFS (every module is decompressed once in memory); its RomFS manifest is
# written here from the TOC (path, size, an empty head), so the report's sizes and extensions are real but the header-magic counts stay empty.
# The Python needs a zstd reader (3.14's compression.zstd, or backports.zstd) when the .nup stores compressed files; most do.
import argparse, sys, tempfile, time
from pathlib import Path as FsPath

REPO = FsPath(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'dm/tools')); sys.path.insert(0, str(REPO / 'dm/games'))
import romfs   # the access layer: a path with .nup: reads inside the container (android/NUP.md)
import nup
import profile_guess as pg


def say(s): print(s, flush=True)


def zstd_note():
    try: nup.zstd(); return 'zstd: available'
    except nup.Error: return '[RED] zstd: no reader (Python 3.14, or pip install backports.zstd) — a .nup with compressed files will fail to open'


def pick(img, version):
    base = [p for p in img.packages if p.kind == nup.BASE]
    ups = sorted((p for p in img.packages if p.kind == nup.UPDATE), key=lambda p: p.version)
    if version is not None:
        hits = [p for p in ups if p.version == version]
        if not hits: raise SystemExit(f'{img.path}: no update of version {version} (has: {", ".join(p.selector for p in ups) or "none"})')
        return hits[0]
    if ups: return ups[-1]
    if base: return base[0]
    raise SystemExit(f'{img.path}: no base and no update package to survey (has only add-ons? pass one: the probe surveys a game package)')


def header_facts(exefs):
    """The facts a damaged or exotic module cannot take away: build ID, segment sizes and bss straight from each NSO header (no dynsyms, no strings)"""
    F = {'mods': {}, 'markers': {}, 'sdkver': set(), 'comps': set(), 'unity': set(), 'glslc': 0, 'glsl_src': 0, 'gl_names': 0, 'gl_src': 0, 'sysres': 0, 'program': None}
    for p in sorted(romfs.Path(str(exefs)).iterdir()):
        with romfs.open(str(p), 'rb') as fh:
            if fh.read(4) != b'NSO0': continue
        import nso
        m = nso.load(romfs.Path(str(p)).read_bytes(), str(p))
        F['mods'][romfs.Path(str(p)).name] = {'bid': m.build_id[:0x10].hex(), 'sizes': [sz for _, sz in m.segments], 'bss': m.bss, 'kind': '?'}
    F['sysres'], F['program'] = pg.npdm(str(romfs.Path(str(exefs)) / 'main.npdm'))
    return F


def facts(exefs, romarg):
    """facts_of in place on the .nup; a module it refuses (damaged, no MOD0 a tool needs) degrades to the header facts with a red note"""
    try:
        return pg.facts_of(exefs, romarg), None
    except Exception as e:   # the survey's own tools raise loudly on damaged code; the probe still reports what a header tells
        return header_facts(exefs), f'[RED] profile_guess.facts_of refused this dump ({type(e).__name__}: {e}): the report has build IDs and sizes only (no imports, SDK strings or markers). The bring-up tools (insn_census.py, nso_syms.py) will name the module and the damage.'


def walk_stats(romfs_root):
    """(files, bytes, {first-level dir: (files, bytes)}, {first/second-level prefix: (files, bytes)}) of a RomFS, from the TOC (no content reads)"""
    files, total, tops, tops2 = 0, 0, {}, {}
    top = str(romfs_root)
    for d, dirs, names in romfs.walk(top):
        rel_d = d[len(top):].lstrip('/')   # romfs.walk (os.walk's shape) prefixes every dir after the first with top
        for name in names:
            rel = f'{rel_d}/{name}' if rel_d else name
            size = romfs.stat(f'{top}/{rel}').st_size
            files += 1; total += size
            parts = rel.split('/')
            t = '/'.join(parts[:2]) if len(parts) > 2 else parts[0] if len(parts) > 1 else '(root)'
            f, b = tops.get(t, (0, 0)); tops[t] = (f + 1, b + size)
            t2 = '/'.join(parts[:3]) if len(parts) > 3 else t
            f, b = tops2.get(t2, (0, 0)); tops2[t2] = (f + 1, b + size)
    return files, total, tops, tops2


def main():
    ap = argparse.ArgumentParser(description="Survey a .nup dump whose title has no game profile yet (a draft game.tsv comes out; see android/NUP.md and docs/agents)")
    ap.add_argument('file', type=FsPath, help="the .nup file (lower case extension)")
    ap.add_argument('--version', type=int, default=None, help="the update's NCM version to survey (default: the highest, else the base)")
    ap.add_argument('--no-romfs', action='store_true', help='skip the RomFS walk (a huge update on a slow disk)')
    ap.add_argument('--out', type=FsPath, default=None, help='also write the report there')
    args = ap.parse_args()
    f = args.file.resolve()
    if f.suffix != '.nup': raise SystemExit(f'{f.name}: not a .nup file (the extension is lower case: the tools and the app split at ".nup:", so rename it)')
    say(f'# NUP probe: {f}')
    say(f'- {zstd_note()}')
    t0 = time.time()
    img = nup.open_nup(str(f))
    say(f'- opened in {time.time() - t0:.1f}s; packages:')
    for p in img.packages:
        say(f'  {p.selector or nup.KINDS[p.kind]}\t{p.title_id:016X}\tv{p.version}\texefs={"yes" if p.exefs != nup.NONE else "no"}\tromfs={"yes" if p.romfs != nup.NONE else "no"}')
    pkg = pick(img, args.version)
    say(f'- surveying: {pkg.selector} ({nup.KINDS[pkg.kind]} of {pkg.title_id:016X}, v{pkg.version})')
    if pkg.exefs == nup.NONE: raise SystemExit(f'{pkg.selector}: the package has no ExeFS, there is no code to survey')
    exefs = f'{f}:{pkg.selector}/exefs'
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix='nup-probe-') as td:
        tmp = FsPath(td)
        romarg = tmp / 'romfs_manifest.tsv'
        if not args.no_romfs and pkg.romfs != nup.NONE:
            romfs_root = f'{f}:{pkg.selector}/romfs'
            say('- walking the RomFS (TOC only, no file contents)...')
            t1 = time.time()
            files, total, tops, tops2 = walk_stats(romfs_root)
            top = str(romfs_root)
            with open(romarg, 'w', encoding='utf-8') as out:
                for d, dirs, names in romfs.walk(top):
                    rel_d = d[len(top):].lstrip('/')
                    for name in names:
                        rel = f'{rel_d}/{name}' if rel_d else name
                        out.write(f'/{rel}\t{romfs.stat(top + "/" + rel).st_size}\t\n')
            say(f'- {files} files, {total / 2**30:.2f} GB in {time.time() - t1:.1f}s')
        else:
            romfs_root, files, total, tops, tops2 = None, 0, 0, {}, {}
            romarg = tmp / 'empty.tsv'; romarg.write_text('')
            if pkg.romfs == nup.NONE: say('[RED] the package has no RomFS (a licence-only add-on?)')
            else: say('- RomFS skipped (--no-romfs)')
        say('- reading the code modules (each is decompressed once in memory)...')
        t1 = time.time()
        F, note = facts(exefs, romarg)
        if note: say(note)
        say(f'- facts in {time.time() - t1:.1f}s')
        report(img, f, pkg, F, romfs_root, files, total, tops, tops2, args.out)


def report(img, f, pkg, F, romfs_root, files, total, tops, tops2, out):
    R = [f'# NUP probe: {f.name} ({pkg.title_id:016X})', '',
         f'- package surveyed: `{pkg.selector}` (v{pkg.version})',
         f'- Python {sys.version.split()[0]}; {zstd_note()}']
    if F['program'] is not None: R.append(f'- main.npdm program ID: `{F["program"]:016X}`')
    if F['sysres']: R.append(f'- system resource: {F["sysres"] / 2**20:.0f} MB (a non-zero value means virtual address memory)')
    R.append(f'- SDK: {", ".join(sorted(F["sdkver"])) or "[RED] none found"}')
    R.append('- SDK components: ' + (', '.join(sorted(F['comps'])) or '—'))
    if F['unity']: R.append('- Unity: ' + ', '.join(sorted(F['unity'])))
    R.append('- engine and API markers: ' + ('; '.join(f'{k} ({", ".join(v)})' for k, v in F['markers'].items()) or '—'))

    R += ['', '## Code modules', '', '| module | what | build ID (game.tsv form) | text / ro / data (MB) | bss (MB) |', '|---|---|---|---|---|']
    for name, m in F['mods'].items():
        R.append(f'| {name} | {m["kind"]} | `{m["bid"]}` | ' + ' / '.join(f'{z / 2**20:.1f}' for z in m['sizes']) + f' | {m["bss"] / 2**20:.1f} |')

    if romfs_root:
        R += ['', f'## RomFS: {files} files, {total / 2**30:.2f} GB (header magics not read: a .nup would decompress whole files for them)', '', '| top level | files | GB |', '|---|---|---|']
        R += [f'| {t} | {n} | {b / 2**30:.2f} |' for t, (n, b) in sorted(tops.items(), key=lambda kv: -kv[1][1])[:20]]
        R += ['', '## RomFS, second level (the 15 largest)', '', '| prefix | files | GB |', '|---|---|---|']
        R += [f'| {t} | {n} | {b / 2**30:.2f} |' for t, (n, b) in sorted(tops2.items(), key=lambda kv: -kv[1][1])[:15]]

    R += ['', '## Draft dm/games/%016X/game.tsv' % pkg.title_id, '', '```']
    R += draft(pkg, F)
    R += ['```', '', 'Next steps: docs/agents/README.md (the checklist for a new title); send this report back with the draft checked by hand.', '']
    text = '\n'.join(R)
    say(text)
    if out: out.write_text(text, encoding='utf-8'); say(f'report written to {out}')


def draft(pkg, F):
    order = sorted((n for n in F['mods'] if n != 'main.npdm'), key=pg.load_order)   # load_order: main, subsdk*, sdk, rtld last (the survey sorts the same way)
    mods = ' '.join(order)
    L = ['# Draft game profile written by scripts/nup_probe.py: the measured identity, builds and modules.',
         '# The bring-up fills the rest (docs/agents/README.md "Checklist for a new title"): memory, shader groups, window, romfs_marker.',
         '# Format: see dm/games/README.md. Rows commented out below are placeholders, not measurements — do not uncomment them unmeasured.', '',
         '# ---- Identity ----',
         f'title_id\t{pkg.title_id:016X}',
         f'program_id\t{(F["program"] or pkg.title_id):016X}', '',
         '# ---- App ----',
         '# name\tTODO: the game\'s name (a .nup carries no control.nacp)',
         '# ipa\tTODO.ipa', '',
         '# ---- Versions ----']
    ver = pkg.version
    bids = ' '.join(f'{n}={F["mods"][n]["bid"]}' for n in order if n != 'rtld' and n != 'main.npdm' and F['mods'][n]['bid'])
    L.append(f'build\t{ver}\t{bids}')
    L.append(f'package\t{ver}')
    L.append(f'shader_versions\t{ver}')
    if F['sysres']: L.append(f'# sys_resource\t0x{F["sysres"]:X}   # measured from main.npdm; the memory map below is the bring-up\'s')
    L += ['', '# ---- Files ----',
          '# load order as on Horizon: main, subsdk*, sdk (the survey\'s "what" column says what each is)',
          f'modules\t{mods}',
          '# romfs_marker\tTODO: a RomFS path that names this game\'s data (from the RomFS listing in the report)',
          '# zip_store\tTODO: extensions to store uncompressed, if any', '',
          '# ---- Memory (TODO: measured in bring-up; commented out until then) ----',
          '# mem_reserve\t0x0', '# mem_alias\t0x0', '# mem_stack\t0x0', '# app_pool\t0x0', '',
          '# ---- Shader split (TODO: shader_groups from the engine the markers and the RomFS show) ----']
    return L


if __name__ == '__main__':
    main()
