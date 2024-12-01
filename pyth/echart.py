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


class EchartGraph_clh:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "chartOptions": ("STRING", {"default": "[1.2.3.4]","forceInput": True}),
            },
            "optional": {
                # "prefix": ("STRING", {"default": ""}),
                # "suffix": ("STRING", {"default": ""}),
            }
        }
    RETURN_TYPES = ()
    FUNCTION = "stringify"
    CATEGORY = "simpleTool_clh"
    DESCRIPTION = "the echart  displayed by options."
    OUTPUT_NODE = True
    def stringify(self,  chartOptions=""):
        return {
            "result": (chartOptions,),
            "ui": {
                "chartOptions": [chartOptions],
            }
        }

class EchartOption_clh:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "title": ("STRING", {"default": "保险"}),
                "xAxis": ("STRING", {"default": '[ "衬衫","羊毛衫","雪纺衫","裤子","高跟鞋","袜子"]',"multiline": True}),
                "data1": ("STRING", {"default": '[1,2,3,4]',"multiline": True}),
                "data1_name": ("STRING", {"default": "销量","multiline": True}),
                "data1_type": (["line","bar","pie"], {"default": "line"}),
            },
            "optional": {
                "data2": ("STRING", {"default": '[1,2,3,4]',"multiline": True}),
                "data2_name": ("STRING", {"default": "比例","multiline": True}),
                "data2_type": (["line","bar","pie"], {"default": "line"}),
            }
        }
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("options",)
    FUNCTION = "stringify"
    CATEGORY = "simpleTool_clh"
    DESCRIPTION = "the echart  displayed by options."
    OUTPUT_NODE = True
    def stringify(self, title,xAxis,data1,data1_name,data1_type,data2,data2_name,data2_type):
        result = {
          "title": {"text": "baoku"},
          "tooltip": {"trigger": "axis"},
          "legend": {
            "data": ["销量1","比例"],
            "left": "center",
            "bottom": "5%"
          },
          "xAxis": {
            "type": "category",
            "data": ["衬衫","羊毛衫","雪纺衫","裤子","高跟鞋","袜子"]
          },
          "yAxis": [
            {
              "type": "value",
              "name": "销量1",
              "min": 0,
              "position": "left",
              "axisLine": {
                "lineStyle": {"color": "#5793f3"}
              },
              # "axisLabel": {"formatter": "{value} 件"}
            },
            {
              "type": "value",
              "name": "比例",
              "position": "right",
              "axisLine": {
                "lineStyle": {
                  "color": "#d14a61"
                }
              },
              # "axisLabel": {"formatter": "{value} °C"}
            }
          ],
          "series": [
            {
              "name": "销量1",
              "type": "bar",
              "data": [50,20,36,10,10,20],
              "yAxisIndex": 0,
              "markPoint": {
                "data": [{"type": "max","name": "最大值"},{"type": "min","name": "最小值"}],
                "label": {"show": True}
              }
            },
            {
              "name": "比例",
              "type": "line",
              "data": [5,20,36,10,100,20],
              "yAxisIndex": 1,
              "markPoint": {
                "data": [{"type": "max","name": "最大值"},{"type": "min","name": "最小值"}],
                "label": {"show": True}
              }
            }
          ]
        }
        result["series"][1]["name"] = data2_name
        result["series"][0]["name"] = data1_name
        result["series"][1]["type"] = data2_type
        result["series"][0]["type"] = data1_type
        result["series"][1]["data"] = json.loads(data2)
        result["series"][0]["data"] = json.loads(data1)
        result["yAxis"][1]["name"] = data2_name
        result["yAxis"][0]["name"] = data1_name
        result["xAxis"]["data"] =  json.loads(xAxis)
        result["title"]["text"] = title
        result["legend"]["data"] = [data1_name,data2_name]
        # 将字典对象转换为 JSON 字符串
        json_string = json.dumps(result)
        return {
            "result": (json_string,),
            "ui": {
            }
        }

