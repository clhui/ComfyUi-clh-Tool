# -*- coding: utf-8 -*-

# This code shows an example of text translation from English to Simplified-Chinese.
# This code runs on Python 2.7.x and Python 3.x.
# You may install `requests` to run this code: pip install requests
# Please refer to `https://api.fanyi.baidu.com/doc/21` for complete clhApi document
#
# import requests
import random
import json
from hashlib import md5

import requests
import hashlib
from app.app_settings import AppSettings
from app.user_manager import UserManager


def baiduTranslateApi(request,query = ""):
    # Set your own appid/appkey.
    settings = UserManager().settings.get_settings(request)
    def getSetting(request,setting_id):
        if setting_id and setting_id in settings:
            return settings[setting_id]
    bdappid = getSetting(request,"clhTool.translate.appid")
    bdappkey = getSetting(request,"clhTool.translate.key")

    # For list of language codes, please refer to `https://api.fanyi.baidu.com/doc/21`
    from_lang = 'en'
    to_lang =  'zh'

    endpoint = 'http://api.fanyi.baidu.com'
    path = '/clhApi/trans/vip/translate'
    url = endpoint + path


    # Generate salt and sign
    def make_md5(s, encoding='utf-8'):
        return md5(s.encode(encoding,"utf-8")).hexdigest()

    salt = random.randint(32768, 65536)
    sign = make_md5(bdappid + query + str(salt) + bdappkey)

    # Build request
    # headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload = {'appid': bdappid, 'q': query, 'from': from_lang, 'to': to_lang, 'salt': salt, 'sign': sign}

    # Send request
    r = requests.post(url, params=payload)
    result = r.json()
    # Show response
    print(json.dumps(result, indent=4, ensure_ascii=False))
    return result

def translate(request,text, from_lang='en', to_lang='zh'):
    # Set your own appid/appkey.
    settings = UserManager().settings.get_settings(request)

    def getSetting(request, setting_id):
        if setting_id and setting_id in settings:
            return settings[setting_id]

    bdappid = getSetting(request, "clhTool.translate.appid")
    bdappkey = getSetting(request, "clhTool.translate.key")
    url = "http://api.fanyi.baidu.com/api/trans/vip/translate"
    salt = str(random.randint(32768, 65536))
    sign = bdappid + text + salt + bdappkey

    m = hashlib.md5()
    m.update(sign.encode())
    sign = m.hexdigest()
    text_without_newlines = text.replace("\n", "")

    payload = {
        'q': text_without_newlines,
        'from': from_lang,
        'to': to_lang,
        'appid': bdappid,
        'salt': salt,
        'sign': sign
    }
    response = requests.post(url, data=payload)
    result = response.json()
    if 'trans_result' in result:
        return result
    else:
        return "Translation error."
