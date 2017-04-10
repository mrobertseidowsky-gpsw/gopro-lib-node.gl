/*
 * Copyright 2016-2017 GoPro Inc.
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

#include <math.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include "log.h"
#include "nodegl.h"
#include "nodes.h"
#include "math_utils.h"
#include "transforms.h"

#define OFFSET(x) offsetof(struct camera, x)
static const struct node_param camera_params[] = {
    {"child", PARAM_TYPE_NODE, OFFSET(child), .flags=PARAM_FLAG_CONSTRUCTOR},
    {"eye", PARAM_TYPE_VEC3,  OFFSET(eye), {.vec={0.0f, 0.0f, 1.0f}}},
    {"center", PARAM_TYPE_VEC3,  OFFSET(center)},
    {"up", PARAM_TYPE_VEC3,  OFFSET(up), {.vec={0.0f, 1.0f, 0.0f}}},
    {"perspective", PARAM_TYPE_VEC4,  OFFSET(perspective)},
    {"eye_transform", PARAM_TYPE_NODE, OFFSET(eye_transform), .flags=PARAM_FLAG_DOT_DISPLAY_FIELDNAME, .node_types=TRANSFORM_TYPES_LIST},
    {"center_transform", PARAM_TYPE_NODE, OFFSET(center_transform), .flags=PARAM_FLAG_DOT_DISPLAY_FIELDNAME, .node_types=TRANSFORM_TYPES_LIST},
    {"up_transform", PARAM_TYPE_NODE, OFFSET(up_transform), .flags=PARAM_FLAG_DOT_DISPLAY_FIELDNAME, .node_types=TRANSFORM_TYPES_LIST},
    {"fov_animkf", PARAM_TYPE_NODELIST, OFFSET(fov_animkf), .flags=PARAM_FLAG_DOT_DISPLAY_PACKED, .node_types=(const int[]){NGL_NODE_ANIMKEYFRAMESCALAR, -1}},
    {"pipe_fd", PARAM_TYPE_INT, OFFSET(pipe_fd)},
    {"pipe_width", PARAM_TYPE_INT, OFFSET(pipe_width)},
    {"pipe_height", PARAM_TYPE_INT, OFFSET(pipe_height)},
    {NULL}
};

static int camera_init(struct ngl_node *node)
{
    struct camera *s = node->priv_data;

    int ret = ngli_node_init(s->child);
    if (ret < 0)
        return ret;

    if (s->eye_transform) {
        ret = ngli_node_init(s->eye_transform);
        if (ret < 0)
            return ret;
    }

    if (s->center_transform) {
        ret = ngli_node_init(s->center_transform);
        if (ret < 0)
            return ret;
    }

    if (s->up_transform) {
        ret = ngli_node_init(s->up_transform);
        if (ret < 0)
            return ret;
    }

    if (s->pipe_fd) {
        s->pipe_buf = calloc(4 /* RGBA */, s->pipe_width * s->pipe_height);
        if (!s->pipe_buf)
            return -1;

#if defined(TARGET_DARWIN) || defined(TARGET_LINUX)
        struct ngl_ctx *ctx = node->ctx;
        struct glcontext *glcontext = ctx->glcontext;
        const struct glfunctions *gl = &glcontext->funcs;

        gl->GenTextures(1, &s->texture_id);
        gl->BindTexture(GL_TEXTURE_2D, s->texture_id);
        gl->TexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
        gl->TexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
        gl->TexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        gl->TexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        gl->TexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, s->pipe_width, s->pipe_height, 0, GL_RGBA, GL_UNSIGNED_BYTE, NULL);
        gl->BindTexture(GL_TEXTURE_2D, 0);

        GLuint framebuffer_id;
        gl->GetIntegerv(GL_FRAMEBUFFER_BINDING, (GLint *)&framebuffer_id);

        gl->GenFramebuffers(1, &s->framebuffer_id);
        gl->BindFramebuffer(GL_FRAMEBUFFER, s->framebuffer_id);
        gl->FramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, s->texture_id, 0);
        ngli_assert(gl->CheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE);

        gl->BindFramebuffer(GL_FRAMEBUFFER, framebuffer_id);
#endif
    }

    return 0;
}

