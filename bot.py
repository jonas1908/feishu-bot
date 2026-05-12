import os
import json
import logging
import lark_oapi as lark
from lark_oapi.api.im.v1 import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

APP_ID = os.environ.get("FEISHU_APP_ID")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET")

def on_message(data: lark.im.v1.P2ImMessageReceiveV1):
    """处理收到的消息"""
    try:
        message = data.event.message
        chat_id = message.chat_id
        msg_type = message.message_type

        if msg_type != "text":
            return

        content = json.loads(message.content)
        text = content.get("text", "").strip()

        # 去掉@机器人部分（格式为 @_user_1）
        import re
        text = re.sub(r"@_user_\d+", "", text).strip()

        # 支持: /查 UID、查 UID、查UID
        if text.startswith("/查"):
            uid = text[2:].strip()
        elif text.startswith("查"):
            uid = text[1:].strip()
        else:
            return

        if not uid:
            reply_text(chat_id, "❌ 格式: 查 玩家UID\n例如: 查 1586971890000071")
            return

        from query import query_player
        result = query_player(uid)
        reply_text(chat_id, result)

    except Exception as e:
        logger.error(f"处理消息异常: {e}", exc_info=True)

def reply_text(chat_id: str, text: str):
    """回复文本消息"""
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
    event_handler = lark.EventDispatcherHandler.builder("", "") \
        .register_p2_im_message_receive_v1(on_message) \
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
