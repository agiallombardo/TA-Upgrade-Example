
import os
import sys
import re
from os.path import dirname

sys.path.insert(0, os.path.sep.join([os.path.dirname(os.path.realpath(os.path.dirname(__file__))), 'lib']))
if sys.version_info < (3, 0):
    sys.path.insert(0, os.path.sep.join([os.path.dirname(os.path.realpath(os.path.dirname(__file__))), 'lib', 'py2']))
else:
    sys.path.insert(0, os.path.sep.join([os.path.dirname(os.path.realpath(os.path.dirname(__file__))), 'lib', 'py3']))

ta_name = 'Splunk_TA_f5-bigip'
tasks_conf_file = "f5_bigip_tasks"
inputs_conf_file = "inputs"
settings_conf_file = "splunk_ta_f5_settings"
existing_templates_conf = 'f5_bigip_templates'
existing_servers_conf = 'f5_bigip_servers'
passwords_migration_stanza = "passwords_migration"
inputs_migration_stanza = "inputs_migration"
templates_migration_stanza = "templates_migration"
servers_conf = 'f5_servers'
templates_conf = 'f5_templates'