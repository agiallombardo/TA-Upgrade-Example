import os

import import_declare_test
from splunklib import binding
from solnlib import conf_manager
from log_manager import setup_logging
from import_declare_test import tasks_conf_file, inputs_conf_file, settings_conf_file, ta_name, inputs_migration_stanza
import splunk_ta_f5_utility as utility
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
try:
  import sys
  sys.path.insert(0, make_splunkhome_path(['etc', 'apps', ta_name, 'appserver', 'controllers']))
  import manage_tasks
except Exception as e:
  pass
from Modules.F5Tasks import F5TasksManager

logger = setup_logging("migrate_existing_tasks")

class MigrateExistingInputs():
  """
  This class is used to migrate the existing tasks to inputs.conf file.
  """

  def check_file_exist(self):
    """
    This function is used to check if the controllers directory exists or not.
    :return: The function returns True if directory exists otherwise returns False.
    """

    file_path = make_splunkhome_path(['etc', 'apps', ta_name, 'appserver', 'controllers', 'manage_tasks.py'])
    if os.path.isfile(file_path):
      return True
    else:
      return False

  def get_tasks(self, session_key):
    """
    This function is used to get the tasks that are configured in the existing addon.
    :param session_key: The session key value.
    :return result: The function returns the list of tasks that are configured in the existing addon.
    """

    tasks_obj = F5TasksManager(session_key).all()
    result = []
    for task in tasks_obj:
      result.append(task.to_dict())
    return result

  def transfer_data_to_inputs(self, session_key, tasks_list):
    """
    This function is used to transfer the stanzas from the splunk_ta_f5_bigip_tasks.conf file to inputs.conf file.
    :param session_key: The session key value.
    :param tasks_list: The list of the tasks that are configured in the existing addon.
    """

    try:
      cfm = conf_manager.ConfManager(session_key, ta_name)
      cfm_input = cfm.get_conf(inputs_conf_file)
      for task in tasks_list:
        new_dict = {}
        stanza_name = "".join(["f5_task://", task['name']])
        if task.get('description'):
          new_dict['description'] = task['description']
        if task.get('disabled'):
          if task['disabled'] == False:
            new_dict['disabled'] = 0
          else:
            new_dict['disabled'] = 1
        if 'index' in task and task['index'] != "default":
          new_dict['index'] = task['index']
        if task.get('interval'):
          new_dict['interval'] = task['interval']
        if task.get('sourcetype'):
          new_dict['sourcetype'] = task['sourcetype']
        if task.get('servers'):
          new_dict['servers'] = self.form_new_value(task['servers'])
        if task.get('templates'):
          new_dict['templates'] = self.form_new_value(task['templates'])
        cfm_input.update(stanza_name, new_dict)

    except binding.HTTPError as e:
      logger.error("HTTPError: "+ str(e))
    except KeyError as e:
      logger.error("Keyerror exception: "+ str(e))
    except Exception as e:
      logger.error("exception raised: "+ str(e))

  def transfer_existing_inputs(self):
    """
    This function is used to perform all the operations required to transfer the existing tasks to inputs.conf file.
    """

    dict_inputs_transfer = {}
    has_migrated = "0"
    session_key = utility.get_session_key()
    cfm = conf_manager.ConfManager(session_key, ta_name)
    settings_file_exists = utility.file_exist(settings_conf_file, ta_name)
    if not settings_file_exists:
      utility.create_splunk_ta_f5_settings_conf_file(cfm, inputs_migration_stanza)
    else:
      has_migrated = utility.check_has_migrated_value(cfm, inputs_migration_stanza)
    if has_migrated == "0":
      manage_tasks_exist = self.check_file_exist()
      if manage_tasks_exist:
        tasks_list = self.get_tasks(session_key)
        self.transfer_data_to_inputs(session_key, tasks_list)
      utility.update_settings_conf(session_key, inputs_migration_stanza)

  def form_new_value(self, value):
    """
    This function is used to remove the destination app value from the servers and templates value in the splunk_ta_f5_bigip_tasks.conf file.
    :param value: The function takes the value of the server or template from which the destination app value needs to be removed.
    :return: This function returns the new value formed after removing destination app value from the servers and templates value.
    """

    old_list = value.split(" | ")
    new_list = [server.split(":")[1] for server in old_list]

    return "|".join(new_list)

if __name__ == "__main__":
  migrate_inputs = MigrateExistingInputs()
  migrate_inputs.transfer_existing_inputs()
