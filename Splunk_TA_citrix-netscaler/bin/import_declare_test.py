#
# SPDX-FileCopyrightText: 2020 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-1-2020
#
#


import os
import sys

sys.path.insert(0, os.path.sep.join([os.path.dirname(__file__), "framework"]))
sys.path.insert(
    0,
    os.path.sep.join(
        [os.path.dirname(os.path.realpath(os.path.dirname(__file__))), "lib"]
    ),
)
if sys.version_info < (3, 0):
    sys.path.insert(
        0,
        os.path.sep.join(
            [
                os.path.dirname(os.path.realpath(os.path.dirname(__file__))),
                "lib",
                "py2",
            ]
        ),
    )
else:
    sys.path.insert(
        0,
        os.path.sep.join(
            [
                os.path.dirname(os.path.realpath(os.path.dirname(__file__))),
                "lib",
                "py3",
            ]
        ),
    )


# Module import tests
import http
import queue

ta_name = "Splunk_TA_citrix-netscaler"

if sys.version_info < (3, 0):
    assert ta_name in http.__file__
    assert ta_name in queue.__file__
else:
    assert ta_name not in http.__file__
    assert ta_name not in queue.__file__
