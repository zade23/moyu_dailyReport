import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import json
import os
import time
import sys
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# 设置详细的日志记录
def log_message(message):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")
    sys.stdout.flush()  # 确保输出立即显示，不被缓存

log_message(f"脚本启动，Python版本: {sys.version}")
log_message(f"当前工作目录: {os.getcwd()}")

# 获取配置文件的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, "config.json")
log_message(f"配置文件路径: {config_path}")

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
    
    log_message("配置文件加载成功")
    
except Exception as e:
    log_message(f"配置文件加载错误: {str(e)}")
    exit(1)

# 配置重试策略
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("http://", adapter)
session.mount("https://", adapter)

# 需要先获取飞书API访问令牌tenant_access_token
try:
    log_message("开始获取访问令牌...")
    token_response = session.post(tenant_token_url, json=tenant_token_data, timeout=30)
    log_message(f"令牌响应状态码: {token_response.status_code}")
    token_response.raise_for_status()
    response_json = token_response.json()
    log_message(f"令牌响应内容: {json.dumps(response_json)[:100]}...")
    access_token = response_json.get("tenant_access_token")
    if not access_token:
        raise Exception(f"未能从响应中获取tenant_access_token: {response_json}")
    log_message("访问令牌获取成功")
except requests.exceptions.RequestException as e:
    log_message(f"获取访问令牌失败: {str(e)}")
    if hasattr(e, 'response') and e.response is not None:
        log_message(f"错误响应: {e.response.text}")
    exit(1)

try:
    # 直接从API获取摸鱼日报图片
    log_message(f"开始从API获取图片: {api_url}")
    image_response = session.get(api_url, timeout=30)
    image_response.raise_for_status()
    image_content = image_response.content
    log_message(f"成功获取图片，大小: {len(image_content)} 字节")
    
    # 上传图片到飞书
    log_message("准备上传图片到飞书...")
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
    
    # 添加重试逻辑
    max_retries = 3
    for attempt in range(max_retries):
        try:
            log_message(f"上传尝试 {attempt+1}/{max_retries}...")
            upload_response = session.post(
                upload_url, 
                headers=headers, 
                data=multipart_data, 
                timeout=60
            )
            log_message(f"上传响应状态码: {upload_response.status_code}")
            upload_response.raise_for_status()
            upload_result = upload_response.json()
            log_message(f"上传响应内容: {json.dumps(upload_result)[:100]}...")
            break
        except requests.exceptions.RequestException as e:
            log_message(f"上传尝试 {attempt+1} 失败: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                log_message(f"错误响应: {e.response.text}")
            if attempt < max_retries - 1:
                log_message(f"将在3秒后重试...")
                time.sleep(3)
                # 需要重新创建 MultipartEncoder 对象，因为它不可重用
                multipart_data = MultipartEncoder(
                    fields={
                        "image_type": "message",
                        "image": ("moyu.jpg", image_content, "image/jpeg"),
                    }
                )
                headers["Content-Type"] = multipart_data.content_type
            else:
                raise
    
    # 从上传响应中获取image_key
    image_key = upload_result.get("data", {}).get("image_key", "")
    
    if not image_key:
        raise Exception(f"无法获取image_key，响应内容: {json.dumps(upload_result)}")
        
    log_message(f"获取到image_key: {image_key}")
    
    # 使用image_key发送图片消息
    message = {
        "msg_type": "image",
        "content": {
            "image_key": image_key
        }
    }
    
    log_message("开始发送图片消息...")
    send_response = session.post(
        webhook_url, 
        headers={"Content-Type": "application/json"}, 
        json=message,
        timeout=30
    )
    log_message(f"发送响应状态码: {send_response.status_code}")
    send_response.raise_for_status()
    
    log_message("摸鱼日报图片发送成功")
    
except Exception as e:
    log_message(f"发生错误: {str(e)}")

    # 发送错误通知
    try:
        error_message = {
            "msg_type": "text",
            "content": {
                "text": f"摸鱼日报获取失败: {str(e)}"
            }
        }
        session.post(webhook_url, headers={"Content-Type": "application/json"}, json=error_message, timeout=30)
    except Exception as notify_error:
        log_message(f"发送错误通知也失败了: {str(notify_error)}")