from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from bigsuds import BIGIP, ConnectionError, OperationFailed
import logging
logger = logging.getLogger('splunk_f5_server_validation')
logger.setLevel(logging.ERROR)

class ServerValidation(Validator):
  """
  Authentication of the F5-BigIP server
  """

  def __init__(self, *args, **kwargs):
    super(ServerValidation, self).__init__(*args, **kwargs)

  def validate(self, value, data):
    """
    This method validates if the credentials provided to authenticate with the f5-bigip server are correct or not. The method returns True on success else it returns False.
    :param value: value of the field for which validation is called.
    :param data: Contains dictionary of all the entities of the server configuration.
    :return: bool
    """
    try:
      api = BIGIP(hostname=data['f5_bigip_url'], username=data['account_name'], password=data['account_password'])
      result = api.System.SystemInfo.get_uptime()
      return True
    except ConnectionError as e:
      msg = "Failed to connect to F5 BIG-IP instance. Verify that the server is reachable and "\
      "correct credentials are provided."
      self.put_msg(msg)
      logger.error("Connection error: {}".format(e))
      return False
    except OperationFailed as e:
      msg = "F5 BIG-IP Operation failed. Reason: " + str(e)
      self.put_msg(msg)
      logger.error("OperationFailed error: {}".format(e))
      return False
    except Exception as e:
      msg = "Authentication Failed. Reason: " + str(e)
      self.put_msg(msg)
      logger.error("Exception error: {}".format(e))
      return False


class PasswordValidation(Validator):
  """
  Check if the password and confirm_password values are same or not.
  """

  def __init__(self, *args, **kwargs):
    super(PasswordValidation, self).__init__(*args, **kwargs)

  def validate(self, value, data):
    """
    This method validates if the values provided in the password and confirm_password fields are same or not. The method returns True on success else it returns False.
    :param value: value of the field for which validation is called.
    :param data: Contains dictionary of all the entities of the server configuration.
    :return: bool
    """
    if data['account_password'] != data['confirm_account_password']:
      msg = "Password is different"
      self.put_msg(msg)
      return False
    else:
      return True
