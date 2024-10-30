import requests
import json

from app.user_manager import UserManager
# 智普AI的API基本信息
API_BASE_URL = "https://open.bigmodel.cn/"  # 假设的API基础URL
ENDPOINT = "api/paas/v4/chat/completions"  # 假设的文本识别接口端点

def chat(request,query = "原文"):
    # Set your own appid/appkey.
    settings = UserManager().settings.get_settings(request)
    def getSetting(request,setting_id):
        if setting_id and setting_id in settings:
            return settings[setting_id]
    APP_SECRET = getSetting(request,"clhTool.zhipu.key")
    APP_ID = "zhipuApp"

    # 准备认证信息（根据智普AI的认证机制可能有所不同）
    auth_headers = {
        "Authorization": f"Bearer {APP_SECRET}",
        "Content-Type": "application/json"
    }

    # 准备请求体（根据实际的API文档构造）
    # request_data = {
        # "app_id": APP_ID,
        # "image_url": "http://example.com/your-image.jpg",  # 假设的图片URL
        # 或者使用其他字段上传图像数据，比如base64编码的图像字符串
    # }
    request_data = {
        "model": "glm-4",
        "messages": [
            {
                "role": "system",
                "content": "嗨，AI助手！你是一个优秀的画家"
            },
            {
                "role": "user",
                "content": "我想描述一个画面，但我的词汇比较少，希望你能帮我把它变得更生动、更详细。帮我加一些形容词、动词或者其他的细节，让这个画面更加栩栩如生，"
                           "下面是我对画面的描述，返回格式是只有画面描述"
            },
            {
                "role": "user",
                "content": query
            }
        ]
    }

    # 发送请求到智普AI的API端点
    response = requests.post(f"{API_BASE_URL}{ENDPOINT}", headers=auth_headers, data=json.dumps(request_data))

    # 检查响应状态
    if response.status_code == 200:
        # 解析响应数据
        response_data = response.json()
        print("识别结果:", response_data)
        print("识别结果:", response_data.get("result", {}).get("text", "未识别到文本"))
        return response_data
    else:
        # 处理错误
        print(f"请求失败，状态码: {response.status_code}")
        print(f"错误信息: {response.text}")
