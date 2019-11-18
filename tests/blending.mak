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

test-blending-none: FUNC_NAME = test_blending_none
BLENDING_TESTS += test-blending-none

test-blending-multiply: FUNC_NAME = test_blending_multiply
BLENDING_TESTS += test-blending-multiply

test-blending-screen: FUNC_NAME = test_blending_screen
BLENDING_TESTS += test-blending-screen

test-blending-darken: FUNC_NAME = test_blending_darken
BLENDING_TESTS += test-blending-darken

test-blending-lighten: FUNC_NAME = test_blending_lighten
BLENDING_TESTS += test-blending-lighten

RENDER_WIDTH = 1280
RENDER_HEIGHT = 800
TOLERANCE = 1
$(BLENDING_TESTS):
	@echo $@
	@$(PYTHON) -c 'from blending import $(FUNC_NAME); $(FUNC_NAME)()' > /dev/null

test-blending: $(BLENDING_TESTS)

TESTS += $(BLENDING_TESTS)
