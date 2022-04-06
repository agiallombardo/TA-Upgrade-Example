import splunk.entity as entity
import import_declare_test
from solnlib import conf_manager, credentials
from log_manager import setup_logging
from import_declare_test import ta_name, servers_conf, settings_conf_file, passwords_migration_stanza, existing_servers_conf
import splunk_ta_f5_utility as utility 

logger = setup_logging("migrate_existing_passwords")

class MigrateExistingPasswords():
  """
  This class is used to migrate the existing passwords to the new format.
  """

  def update_server_conf(self, session_key, creds_list):
    """
    This function is used to update the f5_servers.conf file.
    :param session_key: The session_key value.
    :param creds_list: The list of existing credentials.
    """

    try:
      cfm = conf_manager.ConfManager(session_key, ta_name, realm="__REST_CREDENTIAL__#{}#configs/conf-f5_servers".format(ta_name))
      servers_conf_exist = utility.file_exist(servers_conf, ta_name)
      if not servers_conf_exist:
        cfm.create_conf(servers_conf)
      servers_conf_obj = cfm.get_conf(servers_conf)
      for value in creds_list:
        server_name = value['name']
        del value['name']
        servers_conf_obj.update(server_name, value, ['account_password', 'confirm_account_password'])

    except Exception as e:
      logger.error("Exception occured while getting servers_conf object {} ".format(e))

  def get_server_details(self, session_key, destination_app, creds_dict, server_name):
    """
    :param session_key: The session_key value.
    :param destination_app: The name of the destination app.
    :param creds_dict: The dictionary in which the server details will be stored.
    :param server_name: The name of the server for which the migration should take place.
    :return: The function returns the server details stored in the f5_servers.conf file.
    """

    try:
      dest_app_conf_obj = conf_manager.ConfManager(session_key, destination_app)
      server_conf_obj = dest_app_conf_obj.get_conf(existing_servers_conf)
      if server_conf_obj.stanza_exist(server_name):
        server_creds = {}
        creds_dict = server_conf_obj.get(server_name)
        if creds_dict.get('description'):
          server_creds['description'] = creds_dict['description']
        if creds_dict.get('interval'):
          server_creds['interval'] = creds_dict['interval']
        if creds_dict.get('f5_bigip_partitions'):
          server_creds['f5_bigip_partitions'] = creds_dict['f5_bigip_partitions']
        if creds_dict.get('f5_bigip_url'):
          server_creds['f5_bigip_url'] = creds_dict['f5_bigip_url']
        return server_creds

    except credentials.CredentialNotExistException:
      pass
    except Exception as e:
      logger.error("Exception occured while getting server details from other app {}".format(e))

    return {}

  def get_credentials(self, session_key):
    """
    :param session_key: The session_key value.
    :return creds_list: Returns the list of the existing credentials
    """

    creds_list = []
    old_realm = "_Splunk_TA_f5-bigip_account_#"
    try:
      entities = entity.getEntities(
        ["admin", "passwords"],
        namespace=ta_name,
        owner="nobody",
        sessionKey=session_key,
        count=-1,
        search=ta_name,
      )
      for stanza, value in entities.items():
        creds_dict = {}
        if 'realm' in value:
          realm = value['realm']
          if old_realm in realm:
            destination_app =  realm.split("#")[1]
            server_conf_exist = utility.file_exist(existing_servers_conf, destination_app)    
            if server_conf_exist:
              if "username" in value:
                update_old_realm = "".join([old_realm, destination_app, "#"])
                server_name = realm.replace(update_old_realm, "")
                creds_dict = self.get_server_details(session_key, destination_app, creds_dict, server_name)

                if "clear_password" in value:
                  creds_dict['name'] = server_name
                  creds_dict['account_name'] = value['username']
                  creds_dict['account_password'] = value['clear_password']
                  creds_dict['confirm_account_password'] = value['clear_password']
                  creds_list.append(creds_dict)
    except Exception as e:
      logger.error("error while getting entities {} ".format(e))

    return creds_list

  def migrate_existing_passwords(self):
    """
    This function is used to migrate the existing passwords to the new format.
    """

    has_migrated = "0"
    session_key = utility.get_session_key()
    cfm = conf_manager.ConfManager(session_key, ta_name)
    setting_conf_exist = utility.file_exist(settings_conf_file, ta_name)
    if not setting_conf_exist:
      utility.create_splunk_ta_f5_settings_conf_file(cfm, passwords_migration_stanza)
    else:
      has_migrated = utility.check_has_migrated_value(cfm, passwords_migration_stanza)

    if has_migrated == "0":
      creds = self.get_credentials(session_key)
      self.update_server_conf(session_key, creds)
      utility.update_settings_conf(session_key, passwords_migration_stanza)

if __name__ == "__main__":
  migrate_passwords = MigrateExistingPasswords()
  migrate_passwords.migrate_existing_passwords()
