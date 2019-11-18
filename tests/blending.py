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
import array
import math
import random
import pynodegl as ngl
from pynodegl_utils.misc import scene


# https://en.wikipedia.org/wiki/Color_term
_COLORS_DEF = {
    'white':   (1.0, 1.0, 1.0, 1.0),
    'black':   (0.0, 0.0, 0.0, 1.0),
    'red':     (1.0, 0.0, 0.0, 1.0),
    'orange':  (1.0, 0.5, 0.0, 1.0),
    'yellow':  (1.0, 1.0, 0.0, 1.0),
    'cgreen':  (0.5, 1.0, 0.0, 1.0),  # Chartreuse green
    'green':   (0.0, 1.0, 0.0, 1.0),
    'sgreen':  (0.0, 1.0, 0.5, 1.0),  # Spring green
    'cyan':    (0.0, 1.0, 1.0, 1.0),
    'azure':   (0.0, 0.5, 1.0, 1.0),
    'blue':    (0.0, 0.0, 1.0, 1.0),
    'violet':  (0.5, 0.0, 1.0, 1.0),
    'magenta': (1.0, 0.0, 1.0, 1.0),
    'rose':    (1.0, 0.0, 0.5, 1.0),
}

_REF_DIR = op.join(op.dirname(__file__), "refs")
_CIRCLE_RADIUS = 0.5

_DEBUG_POSITIONS = False

def _equilateral_triangle_coords(sz=0.5, balanced=True):
    b = sz * math.sqrt(3) / 2.
    c = sz / 2.
    yoff = (c - sz) / 2. if balanced else 0.
    return (-b, yoff - c, 0.), (b, yoff - c, 0.), (0., yoff + sz, 0.)


def _mid_pos(*points):
    return [sum(x) / len(x) for x in zip(*points)]


def _color_positions(sz=0.5, balanced=True):
    pA, pB, pC = _equilateral_triangle_coords(sz, balanced)
    pD, pE, pF = [_mid_pos(p0, p1) for (p0, p1) in ((pA, pC), (pA, pB), (pB, pC))]
    pO = _mid_pos(pA, pB, pC)
    yoff = -sz / 4. if balanced else 0.
    return dict(A=pA, B=pB, C=pC, D=pD, E=pE, F=pF, O=pO, Z=(-1., yoff + 1., 0.))


def _pos_to_px(pos, width, height):
    x = int(round((pos[0] + 1.) / 2. * width))
    y = height - 1 - int(round((pos[1] + 1.) / 2. * height))
    x = min(max(x, 0), width - 1)
    y = min(max(y, 0), height - 1)
    return [x, y]


def _get_out_ref(scene, width, height):
    capture_buffer = bytearray(width * height * 4)
    viewer = ngl.Viewer()
    assert viewer.configure(offscreen=1, width=width, height=height, capture_buffer=capture_buffer, clear_color=_COLORS_DEF["azure"]) == 0
    viewer.set_scene(scene["scene"])
    viewer.draw(0)
    points_positions = _color_positions(_CIRCLE_RADIUS)
    colors = []
    for point_name in "ABCDEFOZ":
        x, y, _ = points_positions[point_name]
        pix_x, pix_y = _pos_to_px((x, y), width, height)
        pos = (pix_y * width + pix_x) * 4
        color = capture_buffer[pos:pos + 4]
        colors.append( '{}: {:02X} {:02X} {:02X} {:02X}'.format(point_name, *color))
    return '\n'.join(colors) + '\n'

def _get_output(data):
    return data


def _load_hashes(filename):
    with open(filename) as f:
        return f.read()

def _compare_hashes(test_name, ref_hashes, out_hashes, tolerance):
    if ref_hashes != out_hashes:
        # XXX difflib
        return 1, ["{} Diff".format(test_name)]
    return 0, []

def _run_test(name, width, height, tolerance):

    scene = eval("blending_" + name)(debug_positions=False)

    basename = 'blending'
    entry_point = name

    out_hashes = _get_out_ref(scene, width, height)

    # XXX share with test_visual.py
    gen_ref = os.environ.get("GEN") == "1"

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


