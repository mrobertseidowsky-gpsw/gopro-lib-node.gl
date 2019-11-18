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


def _equilateral_triangle_coords(sz=1.0):
    b = sz * math.sqrt(3) / 3.0
    c = sz * .5
    return (-b, -c, 0), (b, -c, 0), (0, sz * .5, 0)


def _render_shape(cfg, geometry, color):
    prog = ngl.Program(fragment=cfg.get_frag('color'))
    render = ngl.Render(geometry, prog)
    render.update_uniforms(color=ngl.UniformVec4(value=color))
    return render


@scene(sz=scene.Range(range=[0.1, 2], unit_base=100),
       color=scene.Color())
def shape_triangle(cfg, sz=1, color=_COLORS_DEF['orange']):
    cfg.aspect_ratio = (1, 1)
    p0, p1, p2 = _equilateral_triangle_coords(sz)
    geometry = ngl.Triangle(p0, p1, p2)
    return _render_shape(cfg, geometry, color)


@scene(corner=scene.Vector(n=3, minv=(-1, -1, -1), maxv=(1, 1, 1)),
       width=scene.Vector(n=3, minv=(0, 0, 0), maxv=(2, 2, 2)),
       height=scene.Vector(n=3, minv=(0, 0, 0), maxv=(2, 2, 2)),
       color=scene.Color())
def shape_quad(cfg, corner=(-.5, -.8, 0), width=(0.9, 0.2, 0), height=(0.1, 1.3, 0), color=_COLORS_DEF['sgreen']):
    cfg.aspect_ratio = (1, 1)
    geometry = ngl.Quad(corner, width, height)
    return _render_shape(cfg, geometry, color)


@scene(radius=scene.Range(range=[0.1, 2], unit_base=100),
       color=scene.Color())
def shape_circle(cfg, radius=0.5, color=_COLORS_DEF['azure']):
    cfg.aspect_ratio = (1, 1)
    geometry = ngl.Circle(radius, npoints=64)
    return _render_shape(cfg, geometry, color)


def _shape_geometry(cfg, set_normals=False):
    # Fake cube (3 faces only) obtained from:
    # echo 'cube();'>x.scad; openscad x.scad -o x.stl
    vertices = array.array('f', [x - 0.5 for x in [
        1,1,0, 0,1,1, 1,1,1,
        0,1,1, 1,1,0, 0,1,0,
        0,0,0, 0,1,1, 0,1,0,
        0,1,1, 0,0,0, 0,0,1,
        0,1,1, 1,0,1, 1,1,1,
        1,0,1, 0,1,1, 0,0,1,
    ]])

    normals = array.array('f', [
        0,1,0,  0,1,0,  0,1,0,
        0,1,0,  0,1,0,  0,1,0,
       -1,0,0, -1,0,0, -1,0,0,
       -1,0,0, -1,0,0, -1,0,0,
        0,0,1,  0,0,1,  0,0,1,
        0,0,1,  0,0,1,  0,0,1,
    ])

    vertices_buffer = ngl.BufferVec3(data=vertices)
    normals_buffer = ngl.BufferVec3(data=normals)

    cfg.aspect_ratio = (1, 1)
    geometry = ngl.Geometry(vertices=vertices_buffer)

    if set_normals:
        geometry.set_normals(normals_buffer)
        prog = ngl.Program(fragment=cfg.get_frag('colored-normals'))
        render = ngl.Render(geometry, prog)
    else:
        render = _render_shape(cfg, geometry, _COLORS_DEF['magenta'])

    return ngl.Rotate(render, 45, axis=(1, 1, 1))


@scene()
def shape_geometry(cfg):
    return _shape_geometry(cfg, set_normals=False)


@scene()
def shape_geometry_normals(cfg):
    return _shape_geometry(cfg, set_normals=True)


@scene()
def texture_media(cfg):
    # FIXME: using make -jN will cause a race in the creation of the media
    media = cfg.medias[0]
    cfg.aspect_ratio = (media.width, media.height)
    cfg.duration = media.duration
    quad = ngl.Quad((-1, -1, 0), (2, 0, 0), (0, 2, 0))
    texture = ngl.Texture2D(data_src=ngl.Media(media.filename))
    render = ngl.Render(quad)
    render.update_textures(tex0=texture)
    return render


