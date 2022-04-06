#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-1-2020
#
#
from __future__ import absolute_import

from builtins import object
from threading import Condition

from .bigsuds import BIGIP

from . import log_manager
from log_manager import setup_logging
logger = setup_logging("Splunk_TA_f5_bigip_main")


class F5_BigIP_Host(object):
    
    def __init__(self, maxCount):
        self._maxCount = maxCount
        self._conns = []
        self._count = 0
    
    def count(self):
        return self._count
    
    def minus(self):
        self ._count = 0 if self._count<=0 else self._count-1
    
    def new(self, hostname, username, password):
        self._count = self._count+1
        return BIGIP(hostname=hostname, username=username, password=password)
    
    def get(self, hostname, username, password):
        return self._conns.pop() if self._conns else self.new(hostname, username, password)
    
    def put(self, conn):
        self._conns.append(conn)
        
    def has(self):
        return self._conns or self._count<self._maxCount


class F5_BigIP_Pool(object):
    
    cond = Condition()
    pool = {}
    maxCount = 1
    
    @classmethod
    def getConn(cls, hostname, username, password):
        logger.debug("Get an f5 connection: {username}@{hostname}".format(hostname=hostname, username=username))
        cls.cond.acquire()
        if hostname not in cls.pool:
            cls.pool[hostname] = F5_BigIP_Host(cls.maxCount)
        logger.debug('F5 connection count for "{username}@{hostname}" is {count}'.format(hostname=hostname, username=username, count=cls.pool[hostname].count()))
        while True:
            if cls.pool[hostname].has():
                conn = cls.pool[hostname].get(hostname=hostname, username=username, password=password)
                break
            logger.debug("Wait for an f5 connection: {username}@{hostname}".format(hostname=hostname, username=username))
            cls.cond.wait()
            logger.debug("Wake for an f5 connection: {username}@{hostname}".format(hostname=hostname, username=username))
        logger.debug('F5 connection count for "{username}@{hostname}" is {count}'.format(hostname=hostname, username=username, count=cls.pool[hostname].count()))
        cls.cond.release()
        return conn
    
    @classmethod
    def putConn(cls, hostname, username, bigip):
        logger.debug("Put an f5 connection: {username}@{hostname}".format(hostname=hostname, username=username))
        logger.debug('F5 connection count for "{username}@{hostname}" is {count}'.format(hostname=hostname, username=username, count=cls.pool[hostname].count()))
        cls.cond.acquire()
        cls.pool[hostname].put(bigip)
        cls.cond.notify(2)
        cls.cond.release()
    
    @classmethod
    def delConn(cls, hostname, username):
        logger.debug("Drop an f5 connection: {username}@{hostname}".format(hostname=hostname, username=username))
        logger.debug('F5 connection count for "{username}@{hostname}" is {count}'.format(hostname=hostname, username=username, count=cls.pool[hostname].count()))
        cls.cond.acquire()
        cls.pool[hostname].minus()
        cls.cond.notify(2)
        cls.cond.release()
