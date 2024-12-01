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
                "data1_name": ("STRING", {"default": "销量","multiline": True}),
                "data1_type": (["line","bar","pie"], {"default": "line"}),
                "data1": ("STRING", {"default": '[1,2,3,4]',"multiline": True}),
                "markLine1": ("STRING", {"default": '0'}),
            },
            "optional": {
                "data2": ("STRING", {"default": '[1,2,3,4]',"multiline": True}),
                "data2_name": ("STRING", {"default": "比例","multiline": True}),
                "data2_type": (["line","bar","pie"], {"default": "line"}),
                "markLine2": ("STRING", {"default": '0'}),
            }
        }
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("options",)
    FUNCTION = "stringify"
    CATEGORY = "simpleTool_clh"
    DESCRIPTION = "the echart  displayed by options."
    OUTPUT_NODE = True
    def stringify(self, title,xAxis,data1,data1_name,data1_type,markLine1,data2,data2_name,data2_type,markLine2):
        result = {
            "title": {"text": "baoku"},
            "tooltip": {"trigger": "axis"},
            "legend": {
            "data": ["销量1","比例"],
            "left": "center",
            "bottom": "10px"
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
                        # "lineStyle": {"color": "#5793f3"}
                    },
                    # "axisLabel": {"formatter": "{value} 件"}
                },
                {
                    "type": "value",
                    "name": "比例",
                    "position": "right",
                    "axisLine": {
                    # "lineStyle": {"color": "#d14a61"}
                    },
                    # "axisLabel": {"formatter": "{value} °C"}
                }
            ],
            #数据列表
            "series": [
            ]
        }
        result["series"].append( build_series_opiton(data1_type,data1_name,data1,markLine1,xAxis,result["series"]))

        result["series"].append( build_series_opiton(data2_type,data2_name,data2,markLine2,xAxis,result["series"]))
        if data1_type == "pie" and data2_type == "pie":
            # 都是饼图排一下位置
            result["series"][0]["radius"] = '40%'
            result["series"][1]["radius"] = '40%'
            result["series"][0]["center"] = ['30%', '50%']
            result["series"][1]["center"] = ['70%', '50%']
        # else:
        #     result["series"][0]["center"] = None
        #     result["series"][1]["center"] = None
        result["yAxis"][0]["name"] = data1_name
        result["yAxis"][1]["name"] = data2_name
        result["xAxis"]["data"] =  json.loads(xAxis)
        result["title"]["text"] = title
        result["legend"]["data"] = [data1_name, data2_name]
        # 将字典对象转换为 JSON 字符串
        json_string = json.dumps(result)
        return {
            "result": (json_string,),
            "ui": {
            }
        }
def build_series_opiton(data_type,data_name,dataList,markLine,xAxis,series) :
    if data_type == "pie":
        pie_option = {
            "name": data_name,
            "type": "pie",
            "radius": "50%",
            "data": [
                {"value": 1048, "name": "搜索引擎"},
                {"value": 735, "name": "直接访问"},
                {"value": 580, "name": "邮件营销"},
                {"value": 484, "name": "联盟广告"},
                {"value": 300, "name": "视频广告"}
            ],
            "emphasis": {
                "itemStyle": {
                    "shadowBlur": 10,
                    "shadowOffsetX": 0,
                    "shadowColor": "rgba(0, 0, 0, 0.5)"
                }
            },
            "label": {
                "show": True, #// 显示标签
                "formatter": '{b}: {c} ({d}%)' #// 格式化标签
            }
        }
        combined_list = [{'name': letter, 'value': number} for letter, number in zip(json.loads(xAxis),json.loads(dataList),)]
        pie_option["data"] = combined_list
        # pie_option["center"] = None
        return pie_option
    else:
        line_option = {
            "name": data_name, "type": data_type, "data": json.loads(dataList), "yAxisIndex": len(series),
            "markPoint": {
               "data": [{"type": "max", "name": "最大值"}, {"type": "min", "name": "最小值"}],
               "label": {"show": True}
           },
            "markLine": {
                "data": [
                    {
                        "yAxis": markLine,
                        "name": data_name + '标记线',
                        "label": {
                            "show": True,
                            "formatter": data_name + '的标记线'
                        },
                        "lineStyle": {
                            "type": 'dashed', #// 虚线
                            "color": 'red', #// 红色
                            "width": 2 #// 线宽
                        }}  # 设置基线的y轴值
                ]
            }}

        return line_option


class EchartOptionByPath_clh(EchartOption_clh):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "data": ("STRING", {"default": "{}","forceInput":True}),
                "title": ("STRING", {"default": "保险"}),
                "xAxis": ( "STRING", {"default": '$.data[0].0.name', "multiline": False,"title":"X轴类别"}),
                "data1_name": ("STRING", {"default": "销量", "multiline": False}),
                "data1_type": (["line", "bar", "pie"], {"default": "line"}),
                "data1": ("STRING", {"default": '$.data[0].0.name', "multiline": False}),
                "markLine1": ("STRING", {"default": '0'}),
            },
            "optional": {
                "data2_name": ("STRING", {"default": "比例", "multiline": False}),
                "data2_type": (["line", "bar", "pie"], {"default": "line"}),
                "data2": ("STRING", {"default": '$.data[0].0.name', "multiline": False}),
                "markLine2": ("STRING", {"default": '0'}),
            }
        }

    FUNCTION = "stringify_by_path"

    def stringify_by_path(self,data, title,xAxis,data1,data1_name,data1_type,markLine1,data2,data2_name,data2_type,markLine2):

        return self.stringify( title,
                               json.dumps( extract_values(json.loads(data), xAxis)),
                               json.dumps(extract_values(json.loads(data), data1)),
                               data1_name,
                               data1_type,
                               markLine1,
                               json.dumps(extract_values(json.loads(data), data2)),
                               data2_name,
                               data2_type,markLine2)
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
