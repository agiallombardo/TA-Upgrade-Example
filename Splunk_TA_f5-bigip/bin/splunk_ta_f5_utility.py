import os
import base64
import sys
from solnlib import conf_manager
from splunktaucclib.rest_handler import util
from splunktaucclib.rest_handler.error import RestError
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

import import_declare_test
from log_manager import setup_logging
from import_declare_test import settings_conf_file, ta_name

logger = setup_logging("splunk_ta_f5_utility")

params = {
  'CONTENT_PARAM': 'content',
  'F5_BIGIP_TEMPLATES_CONF_FILE_NAME': 'f5_templates'
}

def is_input_exists(callerargs_id, session_key, field):
  """
  This fuction will check for the fields(servers, templates) having inputs configured with it or not.
  :param callerargs_id: parameter containing the name of the raw from the callerArgs.
  :param session_key: parameter containing the session key.
  :param field: parameter containing the field name.
  :return tuple:
  """
  app_name = util.get_base_app_name()
  cfm = conf_manager.ConfManager(session_key, app_name)
  try:
    task_objs_dict = cfm.get_conf("inputs").get_all()
    task_items = list(task_objs_dict.items())
    if task_items:
      for task, task_info in task_items:
        fields = task_info.get(field)
        # If an input uses two or more templates, then it is stored as pipe separated value in 'templates' field.
        if '|' in str(fields):
          list_of_fields = str(fields).split('|')
          if callerargs_id in list_of_fields:
            return True, callerargs_id
        if fields == callerargs_id:
          return True, fields
  except Exception:
    # Handle the case when no inputs configuration found. In this case, no need to
    # check delete raw exists in task configuration.
    pass
  return False, callerargs_id

def encode(value):
  """
  Encode a string using the URL- and filesystem-safe Base64 alphabet.
  :param value: string to converted into base64
  :return: base64 encoded string
  """
  if value is None:
    return ''
  return base64.urlsafe_b64encode(value.encode('utf-8').strip())

def decode(value):
  """
  Decode a string using the URL- and filesystem-safe Base64 alphabet.
  :param value: string to be decoded
  :return: decoded string
  """
  if value is None:
    return ''
  if sys.version_info > (3,):
    return base64.urlsafe_b64decode(str(value)).decode()
  else:
    return base64.urlsafe_b64decode(str(value))
  
def perform_validation(stanza_name, payload, conf_name, endpoint, existing, session_key):
  """
  Perform the validation on configuration object.
  :param stanza_name: stanza name
  :param payload: payload
  :param conf_name: conf file name
  :param endpoint: endpoint object
  :param existing: boolean flag to identify create/update operation
  :param session_key: session key
  """
  if not existing:
    _check_name_for_create(stanza_name)

  # Check the configuration object is exist or not. set the None value if configuration object not found.
  try:
    cfm = conf_manager.ConfManager(session_key, util.get_base_app_name())
    entity = cfm.get_conf(conf_name).get(stanza_name)
  except Exception:
    entity = None

  if existing and not entity:
    raise RestError(404, '"%s" does not exist' % stanza_name)
  elif not existing and entity:
    raise RestError(409, 'Name "%s" is already in use' % stanza_name)
    
  endpoint.validate(
    stanza_name,
    payload,
    entity
  )

def _check_name_for_create(name):
  """
  Check the stanza name should not be default or not start with `_`
  :param name: stanza name
  """
  if name == 'default':
    raise RestError(
      400,
      '"%s" is not allowed for entity name' % name
    )
  if name.startswith("_"):
    raise RestError(
      400,
      'Name starting with "_" is not allowed for entity'
    )

def create_splunk_ta_f5_settings_conf_file(cfm, stanza):
    """
    This function is used to create the splunk_ta_f5_settings.conf file
    :param cfm: Object of the ConfManager to perform operations on the conf files.
    :param stanza: Name of the stanza to be updated in the splunk_ta_f5_settings.conf file
    """

    dict_inputs_transfer = {}
    try:
      cfm.create_conf(settings_conf_file)
      cfm_transfer_conf = cfm.get_conf(settings_conf_file)
      dict_inputs_transfer['has_migrated'] = 0
      cfm_transfer_conf.update(stanza, dict_inputs_transfer)
    except Exception as e:
      logger.error("Error while creating the transfer_settings.conf file. "+ str(e))

def check_has_migrated_value(cfm, stanza):
    """
    This function is used to check the value of the has_migrated parameter in the splunk_ta_f5_settings.conf file.
    :param cfm: Object of the ConfManager to perform operations on the conf files.
    :param stanza: Name of the stanza to be created in the conf file.
    :return has_migrated param value from the splunk_ta_f5_settings.conf file.
    """

    has_migrated = "0"
    try:
      cfm_transfer = cfm.get_conf(settings_conf_file)
      inputs_dict_obj = cfm_transfer.get_all()
      inputs_items = list(inputs_dict_obj.items())
      if inputs_items:
        for inputs, input_info in inputs_items:
          if inputs == stanza and "has_migrated" in input_info:
            has_migrated = input_info['has_migrated']
      return has_migrated
    except Exception as e:
      logger.error("Error inside transfer_settings.conf read: "+ str(e))
      return has_migrated

def get_session_key():
    """
    This function is used to get the session key.
    :return: This function returns the session_key value.
    """

    try:
      session_key = sys.stdin.readline().strip()
    except Exception as e:
      logger.error("inside session key exception: "+ str(e))

    return session_key

def file_exist(file_name, ta_name):
    """
    This function is used to check if the file exists or not.
    :param file_name: Name of the file which is to be checked if it exists or not.
    :param ta_name: Name of the app.
    :return boolean value after checking if the file exists or not.
    """

    file_path = make_splunkhome_path(["etc", "apps", ta_name, "local", file_name])
    file_name = "".join([file_path, ".conf"])
    if os.path.exists(file_name):
      return True
    else:
      return False

def update_settings_conf(session_key, stanza_name):
  """
  This function is used to update the migration stanza in splunk_ta_f5_settings.conf file.
  :param session_key: The session key value.
  :param stanza_name: The name of the stanza for which the value needs to be updated.
  """

  update_dict = {}
  try:
    cfm_settings = conf_manager.ConfManager(session_key, ta_name)
    cfm_settings_conf = cfm_settings.get_conf(settings_conf_file)
    update_dict['has_migrated'] = 1
    cfm_settings_conf.update(stanza_name, update_dict)
  except Exception as e:
    logger.error("Exception occured while updating splunk_ta_f5_settings.conf stanza {}".format(e))
