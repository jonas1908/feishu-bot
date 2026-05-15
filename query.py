import os
import requests
import logging

logger = logging.getLogger(__name__)

APP_ID = os.environ.get("FEISHU_APP_ID")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
APP_TOKEN = "SjrMwZtXuiDQFWk0mbLcyLfDn9e"

# 表ID
TABLE_B3 = "tbl1ymVjgIFS59eQ"  # 玩家档案
TABLE_B4 = "tbldAoG04gMBCi3P"  # 服务器生态
TABLE_B5 = "tblhrDWSXYtsahjt"  # 社交关系

def get_token():
    """获取tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET})
    return resp.json().get("tenant_access_token")

def extract_text(value):
    """从飞书字段值中提取纯文本"""
    if value is None:
        return "暂无"
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return value  # 数字保留原样
    if isinstance(value, list):
        # 富文本格式: [{'text': 'xxx', 'type': 'text'}, ...]
        texts = []
        for item in value:
            if isinstance(item, dict):
                t = item.get("text", "")
                if t:
                    texts.append(t)
            elif isinstance(item, str):
                texts.append(item)
        return "、".join(texts) if texts else "暂无"
    if isinstance(value, dict):
        # 可能是人员字段等
        return value.get("text", value.get("name", str(value)))
    return str(value)

def search_records(table_id, field_name, value, token):
    """搜索记录"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records/search"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    body = {
        "filter": {
            "conjunction": "and",
            "conditions": [
                {
                    "field_name": field_name,
                    "operator": "is",
                    "value": [str(value)]
                }
            ]
        },
        "page_size": 20
    }

    resp = requests.post(url, headers=headers, json=body)
    data = resp.json()

    if data.get("code") != 0:
        logger.error(f"搜索失败: {data}")
        return []

    items = data.get("data", {}).get("items", [])
    return [item.get("fields", {}) for item in items]

def query_player(uid: str) -> str:
    """查询玩家完整档案"""
    try:
        token = get_token()

        # 1. 查B3玩家档案
        b3_records = search_records(TABLE_B3, "玩家UID", uid, token)

        if not b3_records:
            return f"❌ 未找到UID: {uid}\n请确认UID是否正确"

        player = b3_records[0]

        # 提取基础信息（全部用extract_text处理）
        name = extract_text(player.get("玩家名称"))
        server = extract_text(player.get("所属服务器"))
        segment = extract_text(player.get("区段名称"))
        power = player.get("玩家战力", 0)
        total_pay = player.get("总付费", 0)
        pay_7d = player.get("最近7天付费", 0)
        pay_30d = player.get("最近30天付费", 0)
        alliance = extract_text(player.get("当前联盟名称"))
        role = extract_text(player.get("联盟职级"))
        last_login = player.get("最后登录时间", "未知")
        power_rank = extract_text(player.get("区段内战力排名"))
        pay_rank = extract_text(player.get("区段内付费排名"))

        # AI分析字段
        personality = extract_text(player.get("性格标签"))
        social_role = extract_text(player.get("社交角色"))
        pain_points = extract_text(player.get("高频痛点"))
        risk = extract_text(player.get("流失风险"))
        ai_summary = extract_text(player.get("AI分析摘要"))

        # 2. 查B4服务器生态
        server_info = ""
        if server and server != "暂无" and server != "未知":
            b4_records = search_records(TABLE_B4, "所属服务器", server, token)
            if b4_records:
                s = b4_records[0]
                president = extract_text(s.get("当前总统名称"))
                president_alliance = extract_text(s.get("总统所在联盟名称"))
                top1 = extract_text(s.get("服内TOP1联盟名称"))
                top2 = extract_text(s.get("服内TOP2联盟名称"))
                top3 = extract_text(s.get("服内TOP3联盟名称"))
                pattern = extract_text(s.get("权力格局"))
                ecology = extract_text(s.get("生态分析"))

                server_info = (
                    f"\n\n━━━ 服务器生态（{server}服）━━━\n"
                    f"🏛️ 权力格局: {pattern}\n"
                    f"👑 总统: {president}（{president_alliance}）\n"
                    f"🥇 TOP1: {top1}\n"
                    f"🥈 TOP2: {top2}\n"
                    f"🥉 TOP3: {top3}\n"
                    f"🌍 生态: {ecology}"
                )

        # 3. 查B5社交关系
        social_info = ""
        b5_records = search_records(TABLE_B5, "玩家A_UID（聊天的人）", uid, token)
        if b5_records:
            allies = []
            enemies = []
            for r in b5_records:
                rel_type = extract_text(r.get("关系类型"))
                b_name = extract_text(r.get("玩家B名称"))
                if "盟友" in rel_type or "友" in rel_type:
                    allies.append(b_name)
                elif "敌" in rel_type or "冲突" in rel_type:
                    enemies.append(b_name)

            if allies or enemies:
                social_info = "\n\n━━━ 社交关系 ━━━"
                if allies:
                    social_info += f"\n🤝 盟友: {', '.join(allies[:5])}"
                if enemies:
                    social_info += f"\n⚔️ 敌对: {', '.join(enemies[:5])}"

        # 4. 格式化战力
        if isinstance(power, (int, float)):
            if power >= 100000000:
                power_str = f"{power/100000000:.1f}亿"
            elif power >= 10000:
                power_str = f"{power/10000:.0f}万"
            else:
                power_str = str(int(power))
        else:
            power_str = extract_text(power)

        # 格式化付费
        if isinstance(total_pay, (int, float)):
            pay_str = f"${total_pay:,.0f}"
        else:
            pay_str = extract_text(total_pay)

        if isinstance(pay_7d, (int, float)):
            pay_7d_str = f"${pay_7d:,.2f}"
        else:
            pay_7d_str = extract_text(pay_7d)

        if isinstance(pay_30d, (int, float)):
            pay_30d_str = f"${pay_30d:,.2f}"
        else:
            pay_30d_str = extract_text(pay_30d)

        # 5. 格式化登录时间
        if isinstance(last_login, (int, float)):
            import datetime
            try:
                ts = last_login / 1000 if last_login > 9999999999 else last_login
                login_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
            except:
                login_str = str(last_login)
        else:
            login_str = extract_text(last_login)

        # 6. 拼装卡片
        result = (
            f"━━━ 玩家档案 ━━━\n"
            f"👤 {name} | {server}服 | {segment}\n"
            f"⚔️ 战力: {power_str} | 区段排名: #{power_rank}\n"
            f"💰 总付费: {pay_str} | 区段排名: #{pay_rank}\n"
            f"📅 7天付费: {pay_7d_str} | 30天: {pay_30d_str}\n"
            f"🏰 联盟: {alliance} | 职级: {role}\n"
            f"🕐 最后登录: {login_str}\n"
            f"\n━━━ AI画像 ━━━\n"
            f"🧠 性格: {personality}\n"
            f"👥 社交角色: {social_role}\n"
            f"💔 痛点: {pain_points}\n"
            f"⚠️ 流失风险: {risk}\n"
            f"📝 摘要: {ai_summary}"
            f"{social_info}"
            f"{server_info}"
        )

        return result

    except Exception as e:
        logger.error(f"查询异常: {e}", exc_info=True)
        return f"❌ 查询出错: {str(e)}"
