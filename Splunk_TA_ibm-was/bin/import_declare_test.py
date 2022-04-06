import os
import sys
import re

try:
    import queue
    import http
except:
    pass

ta_name = 'Splunk_TA_ibm-was'
ta_lib_name = 'splunk_ta_ibm_was'
pattern = re.compile(r'[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$')
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name]))
sys.path = new_paths
