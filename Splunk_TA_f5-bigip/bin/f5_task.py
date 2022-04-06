import import_declare_test
import sys
import json
from splunklib import modularinput as smi
from log_manager import setup_logging
from solnlib import conf_manager
from import_declare_test import ta_name

logger = setup_logging("Splunk_TA_f5_bigip_main")

import gc
import os
import time
import signal
import traceback
import threading

PARENT = os.path.sep+os.path.pardir
FOLDER = os.path.abspath(__file__+PARENT+os.path.sep+'Splunk_TA_f5_bigip')
sys.path.append(FOLDER)


from Modules.F5Templates import F5TemplatesManager
from Modules.F5Servers import F5ServersManager
from Modules.F5Tasks import F5TasksManager,F5TaskModel
from Modules import to_dict
from Modules.f5_bigip_scheduler import F5BigIPScheduler

from Modules.ta_util.log_settings import get_level
from splunklib import modularinput as smi

DEBUGGING_NAME='___debugging___'
MAIN_LOOP_DELAY=40
EXIT_DELAY=30

def env_debugging():
    return DEBUGGING_NAME in os.environ

def task_debugging(task_manager):
    debugging_task=task_manager.get_by_name(DEBUGGING_NAME)
    return not (debugging_task is None or debugging_task.disabled)

def check_interval_value(interval, input_name):
    """
    This function is used to check if the interval value is not empty and is an integer value.
    :param interval: The value of the 'interval' field obtained from the inputs.
    :param input_name: The name of the input.
    :return: The function returns boolean value after checkin if the interval value is not empty and is an integer value.
    """
    try:
        int(interval)
    except ValueError:
        logger.error("Got unexpected value {} of 'interval' field for input '{}'. Duration should be an integer. You can either change it in inputs.conf file or edit 'Polling interval' on Inputs page.".format(interval, input_name))
        return False

    return True


class F5_TASK(smi.Script):

    def __init__(self):
        super(F5_TASK, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('f5_task')
        scheme.description = 'Input'
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                'name',
                title='Name',
                description='Name',
                required_on_create=True
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'description',
                required_on_create=False,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'servers',
                required_on_create=True,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'templates',
                required_on_create=True,
            )
        )
        
        return scheme

    def _exit_handler(self, signum, frame=None):
        logger.info("cancellation received.")
        self.exit.set()

    def validate_input(self, definition):
        return

    def stream_events(self, inputs, ew):
        self.exit=threading.Event()
        signal.signal(signal.SIGTERM, self._exit_handler)
        signal.signal(signal.SIGINT, self._exit_handler)

        logger.debug("stream_events started.")

        token = self.service.token

        event_writer=ew
        server_manager = F5ServersManager(token)
        template_manager = F5TemplatesManager(token)
        task_manager = F5TasksManager(token)

        if task_debugging(task_manager)!=env_debugging():
            exit(0)

        schedulers = {}

        logger.debug("Tasks loaded.")
        while True:
            try:
                server_manager.reload()
                template_manager.reload()
                task_manager.reload()

                meta_configs = self._input_definition.metadata
                session_key = meta_configs['session_key']
                input_items = [{'count': len(inputs.inputs)}]

                for input_name, input_item in inputs.inputs.items():
                    input_item['name'] = input_name.replace("f5_task://", "")
                    # Check if server is linked with the enabled input
                    if not input_item.get("servers"):
                        logger.error("No F5-BigIP servers are linked to the data input. '{}'. To resume data collection, either configure new server on the Configurations page or link an existing server to the input on Inputs page.".format(input_item["name"]))
                        sys.exit(1)

                    # Check if server is linked with the enabled input
                    if not input_item.get("templates"):
                        logger.error("No F5-BigIP templates are linked to the data input. '{}'. To resume data collection, either configure new template on the Configurations page or link an existing template to the input on Inputs page.".format(input_item["name"]))
                        sys.exit(1)

                    # Convert interval value to integer
                    if not input_item.get("interval"):
                        input_item["interval"] = 300
                        logger.warn("No interval specified for input '{}'. Using default interval=300 for now.".format(input_item["name"]))
                    elif not check_interval_value(input_item['interval'], input_item['name']):
                        input_item['interval'] = 300

                    input_items.append(input_item)
                logger.info("stream_events started.")

                logger.debug("Main loop start.")
                servers = to_dict(server_manager.all(), ':')
                templates = to_dict(template_manager.all(), ':')
                tasks = [task for task in task_manager.all()]
                new_schedulers = {}
            except Exception as e:
                time.sleep(MAIN_LOOP_DELAY)
                if self.exit.isSet():
                    break
                logger.error("Error in getting task definitions by restful API(maybe splunk daemon is down?) - Traceback:\n"+traceback.format_exc())
                continue

            for task in tasks:
                if self.exit.isSet():
                    break

                if isinstance(task, F5TaskModel):
                    if task.name==DEBUGGING_NAME:
                        continue
                    logger.debug("Task :{}".format(task.name))
                    t_hash = task.get_hash()
                    if task.disabled:
                        if t_hash in schedulers:
                            schedulers[t_hash].stop.set()
                            del schedulers[t_hash]
                    else:
                        if t_hash in schedulers:
                            scheduler = schedulers[t_hash]
                            scheduler.update(servers, templates, task)
                            new_schedulers[t_hash] = scheduler
                            del schedulers[t_hash]
                        else:
                            new_schedulers[t_hash] = F5BigIPScheduler(servers, templates, task, event_writer)
                            new_schedulers[t_hash].start()
            for scheduler in list(schedulers.values()):
                scheduler.stop.set()

            schedulers = new_schedulers

            if self.exit.isSet():
                break
            gc.collect()
            time.sleep(MAIN_LOOP_DELAY)

        # exit

        for scheduler in list(schedulers.values()):
            scheduler.stop.set()
        time.sleep(EXIT_DELAY)


if __name__ == '__main__':
    exit_code = F5_TASK().run(sys.argv)
    sys.exit(exit_code)