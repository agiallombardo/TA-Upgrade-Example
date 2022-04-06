#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-1-2020
#
#
from __future__ import absolute_import
from builtins import object
from datetime import datetime, timedelta
from .mixin import KeyCompMixin
import heapq
import time
import sys


class IntervalTask(KeyCompMixin):
    def __init__(self, interval, queries=[],next_exec_time=None):
        self.queries = queries
        self.interval = interval  # seconds
        self.next_exec_time = next_exec_time
        if not self.next_exec_time:
            self.next_exec_time = datetime.now()

    def add(self, query):
        self.queries.append(query)

    def set_queries(self,queries):
        self.queries=queries

    def refresh(self):
        self.next_exec_time = datetime.now() + timedelta(seconds=self.interval)
        
    def assert_type(self, other):
        return isinstance(other, IntervalTask)

    def compare_key(self):
        return self.next_exec_time


class ServerTask(KeyCompMixin):
    def __init__(self, server_data, metadata, global_interval, task_list):
        self.server_data = server_data
        self.metadata = metadata
        self.tasks = task_list
        heapq.heapify(self.tasks)
        self.to_be_deleted = False
        self.multi_interval = len(task_list) > 1 or self.top().interval != global_interval

    def __str__(self):
        return str(self.server_data.get_hash())+' '+str((self.next_exec_time()-datetime.fromtimestamp(0)).total_seconds())

    def pop(self):
        return heapq.heappop(self.tasks)

    def push(self, item):
        return heapq.heappush(self.tasks, item)

    def pushpop(self, item):
        return heapq.heappushpop(self.tasks, item)

    def replace(self, item):
        return heapq.heapreplace(self.tasks, item)

    def top(self):
        if len(self.tasks) == 0:
            return None
        return self.tasks[0]

    def next_task(self):
        task = self.pop()
        task.refresh()
        self.push(task)
        return task

    def next_exec_time(self):
        return self.top().next_exec_time

    def wait(self):
        seconds=(self.next_exec_time() - datetime.now()).total_seconds()
        time.sleep(seconds if seconds>0 else 0)

    def assert_type(self, other):
        if not isinstance(other, ServerTask):
            raise TypeError("wrong type in comparation")

    def compare_key(self):
        return self.next_exec_time()

    def close(self):
        pass




class PollingPool(object):
    def __init__(self,connector,size=1):
        self.connector=connector
        self.pool=[None for i in range(size)]

    def get_conn(self):
        for i in range(len(self.pool)):
            if self.pool[i] is None:
                self.pool[i]=self.connector.connect()
                return self.pool[i]
            elif self.connector.check(self.pool[i]):
                return self.pool[i]
        return None

class ConnectionPoolTask(ServerTask):
    def __init__(self, server_data, metadata, global_interval, task_list, conn_pool):
        ServerTask.__init__(server_data, metadata, global_interval, task_list)
        self.pool=conn_pool

    def get_conn(self):
        return self.pool.get_conn()
