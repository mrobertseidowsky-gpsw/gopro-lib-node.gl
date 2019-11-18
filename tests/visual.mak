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

# 1:category, 2:name, 3:dstlist
define DECLARE_TEST
test-visual-$(1)-$(2): SCENE = $(1)_$(2)
$(3) += test-visual-$(1)-$(2)
endef

# 1:category, 2:namelist, 3:dstlist
define DECLARE_TESTS
$(foreach X,$(2),$(eval $(call DECLARE_TEST,$(1),$(X),$(3))))
test-visual-$(1): $$($3)
VISUAL_TESTS += $$($3)
endef

#
# Shapes
#
SHAPE_TEST_NAMES =          \
    triangle                \
    quad                    \
    circle                  \
    geometry                \
    geometry_normals        \

$(eval $(call DECLARE_TESTS,shape,$(SHAPE_TEST_NAMES),SHAPE_TESTS))


#
# Textures
#
TEXTURE_TEST_NAMES =        \
    media                   \
    data                    \
    data_animated           \
    data_unaligned_row      \

test-visual-texture-media: NB_KEYFRAMES = 5

$(eval $(call DECLARE_TESTS,texture,$(TEXTURE_TEST_NAMES),TEXTURE_TESTS))


#
# Text
#
TEXT_TEST_NAMES =           \
    colors                  \
    0_to_127                \
    128_to_255              \
    align_cc                \
    align_cr                \
    align_cl                \
    align_bc                \
    align_br                \
    align_bl                \
    align_tc                \
    align_tr                \
    align_tl                \

$(eval $(call DECLARE_TESTS,text,$(TEXT_TEST_NAMES),TEXT_TESTS))


#
# Transforms
#
TRANSFORM_TEST_NAMES =      \
    matrix                  \
    translate               \
    translate_animated      \
    scale                   \
    scale_animated          \
    scale_anchor            \
    scale_anchor_animated   \
    rotate                  \
    rotate_anchor           \
    rotate_quat             \
    rotate_quat_anchor      \

$(eval $(call DECLARE_TESTS,transform,$(TRANSFORM_TEST_NAMES),TRANSFORM_TESTS))


#
# Visual Tests (aggregate of all the above)
#
SCENES_SCRIPT = visual.py
RENDER_WIDTH = 1280
RENDER_HEIGHT = 800
NB_KEYFRAMES = 1
TOLERANCE = 0
$(VISUAL_TESTS):
	@echo $@
	@$(PYTHON) test_visual.py "$(SCENES_SCRIPT)" "$(SCENE)" "$(RENDER_WIDTH)" "$(RENDER_HEIGHT)" "$(NB_KEYFRAMES)" "$(TOLERANCE)" > /dev/null

test-visual: $(VISUAL_TESTS)

TESTS += $(VISUAL_TESTS)

.PHONY: $(VISUAL_TESTS)
