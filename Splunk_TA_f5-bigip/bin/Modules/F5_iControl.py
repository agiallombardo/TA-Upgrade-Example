#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-1-2020
#
#
from __future__ import absolute_import

from builtins import object
from .F5_iControl_Template import F5_iControl_Template

class F5_iControl(object):
    
    def __init__(self, hostname, partitions, username, password):
        self._hostname=hostname
        self._partitions = partitions
        self._username=username
        self._password=password
        return
    
    def getTemplates(self, strTemplates):
        """Get F5 iControl templates from a string.
        """
        # Split the inputting string
        lines=strTemplates.split('\n')
        
        # Parse middle language template
        templates=[]
        for line in lines:
            line=line.strip()
            # End of file
            if line.startswith('$$$'):
                break
            # A blank or comment line
            if not line or line.startswith('#'):
                continue
            
            template=F5_iControl_Template(line, self._hostname, self._partitions, self._username, self._password)
            if template.usable():
                templates.append(template)
               
        # From list to map
        result={}
        for template in templates:
            if template.getInterval() not in result:
                result[template.getInterval()]=[]
            result[template.getInterval()].append(template)
            
        return result
    