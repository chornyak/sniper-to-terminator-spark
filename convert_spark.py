#!/usr/bin/env python3
"""Convert a Holley Sniper .spark file (format v2) so Terminator X software can import it (format v3).

Usage:
    python3 convert_spark.py SNIPER.spark [TEMPLATE.spark] [OUTPUT.spark]
    python3 convert_spark.py --show FILE.spark [FILE.spark ...]

TEMPLATE is any .spark file saved from Terminator X software (e.g. your current table). If omitted,
template.spark next to this script is used. It supplies the Terminator signature bytes and the
v3-only blocks (rev limiter / launch retard entries). Everything else (idle/cruise/WOT targets,
31x31 table, axes, settings) comes from the Sniper file.

--show prints the timing targets, axes and table of a Sniper or Terminator X file without converting.
"""
import struct
import sys
from pathlib import Path

SIG = slice(0x00, 0x04)        # product signature (Sniper vs Terminator), not a checksum
VERSION_OFFSETS = (0x04, 0x50)
LENGTH_OFFSET = 0x54           # bytes from 0x4C to end of file
TARGETS_AT = 0x5C              # idle, cruise, WOT timing targets
TABLE_AT = 0x68                # 31x31 table, one MAP row at a time, low MAP first
MAP_AXIS_AT = 0xF6C
RPM_AXIS_AT = 0xFE8
N = 31
INSERT_AT = 0x1114             # v3 inserts a block here that v2 lacks
INSERT_LEN = 0x108
V2_SIZE, V3_SIZE = 4628, 5028
V3_TRAILER_AT = 0x131C          # v3-only rev limiter / launch retard entries
DEFAULT_TEMPLATE = Path(__file__).resolve().with_name('template.spark')


def version(data):
    return struct.unpack_from('<I', data, 0x50)[0]


def check(data, name, ver, size):
    if len(data) != size or version(data) != ver:
        got = f'v{version(data)} / {len(data)} bytes' if len(data) >= 0x54 else f'{len(data)} bytes'
        sys.exit(f'{name}: expected v{ver} / {size} bytes, got {got}')


def convert(sniper, template):
    check(sniper, 'Sniper file', 2, V2_SIZE)
    check(template, 'Template file', 3, V3_SIZE)

    out = bytearray(sniper[:INSERT_AT]
                    + template[INSERT_AT:INSERT_AT + INSERT_LEN]
                    + sniper[INSERT_AT:]
                    + template[V3_TRAILER_AT:])
    out[SIG] = template[SIG]
    for off in VERSION_OFFSETS:
        struct.pack_into('<I', out, off, 3)
    struct.pack_into('<I', out, LENGTH_OFFSET, len(out) - 0x4C)
    assert len(out) == V3_SIZE
    return bytes(out)


def targets(data):
    idle, cruise, wot = struct.unpack_from('<3f', data, TARGETS_AT)
    return f'Idle {idle:.1f}  Cruise {cruise:.1f}  WOT {wot:.1f}'


def show(path):
    data = path.read_bytes()
    kind = {(2, V2_SIZE): 'Sniper', (3, V3_SIZE): 'Terminator X'}.get(
        (version(data), len(data)) if len(data) >= 0x54 else None)
    if kind is None:
        sys.exit(f'{path}: not a recognised Sniper or Terminator X .spark file')
    table = struct.unpack_from(f'<{N * N}f', data, TABLE_AT)
    kpa = struct.unpack_from(f'<{N}f', data, MAP_AXIS_AT)
    rpm = struct.unpack_from(f'<{N}f', data, RPM_AXIS_AT)

    print(f'{path}  ({kind} format)')
    print(targets(data))
    print(f'RPM {rpm[0]:.0f}-{rpm[-1]:.0f}   MAP {kpa[0]:.0f}-{kpa[-1]:.0f} kPa\n')
    # Same orientation as the software: highest MAP at the top
    for r in reversed(range(N)):
        print(f'{kpa[r]:4.0f} |' + ''.join(f'{v:5.1f}' for v in table[r * N:(r + 1) * N]))
    print('     +' + '-' * 5 * N)
    print(' RPM  ' + ''.join(f'{v:5.0f}' for v in rpm) + '\n')


def main():
    args = sys.argv[1:]
    if args[:1] == ['--show'] and len(args) > 1:
        for p in args[1:]:
            show(Path(p))
        return
    if len(args) not in (1, 2, 3) or args[0].startswith('-'):
        sys.exit(__doc__)

    src = Path(args[0])
    tpl = Path(args[1]) if len(args) > 1 else DEFAULT_TEMPLATE
    dst = Path(args[2]) if len(args) > 2 else src.with_name(src.stem + '_terminator.spark')
    if not tpl.exists():
        sys.exit(f'Template not found: {tpl}\n'
                 'Save a base spark table from Terminator X as template.spark next to this script, '
                 'or pass a template file as the second argument.')
    if dst.resolve() in (src.resolve(), tpl.resolve()):
        sys.exit('Output must be a new file, not one of the inputs')
    dst.write_bytes(convert(src.read_bytes(), tpl.read_bytes()))

    print(f'Wrote {dst}')
    print(targets(dst.read_bytes()))


if __name__ == '__main__':
    main()
