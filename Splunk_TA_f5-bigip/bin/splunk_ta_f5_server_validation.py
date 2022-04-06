import logging

from splunktaucclib.rest_handler.endpoint.validator import Validator

from splunk.appserver.mrsparkle.lib.util import (  # noqa: F401 # isort: skip
    make_splunkhome_path,
)  # noqa: F401 # isort: skip

logger = logging.getLogger("splunk_f5_server_validation")
logger.setLevel(logging.ERROR)


class PasswordValidation(Validator):
    """
    Check if the password and confirm_password values are same or not.
    """

    def __init__(self, *args, **kwargs):
        super(PasswordValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        """
        This method validates if the values provided in the password and confirm_password fields are same or not.
        The method returns True on success else it returns False.
        :param value: value of the field for which validation is called.
        :param data: Contains dictionary of all the entities of the server configuration.
        :return: bool
        """
        if data["account_password"] != data["confirm_account_password"]:
            msg = "Password is different"
            self.put_msg(msg)
            return False
        else:
            return True
