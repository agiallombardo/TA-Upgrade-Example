#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-1-2020
#
#
from __future__ import absolute_import

from builtins import object
import re
import json
from .F5_iControl_API import F5_iControl_API
from .F5_BigIP_Pool import F5_BigIP_Pool

from . import log_manager
from log_manager import setup_logging

logger = setup_logging("Splunk_TA_f5_bigip_main")

class F5_iControl_Template(object):
    
    def __init__(self, strTemplate, hostname, partitions, username, password):
        self._hostname=hostname or ""
        self._partitions=partitions or []
        self._username=username or ""
        self._password=password or ""
        
        self._usable=True
        self._apiCall=''
        self._apiAgainst=[]
        self._withField=''
        self._breakField=''
        self._interval = 0
        self._isGlobal = False
        self._strTemplate=strTemplate
        
        logger.debug("F5 BIG-IP Template - New: {}".format(json.dumps({'hostname':self._hostname, 'partitions':self._partitions, 'username':self._username, 'template':self._strTemplate})))
        
        templatePattern = """
        \s*
        call\s+(?P<apiCall>\w+\.\w+\.\w+)
        (?:\s+against\s+
            (?P<apiAgainst>\w+\.\w+\.\w+(?:\s*\;\s*(?:\w+\.\w+\.)?\w+)*)
            (?:\s+withField\s+RESULT\.(?P<withField>\w+))?
        )?
        (?:\s+breakField\s+RESULT\.(?P<breakField>\w+){1})?
        (?:\s+interval\s+(?P<interval>\d+))?
        (?:\s+(?P<isGlobal>\-\-GLOBAL))?
        \s*
        """
        templatePattern = ''.join(templatePattern.split())
        m=re.match(templatePattern, self._strTemplate)
        if m is None:
            self._usable=False
            logger.error('F5 BIG-IP Template - ERROR (not in expected form): "{}"'.format(self._strTemplate))
            return
        
        groupDict = m.groupdict()
        self._apiCall = groupDict['apiCall']
        self._apiAgainst = F5_iControl_API.parse(groupDict['apiAgainst']) if groupDict['apiAgainst'] else []
        self._breakField = groupDict['breakField'] or ""
        self._withField = groupDict['withField'] or ""
        self._interval = int(groupDict['interval']) if groupDict['interval'] else 0
        self._isGlobal = True if groupDict['isGlobal'] else False
    
    def usable(self):
        return self._usable
    
    def getInterval(self):
        return self._interval
    
    def fetch(self):
        """Fetch data for this template.
        """
        logger.debug("F5 BIG-IP Template - Fetch: %s" % json.dumps({'hostname':self._hostname, 'partitions':self._partitions, 'username':self._username, 'template':self._strTemplate}))
        # Get bigip instance from BigIP Pool.
        bigip=F5_BigIP_Pool.getConn(hostname=self._hostname, username=self._username, password=self._password)
        
        # Get partitions
        logger.debug("Get Partitions for API: %s" % (self._apiCall))
        partitions = F5_iControl_API.getPartitions(api=self._apiCall, bigip=bigip, partitions=self._partitions, isGlobal=self._isGlobal)
        logger.debug('Partitions for API "%s" is %s' % (self._apiCall, partitions))
        F5_BigIP_Pool.putConn(hostname=self._hostname, username=self._username, bigip=bigip)
        
        # Fetch on every partition
        return [event for partition in partitions for event in self._fetch(partition)]
    
    def _fetch(self, partition):
        """Fetching operator
        """
        if not self.usable():
            return[]

        # Get bigip instance from BigIP Pool.
        bigip=F5_BigIP_Pool.getConn(hostname=self._hostname, username=self._username, password=self._password)
        # Set active folder
        try:
            bigip.System.Session.set_active_folder(partition)
        except:
            logger.error('Fail to set active folder as partition "{}" for Template "{}" on F5 BIGIP "{}"'.format(partition, self._strTemplate, self._hostname))
            F5_BigIP_Pool.putConn(hostname=self._hostname, username=self._username, bigip=bigip)
            return []
        
        # For call block
        logger.debug("Run call-api: %s" % (self._apiCall))
        dataCall=F5_iControl_API.run(bigip=bigip, api=self._apiCall)
        logger.debug("End call-api: %s" % (self._apiCall))
        if dataCall is None:
            return[]
        if dataCall==[]:
            F5_BigIP_Pool.putConn(hostname=self._hostname, username=self._username, bigip=bigip)
            return[]
                
        # For empty callApi result
        dataCall=self.breakField(dataCall)
            
        # Change result to a list
        if not type(dataCall) is list:
            dataCall=[dataCall]
        
        # Adding fields: mlt_type & module_interface & break_field & with_field
        if self._apiAgainst:
            mlt_type='against'
        elif self._breakField:
            mlt_type='break_field'
        else:
            mlt_type=''
        data=[{'mlt_type':mlt_type, 'module_interface':F5_iControl_API.getModuleInterface(self._apiCall), 'break_field':self._breakField, 'with_field':self._withField, F5_iControl_API.getMethodName(self._apiCall):aDataCall, 'f5_bigip_partition_name':partition.strip('/')} for aDataCall in dataCall]

        # For withField block
        dataWith=dataCall
        if len(self._withField)>0:
            for i in range(len(dataCall)):
                if self._withField not in dataCall[i]:
                    F5_BigIP_Pool.putConn(hostname=self._hostname, username=self._username, bigip=bigip)
                    logger.warn('Wrong withField: \"%s\" in \"%s\"' % (self._withField, self._strTemplate))
                    return data
            dataWith=[dataCall[i][self._withField] for i in range(len(dataCall))]
            
        # For against block
        isWrong=False
        for aApiAgainst in self._apiAgainst:
            logger.debug("Run against-api: %s" % (aApiAgainst))
            dataAgainst=F5_iControl_API.run(bigip=bigip, api=aApiAgainst, params=dataWith)
            logger.debug("End against-api: %s" % (aApiAgainst))
            if dataAgainst is None:
                isWrong=True
                F5_BigIP_Pool.delConn(hostname=self._hostname, username=self._username)
                break
            if dataAgainst==[]:
                continue
            for i in range(len(dataWith)):
                data[i][F5_iControl_API.getMethodName(aApiAgainst)]=dataAgainst[i]
        
        if not isWrong: 
            F5_BigIP_Pool.putConn(hostname=self._hostname, username=self._username, bigip=bigip)
        else:
            F5_BigIP_Pool.delConn(hostname=self._hostname, username=self._username)
        return data
    
    def breakField(self, data):
        '''Break 'data' on a specified field named 'filedName'.
        '''
        if len(self._breakField)<=0:
            return data
        else:
            if not (type(data) is dict and self._breakField in data):
                logger.warn('Wrong breakField: \"%s\" in \"%s\"' % (self._breakField, self._strTemplate))
                return []
            return [item for item in data[self._breakField]]
        
        