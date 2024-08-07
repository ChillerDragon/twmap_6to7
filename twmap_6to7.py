#!/usr/bin/env python3

import os.path
import sys
import json
import argparse
from typing import Optional

import numpy
import twmap # type: ignore

EXAMPLE_TEXT = '''example:

  6to7.py ~/.teeworlds/maps/dm1.map dm1_07.map'''
all_args = argparse.ArgumentParser(
                                 epilog=EXAMPLE_TEXT,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
all_args.add_argument('-v', '--verbose',  help='verbose output', action = 'store_true')
all_args.add_argument('-s', '--strict',  help='fail instead of best effort translation on edge case doodads', action = 'store_true')
all_args.add_argument('-Werror', '--Werror',  help='abort with error on warning', action = 'store_true')
all_args.add_argument('-Wempty', '--Wempty',  help='warn if empty tiles are used', action = 'store_true')
all_args.add_argument('-Wunknown', '--Wunknown',  help='warn if tile index is not in the mapping', action = 'store_true', default = True)
all_args.add_argument('-Wmapping', '--Wmapping',  help='show warnings for problematic tiles from the mappings file', action = 'store_true', default = True)
all_args.add_argument('-Wno-mapping', '--Wno-mapping',  help='turn off -Wmapping', action = 'store_true')
all_args.add_argument('-Weverything', '--Weverything',  help='turn every warning on', action = 'store_true')
all_args.add_argument('-Wall', '--Wall',  help='turn all sensible warnings on', action = 'store_true')
all_args.add_argument('-d', '--direction', help='translation direction either 7to6 or 6to7 (default)', default = '6to7')
all_args.add_argument('INPUT_MAP')
all_args.add_argument('OUTPUT_MAP')

args = vars(all_args.parse_args())

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

def dbg(msg: str) -> None:
    if not args['verbose']:
        return
    print(msg)

def warn(warn_type: str, msg: str) -> None:
    if not is_warn(warn_type):
        return
    print(f"Warning: {msg} [-{warn_type}]")
    if args['Werror']:
        print('Error on waring because -Werror is on')
        sys.exit(1)

def is_warn(warn_type: str) -> bool:
    if args['Weverything']:
        return True
    if args['Wall']:
        if warn_type != 'Wempty':
            return True
    off = f"Wno_{warn_type[1:]}"
    if off in args:
        if args[off]:
            return False
    return args[warn_type]

def replace_doodads(layer, mapping: dict) -> None:
    progress = 0
    edited_tiles = layer.tiles
    for (y, x, flags), tile in numpy.ndenumerate(layer.tiles):
        progress += 1
        if progress % 100 == 0:
            print(x, y)
        if tile == 0:
            continue
        if flags != 0:
            continue

        if str(tile) in mapping:
            warn_key = f"{tile}_warning"
            if warn_key in mapping:
                warn('Wmapping', mapping[warn_key])
            error_key = f"{tile}_error"
            if error_key in mapping:
                print(f"Error: {mapping[error_key]}")
                sys.exit(1)
            mapped = mapping[str(tile)]
            if mapped == 0:
                warn('Wempty', f"Empty tile used at x={x} y={y}")
            edited_tiles[y][x][flags] = mapped
        else:
            warn('Wunknown', f"Tile with index {tile} at x={x} y={y} is not in the mapping")
    layer.tiles = edited_tiles

def get_mapping(image_name, direction) -> Optional[dict]:
    mapping_path = os.path.join(SCRIPT_DIR, "mappings", f"{direction}_{image_name}.json")
    if os.path.isfile(mapping_path):
        with open(mapping_path, encoding='utf-8') as f:
            return json.load(f)
    return None

def main() -> None:
    if args['Werror']:
        print('All warnings will be errors')
    if not args['direction'] in ('6to7', '7to6'):
        print(f"invalid direction '{args['direction']}' valid options are 6to7 and 7to6")
        sys.exit(1)
    dbg(f"translating map {args['INPUT_MAP']}")
    m = twmap.Map(args['INPUT_MAP'])
    for group in m.groups:
        for layer in group.layers:
            if layer.kind() != 'Tiles':
                continue
            if layer.image is None:
                dbg("skipping layer without image")
                continue
            if m.images[layer.image].is_embedded():
                dbg("skipping embedded layer")
                continue
            img_name = m.images[layer.image].name
            dbg(img_name)
            mapping = get_mapping(img_name, args['direction'])
            if mapping:
                print(f"translating {img_name} layer '{layer.name}'")
                replace_doodads(layer, mapping['mappings'])

    m.save(args['OUTPUT_MAP'])

main()
