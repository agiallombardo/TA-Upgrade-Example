
import sys
import os
if sys.version_info[0] < 3:
    suds_py2_path = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "suds_py2")
    sys.path.insert(0, suds_py2_path)
else:
    suds_py3_path = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "suds_py3")
    sys.path.insert(0, suds_py3_path)
import suds