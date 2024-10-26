from typing import Iterator, List, Tuple, Dict, Any, Union, Optional
from _decimal import Context, getcontext
from decimal import Decimal

from comfy_execution.graph_utils import GraphBuilder
from .libs.utils import AlwaysEqualProxy, ByPassTypeTuple, cleanGPUUsedForce, compare_revision
from .libs.cache import cache, update_cache, remove_cache
from .libs.log import log_node_info, log_node_warn
from nodes import PreviewImage, SaveImage
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from PIL.PngImagePlugin import PngInfo
import numpy as np
import os
import re
import csv
import json
import torch
import comfy.utils
import folder_paths

DEFAULT_FLOW_NUM = 2
MAX_FLOW_NUM = 10
lazy_options = {"lazy": True} if compare_revision(2543) else {}

any_type = AlwaysEqualProxy("*")


def validate_list_args(args: Dict[str, List[Any]]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Checks that if there are multiple arguments, they are all the same length or 1
    :param args:
    :return: Tuple (Status, mismatched_key_1, mismatched_key_2)
    """
    # Only have 1 arg
    if len(args) == 1:
        return True, None, None

    len_to_match = None
    matched_arg_name = None
    for arg_name, arg in args.items():
        if arg_name == 'self':
            # self is in locals()
            continue

        if len(arg) != 1:
            if len_to_match is None:
                len_to_match = len(arg)
                matched_arg_name = arg_name
            elif len(arg) != len_to_match:
                return False, arg_name, matched_arg_name

    return True, None, None


def error_if_mismatched_list_args(args: Dict[str, List[Any]]) -> None:
    is_valid, failed_key1, failed_key2 = validate_list_args(args)
    if not is_valid:
        assert failed_key1 is not None
        assert failed_key2 is not None
        raise ValueError(
            f"Mismatched list inputs received. {failed_key1}({len(args[failed_key1])}) !== {failed_key2}({len(args[failed_key2])})"
        )


def zip_with_fill(*lists: Union[List[Any], None]) -> Iterator[Tuple[Any, ...]]:
    """
    Zips lists together, but if a list has 1 element, it will be repeated for each element in the other lists.
    If a list is None, None will be used for that element.
    (Not intended for use with lists of different lengths)
    :param lists:
    :return: Iterator of tuples of length len(lists)
    """
    max_len = max(len(lst) if lst is not None else 0 for lst in lists)
    for i in range(max_len):
        yield tuple(None if lst is None else (lst[0] if len(lst) == 1 else lst[i]) for lst in lists)


# ---------------------------------------------------------------类型 开始----------------------------------------------------------------------#

# ---------------------------------------------------------------Index Switch----------------------------------------------------------------------#


COMPARE_FUNCTIONS = {
    "a == b": lambda a, b: a == b,
    "a != b": lambda a, b: a != b,
    "a < b": lambda a, b: a < b,
    "a > b": lambda a, b: a > b,
    "a <= b": lambda a, b: a <= b,
    "a >= b": lambda a, b: a >= b,
}


class JoinStringMulti_clh:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "delimiter": ("STRING", {"default": ' ', "multiline": True}),
                "inputcount": ("INT", {"default": 2, "min": 2, "max": 1000, "step": 1}),
                "string_1": ("STRING", {"default": '', "forceInput": True}),
                "string_2": ("STRING", {"default": '', "forceInput": True}),
            },
            "optional": {
            },
            "hidden": {
                "return_list": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("string",)
    FUNCTION = "combine"
    CATEGORY = "simpleTool_clh"
    DESCRIPTION = """
                Creates single string, or a list of strings, from  
                multiple input strings.  
                You can set how many inputs the node has,  
                with the **inputcount** and clicking update.
                """

    def combine(self, inputcount, delimiter, **kwargs):
        string = kwargs["string_1"]
        return_list = False #//kwargs["return_list"]
        strings = [string]  # Initialize a list with the first string
        for c in range(1, inputcount):
            keyStr = f"string_{c + 1}"
            if(kwargs.__contains__(keyStr)):
                new_string = kwargs[f"string_{c + 1}"]
                if return_list:
                    strings.append(new_string)  # Add new string to the list
                else:
                    string = string + delimiter + new_string

        if return_list:
            return (strings,)  # Return the list of strings
        else:
            return (string,)  # Return the combined string


NODE_CLASS_MAPPINGS = {
    "JoinStringMulti_clh": JoinStringMulti_clh

}

NODE_DISPLAY_NAME_MAPPINGS = {}