def _render_buffer(w, h):
    n = w * h
    data = array.array('B', [i * 255 // n for i in range(n)])
    buf = ngl.BufferUByte(data=data)
    texture = ngl.Texture2D(width=w, height=h, data_src=buf)
    render = ngl.Render(ngl.Quad())
    render.update_textures(tex0=texture)
    return render


@scene(w=scene.Range(range=[1, 128]),
       h=scene.Range(range=[1, 128]))
def texture_data(cfg, w=4, h=5):
    cfg.aspect_ratio = (1, 1)
    return _render_buffer(w, h)


@scene(dim=scene.Range(range=[1, 100]))
def texture_data_animated(cfg, dim=8):
    cfg.duration = 3.0
    random.seed(0)
    get_rand = lambda: array.array('f', [random.random() for i in range(dim ** 2 * 3)])
    nb_kf = int(cfg.duration)
    buffers = [get_rand() for i in range(nb_kf)]
    random_animkf = []
    time_scale = cfg.duration / float(nb_kf)
    for i, buf in enumerate(buffers + [buffers[0]]):
        random_animkf.append(ngl.AnimKeyFrameBuffer(i*time_scale, buf))
    random_buffer = ngl.AnimatedBufferVec3(keyframes=random_animkf)
    random_tex = ngl.Texture2D(data_src=random_buffer, width=dim, height=dim)
    quad = ngl.Quad((-1, -1, 0), (2, 0, 0), (0, 2, 0))
    prog = ngl.Program()
    render = ngl.Render(quad, prog)
    render.update_textures(tex0=random_tex)
    return render


@scene(h=scene.Range(range=[1, 32]))
def texture_data_unaligned_row(cfg, h=32):
    '''Tests upload of buffers with rows that are not 4-byte aligned'''
    cfg.aspect_ratio = (1, 1)
    return _render_buffer(1, h)


@scene()
def text_0_to_127(cfg):
    s = ''
    for y in range(8):
        for x in range(16):
            c = y << 4 | x
            s += chr(c) if c else ' '
        s += '\n'
    return ngl.Text(s)


@scene()
def text_128_to_255(cfg):
    '''Note: this is currently incorrectly displaying characters it shouldn't
    display but this test is mainly meant to check for crashes'''
    s = ''
    for y in range(8):
        for x in range(16):
            c = 1<<7 | y << 4 | x
            s += chr(c) if c else ' '
        s += '\n'
    return ngl.Text(s)


def _text(**params):
    return ngl.Text('This\nis\nnode.gl', font_scale=0.7, padding=8, **params)


@scene()
def text_colors(cfg):
    return _text(fg_color=_COLORS_DEF['rose'], bg_color=_COLORS_DEF['cgreen'])


@scene()
def text_align_cc(cfg):
    return _text(valign="center", halign="center")


@scene()
def text_align_cr(cfg):
    return _text(valign="center", halign="right")


@scene()
def text_align_cl(cfg):
    return _text(valign="center", halign="left")


@scene()
def text_align_bc(cfg):
    return _text(valign="bottom", halign="center")


@scene()
def text_align_br(cfg):
    return _text(valign="bottom", halign="right")


@scene()
def text_align_bl(cfg):
    return _text(valign="bottom", halign="left")


@scene()
def text_align_tc(cfg):
    return _text(valign="top", halign="center")


@scene()
def text_align_tr(cfg):
    return _text(valign="top", halign="right")


@scene()
def text_align_tl(cfg):
    return _text(valign="top", halign="left")


def _transform_shape(cfg):
    w, h = 0.75, 0.45
    geometry = ngl.Quad(corner=(-w/2., -h/2., 0), width=(w, 0, 0), height=(0, h, 0))
    return _render_shape(cfg, geometry, _COLORS_DEF["rose"])


@scene()
def transform_matrix(cfg):
    cfg.aspect_ratio = (1, 1)
    shape = _transform_shape(cfg)
    # XXX: set arbitrary matrix + transform chain
    return ngl.Transform(shape)


@scene(vector=scene.Vector(n=3, minv=(-1, -1, -1), maxv=(1, 1, 1)))
def transform_translate(cfg, vector=(0.2, 0.7, -0.4)):
    cfg.aspect_ratio = (1, 1)
    shape = _transform_shape(cfg)
    return ngl.Translate(shape, vector)


@scene()
def transform_translate_animated(cfg):
    cfg.aspect_ratio = (1, 1)
    cfg.duration = 3.
    p0, p1, p2 = _equilateral_triangle_coords()
    anim = [
        ngl.AnimKeyFrameVec3(0, p0),
        ngl.AnimKeyFrameVec3(1 * cfg.duration / 3., p1),
        ngl.AnimKeyFrameVec3(2 * cfg.duration / 3., p2),
        ngl.AnimKeyFrameVec3(cfg.duration, p0),
    ]
    shape = _transform_shape(cfg)
    return ngl.Translate(shape, anim=ngl.AnimatedVec3(anim))


@scene(factors=scene.Vector(n=3, minv=(-1, -1, -1), maxv=(1, 1, 1)))
def transform_scale(cfg, factors=(0.7, 1.4, 0)):
    cfg.aspect_ratio = (1, 1)
    shape = _transform_shape(cfg)
    return ngl.Scale(shape, factors)


@scene(factors=scene.Vector(n=3, minv=(-1, -1, -1), maxv=(1, 1, 1)),
       anchor=scene.Vector(n=3, minv=(-1, -1, -1), maxv=(1, 1, 1)))
def transform_scale_anchor(cfg, factors=(0.7, 1.4, 0), anchor=(-0.4, 0.5, 0.7)):
    cfg.aspect_ratio = (1, 1)
    shape = _transform_shape(cfg)
    return ngl.Scale(shape, factors, anchor=anchor)


@scene(factors=scene.Vector(n=3, minv=(-1, -1, -1), maxv=(1, 1, 1)))
def transform_scale_animated(cfg, factors=(0.7, 1.4, 0)):
    cfg.aspect_ratio = (1, 1)
    cfg.duration = 2.0
    shape = _transform_shape(cfg)
    anim = [
        ngl.AnimKeyFrameVec3(0, (0, 0, 0)),
        ngl.AnimKeyFrameVec3(cfg.duration / 2., factors),
        ngl.AnimKeyFrameVec3(cfg.duration, (0, 0, 0)),
    ]
    return ngl.Scale(shape, anim=ngl.AnimatedVec3(anim))


@scene(factors=scene.Vector(n=3, minv=(-1, -1, -1), maxv=(1, 1, 1)),
       anchor=scene.Vector(n=3, minv=(-1, -1, -1), maxv=(1, 1, 1)))
def transform_scale_anchor_animated(cfg, factors=(0.7, 1.4, 0), anchor=(-0.4, 0.5, 0.7)):
    cfg.aspect_ratio = (1, 1)
    cfg.duration = 2.0
    shape = _transform_shape(cfg)
    anim = [
        ngl.AnimKeyFrameVec3(0, (0, 0, 0)),
        ngl.AnimKeyFrameVec3(cfg.duration / 2., factors),
        ngl.AnimKeyFrameVec3(cfg.duration, (0, 0, 0)),
    ]
    return ngl.Scale(shape, anim=ngl.AnimatedVec3(anim), anchor=anchor)


@scene(angle=scene.Range(range=[0, 360], unit_base=10))
def transform_rotate(cfg, angle=123.4):
    cfg.aspect_ratio = (1, 1)
    shape = _transform_shape(cfg)
    return ngl.Rotate(shape, angle)


@scene(angle=scene.Range(range=[0, 360], unit_base=10),
       anchor=scene.Vector(n=3, minv=(-1, -1, -1), maxv=(1, 1, 1)))
def transform_rotate_anchor(cfg, angle=123.4, anchor=(0.15, 0.35, 0.7)):
    cfg.aspect_ratio = (1, 1)
    shape = _transform_shape(cfg)
    return ngl.Rotate(shape, angle, anchor=anchor)


@scene(quat=scene.Vector(n=4, minv=(-1, -1, -1, -1), maxv=(1, 1, 1, 1)))
def transform_rotate_quat(cfg, quat=(0, 0, -0.474, 0.880)):
    cfg.aspect_ratio = (1, 1)
    shape = _transform_shape(cfg)
    return ngl.RotateQuat(shape, quat)


@scene(quat=scene.Vector(n=4, minv=(-1, -1, -1, -1), maxv=(1, 1, 1, 1)),
       anchor=scene.Vector(n=3, minv=(-1, -1, -1), maxv=(1, 1, 1)))
def transform_rotate_quat_anchor(cfg, quat=(0, 0, -0.474, 0.880), anchor=(0.15, 0.35, 0.7)):
    cfg.aspect_ratio = (1, 1)
    shape = _transform_shape(cfg)
    return ngl.RotateQuat(shape, quat, anchor=anchor)


@scene()
def shared_buffer(cfg):
    # XXX TODO
    n = 4
    data = array.array('B', [i * 255 // n for i in range(n)])
    buf = ngl.BufferUByte(data=data)
    texture = ngl.Texture2D(width=n, height=1, data_src=buf)
    render = ngl.Render(ngl.Quad())
    render.update_textures(tex0=texture)
    return render


#def instancing... (all draw modes)
#
#def animation...
#
#
#@scene()
#def diamond_blending(cfg):
#    pass
#
#
#@scene()
#def diamond_blending_with_timeranges(cfg):
#    # XXX: shuffled order?
#    pass
#
#
#@scene()
#def camera(cfg):
#    pass
#
#
#@scene()
#def shared_buffers(cfg):
#    pass
#
#
#@scene()
#def shared_geometries(cfg):
#    pass
#
#
#@scene()
#def data_uniform(cfg):
#    pass
#
#
#@scene()
#def data_streamed(cfg):
#    pass
#
#
#@scene()
#def data_animated(cfg):
#    pass
#
#
#@scene()
#def timerange(cfg):
#    pass
