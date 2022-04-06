#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-1-2020
#
#
from __future__ import absolute_import
import sys
from builtins import object
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from . import bigsuds

from . import log_manager
from log_manager import setup_logging
logger = setup_logging("Splunk_TA_f5_bigip_main")

basestring = str if sys.version_info[0] == 3 else basestring


def loadGlobalApiList():
    apisFile = make_splunkhome_path(["etc", "apps", "Splunk_TA_f5-bigip", "README", "global_api_list.spec"])
    try:
        with open(apisFile, 'r') as f:
            apis = set(line.strip() for line in f if (line.strip() and not line.strip().startswith('#')))
        return apis
    except Exception as exc:
        logger.error("Fail to load Global API List - Exception: %s" % (exc))
        return set()

GLOBAL_API_LIST = loadGlobalApiList()
logger.debug("Global API List is: %s" % (list(GLOBAL_API_LIST)))

class F5_iControl_API(object):
    
    @staticmethod
    def getMethodName(api):
        arrApi=api.split('.')
        return arrApi[2]
    
    @staticmethod
    def getModuleInterface(api):
        arrApi=api.split('.')
        return '%s.%s' % (arrApi[0], arrApi[1])
    
    @staticmethod
    def getPartitions(api, bigip, partitions="", isGlobal=False):
        partitions = ['/'+partition.strip('/ ') for partition in (partitions.split(',') if isinstance(partitions, basestring) else [])]
        if isGlobal or api in GLOBAL_API_LIST:
            return [partitions[0]] if (partitions and '/Common' not in partitions) else ['/Common']
        try:
            return (partitions if partitions else ['/'+partition['partition_name'] for partition in bigip.Management.Partition.get_partition_list()])
        except:
            return ['/Common']
    
    @staticmethod
    def run(bigip, api, params=None):
        arrApi=api.split('.')
        
        # Module
        logger.debug("Get module for API: %s" % (api))
        module=getattr(bigip, arrApi[0])

        # Interface
        logger.debug("Get interface for API: %s" % (api))
        retry=False # Retry it if there is a connection error
        try:
            interface=getattr(module, arrApi[1])
        except bigsuds.ConnectionError:
            retry=True
        except bigsuds.ServerError as e:
            logger.error(F5_iControl_API.getLogTxt(bigip, api, e))
            return None
        except (bigsuds.ParseError, bigsuds.OperationFailed) as e:
            logger.error(F5_iControl_API.getLogTxt(bigip, api, e))
            return []
        
        if retry:
            logger.debug("Retry interface for API: %s" % (api))
            try:
                interface=getattr(module, arrApi[1])
            except (bigsuds.ConnectionError, bigsuds.ServerError) as e:
                logger.error(F5_iControl_API.getLogTxt(bigip, api, e))
                return None
            except (bigsuds.ParseError, bigsuds.OperationFailed) as e:
                logger.error(F5_iControl_API.getLogTxt(bigip, api, e))
                return []
        
        # Method
        logger.debug("Get method for API: %s" % (api))
        try:
            method=getattr(interface, arrApi[2])
        except bigsuds.MethodNotFound as e:
            logger.error(F5_iControl_API.getLogTxt(bigip, api, e))
            return []
        
        # Call api
        logger.debug("Call API: %s" % (api))
        try:
            return method(params) if params else method()
        except (bigsuds.ConnectionError, bigsuds.ServerError) as e:
            logger.error(F5_iControl_API.getLogTxt(bigip, api, e))
            return None
        except (bigsuds.ParseError, bigsuds.OperationFailed) as e:
            logger.error(F5_iControl_API.getLogTxt(bigip, api, e))
            return []
    
    @staticmethod
    def getLogTxt(bigip, api, e):
        return 'Exception (it may be caused by unreachable F5 server "{}" or wrong iControl API "{}" in configured template): {}'.format(bigip._hostname, api, e)
    
    @staticmethod
    def parse(strAPIs):
        strAPIs=''.join(strAPIs.split())
        apis = []
        module, interface = [""]*2
        for strAPI in strAPIs.split(';'):
            arrAPI=strAPI.split('.')
            method = arrAPI[0] if len(arrAPI)==1 else ""
            module, interface, method = arrAPI if len(arrAPI)==3 else (module, interface, method)
            
            if module and interface and method:
                apis.append("{}.{}.{}".format(module, interface, method))
            else:
                logger.error('Fail to parse API "{}" in "{}"'.format(strAPI, strAPIs))
        return apis
    
    
