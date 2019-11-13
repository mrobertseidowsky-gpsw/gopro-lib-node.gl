#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2019 GoPro Inc.
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#


import sys
import os
import os.path as op

from PIL import Image

import pynodegl as ngl
from pynodegl_utils.com import query_inplace


_HSIZE = 8
_HNBITS = _HSIZE * _HSIZE * 2
_REF_DIR = op.join(op.dirname(__file__), "refs")
_MODE = "RGBA"


def _get_plane_hashes(buf):
    hashes = []
    linesize = _HSIZE + 1
    comp_bufs = (buf[x::4] for x in range(4))  # R, G, B, A
    for comp_buf in comp_bufs:
        comp_hash = 0
        for y in range(_HSIZE):
            for x in range(_HSIZE):
                pos = y * linesize + x
                px_ref = comp_buf[pos]
                px_xp1 = comp_buf[pos + 1]
                px_yp1 = comp_buf[pos + linesize]
                h_bit = px_ref < px_xp1
                v_bit = px_ref < px_yp1
                comp_hash = comp_hash << 2 | h_bit << 1 | v_bit
        hashes.append(comp_hash)
    return hashes


def _hash_scene(scene, width, height, duration, nb_keyframes):
    # TODO: png output?
    capture_buffer = bytearray(width * height * 4)
    viewer = ngl.Viewer()
    assert viewer.configure(offscreen=1, width=width, height=height, capture_buffer=capture_buffer) == 0
    timescale = duration / nb_keyframes
    viewer.set_scene_from_string(scene)
    hashes = []
    for t_id in range(nb_keyframes):
        viewer.draw(t_id * timescale)
        img = Image.frombuffer(_MODE, (width, height), capture_buffer, 'raw', _MODE, 0, 1)
        img = img.resize((_HSIZE + 1, _HSIZE + 1), resample=Image.LANCZOS)
        data = img.tobytes()
        h = _get_plane_hashes(data)
        hashes.append(h)
    return hashes


def _get_output(hashes):
    return '\n'.join(' '.join(format(x, '032X') for x in comp_hashes) for comp_hashes in hashes) + '\n'


def _hash_repr(hash_val):
    linesize = _HSIZE + 1
    diff_chars = '.v>+'  # identical, vertical diff, horizontal diff, vertical+horizontal diff
    ret = ''
    for y in range(_HSIZE):
        line = ''
        for x in range(_HSIZE):
            pos = y * linesize + x
            bits = hash_val >> (pos * 2) & 0b11
            line += ' {}'.format(diff_chars[bits])
        ret += line + '\n'
    return ret


def _parse_hash_line(line):
    return [int(x, 16) for x in line.split()]


def _load_hashes(filename):
    with open(filename) as f:
        return [_parse_hash_line(line) for line in f.readlines()]


def _compare_hashes(test_name, ref_hashes, out_hashes, tolerance):
    err = []
    nb_fail = 0

    assert len(ref_hashes) == len(out_hashes)

    for frame, (frame_ref_hashes, frame_out_hashes) in enumerate(zip(ref_hashes, out_hashes)):
        for comp, (ref_hash, out_hash) in enumerate(zip(frame_ref_hashes, frame_out_hashes)):
            hash_diff = ref_hash ^ out_hash
            bstring = '{:b}'.format(hash_diff)
            diff = bstring.count('1') * 100 // _HNBITS
            if diff > tolerance:
                err.append('{} frame #{} Component {}: Diff too high ({}% > {}%)\n{:s}'.format(
                    test_name, frame, _MODE[comp], diff, tolerance, _hash_repr(hash_diff)))
                nb_fail += 1

    return nb_fail, err


def _run_test(script_path, entry_point, width, height, nb_keyframes, tolerance):
    gen_ref = os.environ.get("GEN") == "1"

    script_file = op.basename(script_path)
    basename, _ = op.splitext(script_file)
    cfg = {
        'pkg': script_path,
        'scene': (basename, entry_point),
    }
    ret = query_inplace(query='scene', **cfg)
    assert 'error' not in ret

    out_hashes = _hash_scene(ret['scene'], width, height, ret['duration'], nb_keyframes)

    test_name = '{}_{}'.format(basename, entry_point)
    ref_filepath = op.join(_REF_DIR, '{}.ref'.format(test_name))

    if gen_ref:
        with open(ref_filepath, "w") as ref_file:
            ref_file.write(_get_output(out_hashes))
        ref_hashes = out_hashes
    else:
        ref_hashes = _load_hashes(ref_filepath)

    nb_fail, err = _compare_hashes(test_name, ref_hashes, out_hashes, tolerance)
    if nb_fail:
        sys.stderr.write('\n'.join(err))
        return 1

    return 0


if __name__ == '__main__':
    script_path, entry_point = sys.argv[1:3]
    width = int(sys.argv[3])
    height = int(sys.argv[4])
    nb_keyframes = int(sys.argv[5])
    tolerance = int(sys.argv[6])
    sys.exit(_run_test(script_path, entry_point, width, height, nb_keyframes, tolerance))
