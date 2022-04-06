import os
import json
import splunk.rest as rest
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

import import_declare_test
from solnlib import conf_manager
from log_manager import setup_logging
from import_declare_test import settings_conf_file, ta_name, templates_conf, templates_migration_stanza, existing_templates_conf
import splunk_ta_f5_utility as utility

try:
  import sys
  sys.path.insert(0, make_splunkhome_path(['etc', 'apps', ta_name, 'appserver', 'controllers']))
  import manage_templates
except Exception as e:
  pass

from Modules.F5Templates import F5TemplatesManager

logger = setup_logging("migrate_existing_templates")

class MigrateExistingTemplates():
  """
  This class is used to migrate the existing templates to the new UCC based addon.
  """

  def check_file_exist(self):
    """
    This function is used to check if the controllers directory exists or not.
    :return: The function returns True if file exists otherwise returns False.
    """

    file_path = make_splunkhome_path(['etc', 'apps', ta_name, 'appserver', 'controllers', 'manage_templates.py'])
    if os.path.isfile(file_path):
      return True
    else:
      return False

  def get_templates(self, session_key):
    """
    This function is used to get the templates that are configured in the existing addon.
    :param session_key: The session key value.
    :return result: The function returns the list of templates that are configured in the existing addon.
    """

    templates_obj = F5TemplatesManager(session_key).all()
    result = []
    for template in templates_obj:
      result.append(template.to_dict())

    return result

  def get_template_migration_list(self, templates_list):
    """
    This function is used to get the list of the templates that are to be migrated.
    :param templates_list: The list of all the templates that are configured in the existing addon.
    :return: The list of templates that are to be migrated.
    """

    template_migrate_list = []
    for template in templates_list:
      template_dict = {}
      if template.get('name'):
        template_dict['name'] = template['name']
        if template.get('description'):
          template_dict['description'] = template['description']
        if template.get('content'):
          template_dict['content'] = utility.encode(template['content'])
        template_migrate_list.append(template_dict)

    return template_migrate_list

  def migrate_template(self, session_key, template_migration_list):
    """
    This function is used to migrate the templates.
    :param session_key: The session key value.
    :param template_migration_list: The list of the templates that are to be migrated.
    """

    try:
      cfm = conf_manager.ConfManager(session_key, ta_name)
      templates_conf_exist = utility.file_exist(templates_conf, ta_name)
      if not templates_conf_exist:
        cfm.create_conf(templates_conf)
      cfm_template = cfm.get_conf(templates_conf)
      for template in template_migration_list:
        template_dict = {}
        template_name = template['name']
        if template.get("description"):
          template_dict['description'] = template['description']
        if template.get("content"):
          template_dict['content'] = template['content']
        cfm_template.update(template_name, template_dict)

    except binding.HTTPError as e:
      logger.error("HTTPError: "+ str(e))
    except KeyError as e:
      logger.error("Keyerror exception: "+ str(e))
    except Exception as e:
      logger.error("exception raised: "+ str(e))

  def migrate_existing_templates(self):
    """
    This function is used to migrate the existing templates.
    """

    has_migrated = "0"
    session_key = utility.get_session_key()
    cfm = conf_manager.ConfManager(session_key, ta_name)
    settings_file_exists = utility.file_exist(settings_conf_file, ta_name)
    if not settings_file_exists:
      utility.create_splunk_ta_f5_settings_conf_file(cfm, templates_migration_stanza)
    else:
      has_migrated = utility.check_has_migrated_value(cfm, templates_migration_stanza)
    
    if has_migrated == "0":
      manage_templates_exist = self.check_file_exist()
      if manage_templates_exist:
        templates_list = self.get_templates(session_key)
        template_migration_list = self.get_template_migration_list(templates_list)
        self.migrate_template(session_key, template_migration_list)
      utility.update_settings_conf(session_key, templates_migration_stanza)


if __name__ == "__main__":
  migrate_templates = MigrateExistingTemplates()
  migrate_templates.migrate_existing_templates()
