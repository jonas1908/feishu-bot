import os
import json
import logging
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from query import query_player

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 环境变量
APP_ID = os.environ.get("FEISHU_APP_ID")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET")

def do_p2_im_message_receive_v1(data: lark.CustomizedEvent):
    """处理收到的消息"""
    try:
        event = data.event
        message = event.get("message", {})
        chat_id = message.get("chat_id", "")
        msg_type = message.get("message_type", "")
        content_str = message.get("content", "{}")
        
        if msg_type != "text":
            return
        
        content = json.loads(content_str)
        text = content.get("text", "").strip()
        
        # 去掉@机器人的部分
        # 飞书@机器人格式: @_user_1 /查 xxx
        if "@" in text:
            # 移除所有@mention
            parts = text.split()
            text = " ".join([p for p in parts if not p.startswith("@")])
            text = text.strip()
        
        # 支持命令: /查 UID 或 /q UID
        if text.startswith("/查") or text.startswith("/q"):
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                reply_text(chat_id, "❌ 格式: /查 玩家UID\n例如: /查 1586971890000071")
                return
            
            uid = parts[1].strip()
            result = query_player(uid)
            reply_text(chat_id, result)
        
        elif text.startswith("/帮助") or text.startswith("/help"):
            help_msg = (
                "📖 使用指南\n"
                "━━━━━━━━━━━━━━━\n"
                "/查 UID — 查询玩家档案\n"
                "/帮助 — 显示本帮助\n"
                "━━━━━━━━━━━━━━━\n"
                "示例: /查 1586971890000071"
            )
            reply_text(chat_id, help_msg)
    
    except Exception as e:
        logger.error(f"处理消息异常: {e}")

def reply_text(chat_id: str, text: str):
    """回复文本消息到群"""
    client = lark.Client.builder().app_id(APP_ID).app_secret(APP_SECRET).build()
    
    content = json.dumps({"text": text})
    
    request = CreateMessageRequest.builder() \
        .receive_id_type("chat_id") \
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type("text")
            .content(content)
            .build()
        ).build()
    
    response = client.im.v1.message.create(request)
    if not response.success():
        logger.error(f"发送消息失败: {response.code} - {response.msg}")

def main():
    # 长连接模式
    event_handler = lark.EventDispatcherHandler.builder("", "") \
        .register_p1_customized_event("im.message.receive_v1", do_p2_im_message_receive_v1) \
        .build()
    
    cli = lark.ws.Client(
        APP_ID,
        APP_SECRET,
        event_handler=event_handler,
        log_level=lark.LogLevel.INFO
    )
    cli.start()

if __name__ == "__main__":
    main()