class EchartOptionByPath_clh(EchartOption_clh):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "data": ("STRING", {"default": "{}","forceInput":True}),
                "title": ("STRING", {"default": "保险"}),
                "xAxis": (
                "STRING", {"default": '[ "衬衫","羊毛衫","雪纺衫","裤子","高跟鞋","袜子"]', "multiline": True}),
                "data1": ("STRING", {"default": '[1,2,3,4]', "multiline": True}),
                "data1_name": ("STRING", {"default": "销量", "multiline": True}),
                "data1_type": (["line", "bar", "pie"], {"default": "line"}),
            },
            "optional": {
                "data2": ("STRING", {"default": '[1,2,3,4]', "multiline": True}),
                "data2_name": ("STRING", {"default": "比例", "multiline": True}),
                "data2_type": (["line", "bar", "pie"], {"default": "line"}),
            }
        }

    FUNCTION = "stringify_by_path"

    def stringify_by_path(self,data, title,xAxis,data1,data1_name,data1_type,data2,data2_name,data2_type):

        return self.stringify( title,
                               json.dumps( extract_values(json.loads(data), xAxis)),
                               json.dumps(extract_values(json.loads(data), data1)),
                               data1_name,
                               data1_type,
                               json.dumps(extract_values(json.loads(data), data2)),
                               data2_name,
                               data2_type)
# 取路径下的值
def get_value_by_jsonpath(obj, jsonpath):
    # 去掉路径字符串开头的 '$'
    if jsonpath.startswith('$.'):
        jsonpath = jsonpath[2:]

    # 分割路径为各个部分
    parts = jsonpath.split('.')

    # 初始化当前对象为传入的对象
    current = obj

    # 遍历路径的各个部分
    for part in parts:
        # 检查部分是否包含 '[]' 表示索引
        if '[' in part and ']' in part:
            # 提取索引值
            index = int(part[part.index('[') + 1 : part.index(']')])
            # 根据索引获取当前对象的对应元素
            current = current[index]
        else:
            # 根据属性名获取当前对象的对应属性
            current = current[part]

        # 如果当前对象为 None，则路径无效，返回 None
        if current is None:
            return None

    # 返回最终获取的值
    return current


def extract_values(data, path):
    path = path.replace("[", ".[")
    # path = path.replace("]","")
    # 分割路径字符串以便逐层访问对象
    parts = path.strip('$.').split('.')

    # 初始化当前层级为数据本身
    current_level = data

    # 遍历路径的每一部分
    for part in parts:
        # 检查当前层级是否为字典，并且包含当前部分作为键
        if isinstance(current_level, dict) and part in current_level:
            # 根据属性名获取当前对象的对应属性
            current_level = current_level[part]
        # 检查当前部分是否为数组索引
        elif isinstance(current_level, list) :
            is_index = '[' in part and ']' in part
            part = part.replace("[", "").replace("]", "")
            if is_index  and part.isdigit():
                # 如果是索引格式(用户输入的[])直接取下标index的元素
                # 例如  part = '0]'， current_level = [[1,2,3],[4,5,6]]   结果：[1,2,3]
                index = int(part)
                # 确保索引在列表范围内
                if index < len(current_level):
                    current_level = current_level[index]
                else:
                    # 索引超出范围，返回空列表
                    return []
            elif len(part) > 0 :
                # 如果是字段格式，保留数组维度，元素展开key = part的value值，
                # 例如  part = 'name'， current_level = [{name:'张三'},{name:'李四'}]   结果：['张三','李四']
                # 例如  part = 0， current_level = [[1,2,3],[4,5,6]]   结果：[1,4]
                flat_map = []
                for current in current_level :
                    if isinstance(current_level, list) and part.isdigit():
                        index = int(part)
                        # 读取数组中某个字段
                        flat_map.append(current[index])
                    else:
                        # 读取数组中某个字段
                        flat_map.append(current[part])
                current_level = flat_map
        # 如果当前层级不是期望的类型或不包含当前部分，返回空列表
        else:
            return []

    # 否则，直接返回当前层级的值
    else:
        return current_level


NODE_CLASS_MAPPINGS = {
    "EchartGraph_clh": EchartGraph_clh,
    "EchartOption_clh":EchartOption_clh,
    "EchartOptionByPath_clh":EchartOptionByPath_clh

}

NODE_DISPLAY_NAME_MAPPINGS = {}
