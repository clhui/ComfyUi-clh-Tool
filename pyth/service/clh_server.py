import os

from envs.linly.Lib.venv import logger

from app.app_settings import AppSettings
from server import PromptServer


from ..clhApi import Baidu_Text_transAPI
from ..clhApi import ZhiPuAiApi
# from ...server import PromptServer
from aiohttp import web
import json


class Cancelled(Exception):
    pass
def read_file_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        return '{"appid": "","key": "","help": "在上方填写百度翻译API的appid和key,注意你需要申请好翻译权限，否则翻译会不成功~"}'
    except Exception as e:
         return '{"appid": "","key": "","help": "在上方填写百度翻译API的appid和key,注意你需要申请好翻译权限，否则翻译会不成功~"}'
    return None
def string_to_json(json_string):
    try:
        json_object = json.loads(json_string)
        return json_object
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        return None
    
@PromptServer.instance.routes.get("/clh_server")
async def clhGetApi(request):
         tget = request.rel_url.query
         gtype =  tget['type']
         config_path = os.path.join(os.path.dirname(__file__), "ini.json")
         if gtype == "getpz":

            config = {
             "appid": AppSettings.get_settings("clhTool.translate.appid"),
             "key": AppSettings.get_settings("clhTool.translate.key"),
             "help": "在上方填写百度翻译API的appid和key,注意你需要申请好翻译权限，否则翻译会不成功~",
             "zhitsc": "请你根据我输入的AI绘画提示词，进行专业的润色，并用中文直接输出结果（输出结果不要附带任何无关内容），以下是我的AI绘画提示词：",
             "zhipukey": AppSettings.get_settings("clhTool.zhipu.key"),
            }
            # return web.json_response(string_to_json(read_file_content(config_path)), content_type='application/json')
            return web.json_response(config, content_type='application/json')
         else:
             return web.json_response({"v":gtype}, content_type='application/json')
@PromptServer.instance.routes.get("/clhhome")
async def clhWeb(request):
         return web.Response(
                text="hi",
                content_type="text/html",
            )
@PromptServer.instance.routes.post('/clh_server')
async def clhpostapi(request):
    post = await request.post()
    bdappid = post.get("bdappid")
    bdappkey = post.get("appbdkey") 
    zhitsc = post.get("zhitsc")
    zhipukey = post.get("zhipukey") 
    if bdappid and bdappkey:
        config_path = os.path.join(os.path.dirname(__file__), "ini.json")
        config_data = string_to_json(read_file_content(config_path))
        print(f"Comfyui_fk_server：密钥设置成功")
        config_data["appid"] = bdappid
        config_data["key"] = bdappkey
        config_data["zhitsc"] = zhitsc
        config_data["zhipukey"] = zhipukey
        with open(config_path, 'w', encoding='utf-8') as file:
             json.dump(config_data, file, ensure_ascii=False, indent=4)
    return web.json_response({})

@PromptServer.instance.routes.post('/clh_translate')
async def clhTranslateApi(request):
    post = await request.json()

    logger.info(post)
    # result = Baidu_Text_transAPI.baiduTranslateApi(request,post.get("query"))
    result = Baidu_Text_transAPI.translate(request,post.get("query"),post.get("from"),post.get("to"))
    return web.json_response(result)

@PromptServer.instance.routes.post('/clh_zhipu')
async def clhZhipuApi(request):
    post = await request.json()

    logger.info(post)
    # result = Baidu_Text_transAPI.baiduTranslateApi(request,post.get("query"))
    result = ZhiPuAiApi.chat(request,post.get("query"))
    return web.json_response(result)


print(f"\33[93m》===>====>========>Clh_Server:OK!<========<====<===《\33[0m")

