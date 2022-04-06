#
# SPDX-FileCopyrightText: 2020 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-1-2020
#
#
"""
This module will be used to validate the if the input configuration is valid or not
"""
import import_declare_test
import splunk.admin as admin
from solnlib import log
from solnlib import conf_manager
from ta_util2 import utils
from citrix_netscaler_config import CitrixNetscalerConfig
from splunk.clilib import cli_common as cli

log.Logs.set_context()
logger = log.Logs().get_logger("ta_citrix_netscaler_data_duplication")
"""
REST Endpoint to validate the if the input configuration is valid or not
"""


class Splunk_TA_citrix_netscaler_rh_validate_input_configuration(admin.MConfigHandler):

    """
    This method checks which action is getting called and what parameters are required for the request.
    """
    def setup(self):
        if self.requestedAction == admin.ACTION_LIST:
            # Add required args in supported args
            for arg in ("appliances", "templates", "input_name", "index", "duration", "url"):
                self.supportedArgs.addReqArg(arg)
        return

    """
    This handler is to validate the if the input configuration is valid or not
    It takes  ("appliances", "templates", "input_name", "index", "duration", "url") as caller args and
    Returns the confInfo dict object in response.
    """
    def handleList(self, confInfo):
        logger.info("Entering handler to check input configuration")

        # Get args parameters from the request
        templates = self.callerArgs.data["templates"][0]
        appliances = self.callerArgs.data["appliances"][0]
        input_name = "citrix_netscaler://" + self.callerArgs.data["input_name"][0]
        index = self.callerArgs.data["index"][0]
        duration = self.callerArgs.data["duration"][0]
        service_url = self.callerArgs.data["url"][0]

        # Input objects
        inputs = {}

        # The input obj which is being configured from UI
        ui_input_obj = {
            "servers": appliances,
            "templates": templates,
            "name": input_name,
            "index": index,
            "duration": duration
        }

        inputs[input_name] = ui_input_obj

        app_name = utils.get_appname_from_path(__file__)
        inputs_file_path = utils.make_splunk_path(["etc", "apps", app_name, "local", "inputs.conf"])

        # As conf manager is unable to distinguish the inherited properties i.e ("disabled" property)
        # Reading inputs stanzas from inputs.conf using splunk's internal method
        cfg= cli.readConfFile(inputs_file_path)
        cfg.pop('default', None)

        input_objs = {}

        for input in cfg:
            input_configs = cfg[input]
            input_objs[input] = input_configs

        # Reading inputs from inputs.conf using conf manager
        cfm = conf_manager.ConfManager(self.getSessionKey(), app_name)

        input_objs_dict = cfm.get_conf("inputs").get_all(only_current_app=True)

        # If input is being configured in UI, already found in inputs.conf then delete it. i.e(while updating input)
        if input_name in input_objs and input_name in input_objs_dict:
            del input_objs[input_name]
            del input_objs_dict[input_name]

        # meta configs
        metas = {
            "session_key": self.getSessionKey(),
            "app_name": app_name,
            "server_uri": service_url
        }

        # Here,Mapped the "disabled" property of read inputs from config parser and conf manager
        for input,input_config in input_objs.items():

            if "disabled" not in input_config:
                input_objs_dict[input]["disabled"] = "1"
            else:
                input_objs_dict[input]["disabled"] = input_config["disabled"]

        # Only enabled inputs are going to be considered
        for input, input_config in input_objs_dict.items():
            if input != "citrix_netscaler" and not utils.is_true(input_config["disabled"]):
                    inputs[input] = input_config

        ucs_config = CitrixNetscalerConfig(metas)
        is_warning = ucs_config.get_tasks(inputs, ui_input_validator_args=(input_name, appliances, templates),
                                          ui_input_validator_logger=logger)

        if is_warning:
            confInfo["input_name"]["isValid"] = False
        else:
            confInfo["input_name"]["isValid"] = True

        logger.info("Exiting handler to check input configuration")


if __name__ == "__main__":
    admin.init(Splunk_TA_citrix_netscaler_rh_validate_input_configuration, admin.CONTEXT_APP_AND_USER)