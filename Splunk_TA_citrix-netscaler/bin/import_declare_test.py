#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-1-2020
#
#


import os
import sys

sys.path.insert(0, os.path.sep.join([os.path.dirname(__file__), "framework"]))
sys.path.insert(0,os.path.sep.join([os.path.dirname(os.path.realpath(os.path.dirname(__file__))), "lib"]))

# Module import tests
import http
import queue

ta_name = "Splunk_TA_citrix-netscaler"
assert ta_name not in http.__file__
assert ta_name not in queue.__file__
