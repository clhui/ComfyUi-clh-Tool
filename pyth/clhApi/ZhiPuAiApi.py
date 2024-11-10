import requests
import json

from app.user_manager import UserManager
# ����AI��API������Ϣ
API_BASE_URL = "https://open.bigmodel.cn/"  # �����API����URL
ENDPOINT = "api/paas/v4/chat/completions"  # ������ı�ʶ��ӿڶ˵�

def chat(request,query = ""):
    # Set your own appid/appkey.
    settings = UserManager().settings.get_settings(request)
    def getSetting(request,setting_id):
        if setting_id and setting_id in settings:
            return settings[setting_id]
    APP_SECRET = getSetting(request,"clhTool.zhipu.key")
    APP_ID = "zhipuApp"

    # ׼����֤��Ϣ����������AI����֤���ƿ���������ͬ��
    auth_headers = {
        "Authorization": f"Bearer {APP_SECRET}",
        "Content-Type": "application/json"
    }

    # ׼�������壨����ʵ�ʵ�API�ĵ����죩
    # request_data = {
        # "app_id": APP_ID,
        # "image_url": "http://example.com/your-image.jpg",  # �����ͼƬURL
        # ����ʹ�������ֶ��ϴ�ͼ�����ݣ�����base64�����ͼ���ַ���
    # }
    request_data = {
        "model": "glm-4",
        "messages": [
            {
                "role": "system",
                "content": "�ˣ�AI���֣�����һ������Ļ���"
            },
            {
                "role": "user",
                "content": "��������һ�����棬���ҵĴʻ�Ƚ��٣�ϣ�����ܰ��Ұ�����ø�����������ϸ�����Ҽ�һЩ���ݴʡ����ʻ���������ϸ�ڣ�����������������������"
                           "�������ҶԻ�������������ظ�ʽ��ֻ�л�������"
            },
            {
                "role": "user",
                "content": query
            }
        ]
    }

    # ������������AI��API�˵�
    response = requests.post(f"{API_BASE_URL}{ENDPOINT}", headers=auth_headers, data=json.dumps(request_data))

    # �����Ӧ״̬
    if response.status_code == 200:
        # ������Ӧ����
        response_data = response.json()
        print("ʶ����:", response_data)
        print("ʶ����:", response_data.get("result", {}).get("text", "δʶ���ı�"))
        return response_data
    else:
        # �������
        print(f"����ʧ�ܣ�״̬��: {response.status_code}")
        print(f"������Ϣ: {response.text}")