static void camera_update(struct ngl_node *node, double t)
{
    struct camera *s = node->priv_data;
    struct ngl_node *child = s->child;

    float eye[4]    = { 0.0f, 0.0f, 0.0f, 1.0f };
    float center[4] = { 0.0f, 0.0f, 0.0f, 1.0f };
    float up[4]     = { 0.0f, 0.0f, 0.0f, 1.0f };

    float perspective[4*4];
    float view[4*4];

    const float *matrix;

#define APPLY_TRANSFORM(what) do {                                          \
    memcpy(what, s->what, sizeof(s->what));                                 \
    if (s->what##_transform) {                                              \
        ngli_node_update(s->what##_transform, t);                           \
        matrix = ngli_get_last_transformation_matrix(s->what##_transform);  \
        if (matrix)                                                         \
            ngli_mat4_mul_vec4(what, matrix, what);                         \
    }                                                                       \
} while (0)

    APPLY_TRANSFORM(eye);
    APPLY_TRANSFORM(center);
    APPLY_TRANSFORM(up);

    ngli_mat4_look_at(
        view,
        eye,
        center,
        up
    );

    if (s->pipe_fd)
        view[5] = -view[5];

    if (s->nb_fov_animkf)
        ngli_animkf_interpolate(&s->perspective[0], s->fov_animkf, s->nb_fov_animkf, &s->current_fov_kf, t);

    ngli_mat4_perspective(
        perspective,
        s->perspective[0],
        s->perspective[1],
        s->perspective[2],
        s->perspective[3]
    );

    memcpy(child->modelview_matrix, view, sizeof(view));
    memcpy(child->projection_matrix, perspective, sizeof(perspective));

    ngli_node_update(child, t);
}

static void camera_draw(struct ngl_node *node)
{
    struct ngl_ctx *ctx = node->ctx;
    struct glcontext *glcontext = ctx->glcontext;
    const struct glfunctions *gl = &glcontext->funcs;

    struct camera *s = node->priv_data;
    ngli_node_draw(s->child);

    if (s->pipe_fd) {
#if defined(TARGET_DARWIN) || defined(TARGET_LINUX)
        GLint multisampling = 0;
        GLuint framebuffer_read_id;
        GLuint framebuffer_draw_id;

        gl->GetIntegerv(GL_MULTISAMPLE, &multisampling);

        if (multisampling) {
            gl->GetIntegerv(GL_READ_FRAMEBUFFER_BINDING, (GLint *)&framebuffer_read_id);
            gl->GetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING, (GLint *)&framebuffer_draw_id);

            gl->BindFramebuffer(GL_READ_FRAMEBUFFER, framebuffer_draw_id);
            gl->BindFramebuffer(GL_DRAW_FRAMEBUFFER, s->framebuffer_id);
            gl->BlitFramebuffer(0, 0, s->pipe_width, s->pipe_height, 0, 0, s->pipe_width, s->pipe_height, GL_COLOR_BUFFER_BIT, GL_NEAREST);

            gl->BindFramebuffer(GL_READ_FRAMEBUFFER, s->framebuffer_id);
        }
#endif

        LOG(DEBUG, "write %dx%d buffer to FD=%d", s->pipe_width, s->pipe_height, s->pipe_fd);
        gl->ReadPixels(0, 0, s->pipe_width, s->pipe_height, GL_RGBA, GL_UNSIGNED_BYTE, s->pipe_buf);
        write(s->pipe_fd, s->pipe_buf, s->pipe_width * s->pipe_height * 4);

#if defined(TARGET_DARWIN) || defined(TARGET_LINUX)
        if (multisampling) {
            gl->BindFramebuffer(GL_READ_FRAMEBUFFER, framebuffer_read_id);
            gl->BindFramebuffer(GL_DRAW_FRAMEBUFFER, framebuffer_draw_id);
        }
#endif
    }

}

static void camera_uninit(struct ngl_node *node)
{
    struct camera *s = node->priv_data;
    if (s->pipe_fd)
        free(s->pipe_buf);

#if defined(TARGET_DARWIN) || defined(TARGET_LINUX)
    struct ngl_ctx *ctx = node->ctx;
    struct glcontext *glcontext = ctx->glcontext;
    const struct glfunctions *gl = &glcontext->funcs;

    gl->BindFramebuffer(GL_FRAMEBUFFER, s->framebuffer_id);
    gl->FramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, 0, 0);

    gl->DeleteRenderbuffers(1, &s->framebuffer_id);
    gl->DeleteTextures(1, &s->texture_id);
#endif
}

const struct node_class ngli_camera_class = {
    .id        = NGL_NODE_CAMERA,
    .name      = "Camera",
    .init      = camera_init,
    .update    = camera_update,
    .draw      = camera_draw,
    .uninit    = camera_uninit,
    .priv_size = sizeof(struct camera),
    .params    = camera_params,
};
