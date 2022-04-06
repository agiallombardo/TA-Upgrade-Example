
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import logging
import splunk.rest as rest
from splunktaucclib.rest_handler.error import RestError
import json

from splunk_ta_f5_server_validation import (
    ServerValidation,
    PasswordValidation,
)
from import_declare_test import ta_name

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'description',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=255, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'f5_bigip_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=4096, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'f5_bigip_partitions',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'account_name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=255, 
            min_len=1, 
        )
    ), 
    field.RestField(
        "confirm_account_password",
        required=True,
        encrypted=True,
        default=None,
        validator=PasswordValidation(),
    ),
    field.RestField(
        "account_password",
        required=True,
        encrypted=True,
        default=None,
        validator=ServerValidation(),
    ), 
    field.RestField(
        'interval',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'example_help_link',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'f5_servers',
    model,
    config_name='server'
)

class ServerInputHandler(AdminExternalHandler):
    """
    This class hanldes the parameters in the configuration page.
    """

    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleRemove(self, conf_info):
        """
        This method is called when server is deleted. It deletes the server if it is not used in the task configuration.
        :param conf_info: The dictionary containing configurable parameters.
        """

        session_key = self.getSessionKey()
        stanza_name = self.callerArgs.id
        try:
            response_status, response_content = rest.simpleRequest("/servicesNS/nobody/"+ str(ta_name) + "/configs/conf-inputs/", sessionKey=session_key, getargs={"output_mode": "json"}, raiseAllErrors=True)
            res = json.loads(response_content)
            if "entry" in res:
                for inputs in res['entry']:
                    if "name" in inputs:
                        task_name = (inputs['name']).replace("f5_task://", "")
                        if "content" in inputs and "servers" in inputs['content']:
                            server_name = inputs['content']['servers']
                            server_list = [server.strip() for server in server_name.split("|")]
                            if stanza_name in server_list:
                                raise RestError(409, "Cannot delete the server as it is already been used in {}.".format(task_name))
        except Exception as e:
            raise RestError(409, "Cannot delete the server as it is already been used in {}.".format(task_name))
        super(ServerInputHandler, self).handleRemove(conf_info)

if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=ServerInputHandler,
    )
