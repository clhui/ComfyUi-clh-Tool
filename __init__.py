"""
@author: Dr.Lt.Data
@title: CLH simple Tool
@nickname: CLH Simple Tool
@description: This extension offers various detector nodes and detailer nodes that allow you to configure a workflow that automatically enhances facial details. And provide iterative upscaler.
"""
import importlib
import sys, os
# from .pyth.service.server import Cancelled
from .pyth.service.clh_server import Cancelled

sys.path.insert(0,os.path.dirname(os.path.realpath(__file__)))


node_list = [
    "fat_labels",
    "logic",
    "math_expression",
]

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
for module_name in node_list:
    imported_module = importlib.import_module(".pyth.{}".format(module_name), __name__)
    NODE_CLASS_MAPPINGS = {**NODE_CLASS_MAPPINGS, **imported_module.NODE_CLASS_MAPPINGS}
    NODE_DISPLAY_NAME_MAPPINGS = {**NODE_DISPLAY_NAME_MAPPINGS, **imported_module.NODE_DISPLAY_NAME_MAPPINGS}
WEB_DIRECTORY = f"web_version"
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', "WEB_DIRECTORY"]

VERSION = "1.2.7"