def _blending_scene(cfg, name=None, bgcolor=None, debug_positions=False, **blending_kwargs):
    cfg.aspect_ratio = (1, 1)

    prog = ngl.Program(fragment=cfg.get_frag('color'))
    positions = _equilateral_triangle_coords(_CIRCLE_RADIUS * 2.0 / 3.0)
    dbg_positions = _color_positions(_CIRCLE_RADIUS)
    circle = ngl.Circle(radius=_CIRCLE_RADIUS, npoints=100)
    g = ngl.Group()

    # Optional text
    if name:
        text_height = 0.25
        text = ngl.Text(name,
                        fg_color=_COLORS_DEF["white"], bg_color=_COLORS_DEF["black"],
                        valign='top',
                        box_height=(0, text_height, 0),
                        box_corner=(-1, 1.0 - text_height, 0))
        g.add_children(text)
        # offset circle positions
        positions = [(p[0], p[1] - text_height / 2.0, p[2]) for p in positions]
        dbg_positions = dict((name, (p[0], p[1] - text_height / 2.0, p[2])) for name, p in dbg_positions.items())

    # Blending background
    if bgcolor is not None:
        blend_bg = ngl.Group(label='blend background')
        for position in positions:
            render = ngl.Render(circle, prog)
            render.update_uniforms(color=ngl.UniformVec4(value=bgcolor))
            render = ngl.Translate(render, position)
            blend_bg.add_children(render)
        g.add_children(blend_bg)

    # Blended colored circles
    colors = [
        (186/255., 159/255.,   8/255., 1.0),
        (165/255.,   3/255.,  81/255., 1.0),
        (  6/255., 163/255., 194/255., 1.0),
    ]
    circles_group = ngl.Group()
    for position, color in zip(positions, colors):
        render = ngl.Render(circle, prog)
        render.update_uniforms(color=ngl.UniformVec4(value=color))
        render = ngl.Translate(render, position)
        circles_group.add_children(render)
    circles = ngl.GraphicConfig(circles_group, label='blended circles', blend=True, **blending_kwargs)
    g.add_children(circles)

    # Display named green circles on the points where the colors are picked for the
    # tests. Enabling this option should cause all the blending tests to return
    # green pixels.
    if debug_positions:
        dbg_circle_group = ngl.Group()
        dbg_circle_radius = 0.025
        dbg_circle = ngl.Circle(radius=dbg_circle_radius)
        dbg_circle_render = ngl.Render(dbg_circle, prog)
        dbg_circle_render.update_uniforms(color=ngl.UniformVec4(value=_COLORS_DEF["green"]))
        text_sz = 0.1, 0.1
        for pos_name, position in dbg_positions.items():
            text = ngl.Text(pos_name, box_width=(text_sz[0], 0, 0), box_height=(0, text_sz[1], 0),
                            bg_color=(0, 0, 0, 0))
            text = ngl.Translate(text, (1 + dbg_circle_radius, 1 - dbg_circle_radius - text_sz[1], 0))
            point = ngl.Group(children=(dbg_circle_render, text))
            point = ngl.Translate(point, position)
            dbg_circle_group.add_children(point)
        dbg_circles = ngl.GraphicConfig(dbg_circle_group, blend=True,
                                        blend_src_factor='src_alpha',
                                        blend_dst_factor='one_minus_src_alpha',
                                        blend_src_factor_a='zero',
                                        blend_dst_factor_a='one',
                                        label='Debug circles')
        g.add_children(dbg_circles)

    return g


def _grid(*scenes):
    nb = len(scenes)
    nb_rows = int(math.sqrt(nb))
    nb_cols = int(math.ceil(nb / float(nb_rows)))
    dim = max(nb_rows, nb_cols)
    elem_size = 2. / dim
    scale = elem_size / 2.
    offset = elem_size * (dim - 1) / 2.

    g = ngl.Group()
    for row in range(nb_rows):
        for col in range(nb_cols):
            pos_x = -offset + col * elem_size
            pos_y = offset - row * elem_size
            scene_id = row * nb_cols + col
            if scene_id >= len(scenes):
                return g
            scene = scenes[scene_id]
            scene = ngl.Scale(scene, [scale, scale, 1])
            scene = ngl.Translate(scene, (pos_x, pos_y, 0))
            g.add_children(scene)
    return g


@scene(debug_positions=scene.Bool())
def all_blendings(cfg, debug_positions=False):
    cfg.aspect_ratio = (1, 1)
    scenes = []
    for bname, bcolor, bparams in _blending_cfgs:
        scenes.append(_blending_scene(cfg, bname, bcolor, debug_positions=debug_positions, **bparams))
    return _grid(*scenes)


_blending_cfgs = (
    ("none", None, dict()),
    ("multiply", _COLORS_DEF["white"], dict(
        blend_src_factor='dst_color',
        blend_dst_factor='zero',
    )),
    ("screen", _COLORS_DEF["black"], dict(
        blend_src_factor="one",
        blend_dst_factor="one_minus_src_color",
    )),
    ("darken", _COLORS_DEF["white"], dict(
        blend_op='min',
    )),
    ("lighten", _COLORS_DEF["black"], dict(
        blend_op='max',
    )),
)


def _get_blending_function(bcolor, **bparams):
    @scene(debug_positions=scene.Bool())
    def scene_func(cfg, debug_positions=True):
        return _blending_scene(cfg, bgcolor=bcolor, debug_positions=debug_positions, **bparams)
    return scene_func

def _get_test_blending_function(bname):
    def test_func():
        sys.exit(_run_test(bname, 128, 128, 0))
    return test_func

for bname, bcolor, bparams in _blending_cfgs:
    globals()["blending_" + bname] = _get_blending_function(bcolor, **bparams)
    globals()["test_blending_" + bname] = _get_test_blending_function(bname)
