import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import json
import os

# 获取配置文件的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, "config.json")

# 从配置文件中加载敏感信息
try:
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    
    webhook_url = config["webhook_url"]
    tenant_token_url = config["tenant_token_url"]
    tenant_token_data = {
        "app_id": config["app_id"],
        "app_secret": config["app_secret"]
    }
    upload_url = config["upload_url"]
    api_url = config["api_url"]
    
except Exception as e:
    print(f"配置文件加载错误: {str(e)}")
    exit(1)

# 需要先获取飞书API访问令牌tenant_access_token
token_response = requests.post(tenant_token_url, json=tenant_token_data)
token_response.raise_for_status()
access_token = token_response.json().get("tenant_access_token")

try:
    # 直接从API获取摸鱼日报图片
    image_response = requests.get(api_url)
    image_response.raise_for_status()
    image_content = image_response.content
    
    # 上传图片到飞书
    multipart_data = MultipartEncoder(
        fields={
            "image_type": "message",
            "image": ("moyu.jpg", image_content, "image/jpeg"),
        }
    )
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": multipart_data.content_type,
    }
    
    upload_response = requests.post(upload_url, headers=headers, data=multipart_data)
    upload_response.raise_for_status()
    upload_result = upload_response.json()
    
    # 从上传响应中获取image_key
    image_key = upload_result.get("data", {}).get("image_key", "")
    
    if not image_key:
        raise Exception("无法获取image_key")
        
    print(f"获取到image_key: {image_key}")
    
    # 使用image_key发送图片消息
    message = {
        "msg_type": "image",
        "content": {
            "image_key": image_key
        }
    }
    
    send_response = requests.post(
        webhook_url, 
        headers={"Content-Type": "application/json"}, 
        json=message
    )
    send_response.raise_for_status()
    
    print("摸鱼日报图片发送成功")
    
except Exception as e:
    print(f"发生错误: {str(e)}")

    # 发送错误通知
    try:
        error_message = {
            "msg_type": "text",
            "content": {
                "text": f"摸鱼日报获取失败: {str(e)}"
            }
        }
        requests.post(webhook_url, headers={"Content-Type": "application/json"}, json=error_message)
    except:
        pass