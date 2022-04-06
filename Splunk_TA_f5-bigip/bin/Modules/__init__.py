#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-1-2020
#
#
from __future__ import absolute_import
from .models import SOLNAppObjModel
import logging
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
logging.basicConfig( filename=make_splunkhome_path(["var", "log", "splunk"]) + "/Splunk_TA_f5_bigip_main.log", format="%(asctime)s %(levelname)s %(lineno)d %(message)s", filemode="a+", )
logger = logging.getLogger()
logger.setLevel(logging.INFO)
def to_dict(models,connector=None):
    ret={}
    for model in models:
        if isinstance(model,SOLNAppObjModel):
            key=(model.namespace,model.name)
            if connector:
                key=connector.join(key)
            ret[key]=model
    return ret