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
TABLE_A5 = "tblIZrPDKckN53VQ"  # 战斗数据

def get_token():
    """获取tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET})
    return resp.json().get("tenant_access_token")

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
        
        # 提取基础信息
        name = player.get("玩家名称", "未知")
        server = player.get("所属服务器", "未知")
        segment = player.get("区段名称", "未知")
        power = player.get("玩家战力", "未知")
        total_pay = player.get("总付费", "未知")
        pay_7d = player.get("最近7天付费", 0)
        pay_30d = player.get("最近30天付费", 0)
        alliance = player.get("当前联盟名称", "无")
        role = player.get("联盟职级", "未知")
        last_login = player.get("最后登录时间", "未知")
        power_rank = player.get("区段内战力排名", "未知")
        pay_rank = player.get("区段内付费排名", "未知")
        
        # AI分析字段
        personality = player.get("性格标签", "暂无")
        social_role = player.get("社交角色", "暂无")
        friends = player.get("好友列表", "暂无")
        conflicts = player.get("冲突对象", "暂无")
        emotion = player.get("情感关系", "暂无")
        pain_points = player.get("高频痛点", "暂无")
        risk = player.get("流失风险", "暂无")
        ai_summary = player.get("AI分析摘要", "暂无")
        
        # 2. 查B4服务器生态
        server_info = ""
        if server != "未知":
            b4_records = search_records(TABLE_B4, "所属服务器", server, token)
            if b4_records:
                s = b4_records[0]
                president = s.get("当前总统名称", "未知")
                president_alliance = s.get("总统所在联盟名称", "未知")
                top1 = s.get("服内TOP1联盟名称", "未知")
                top2 = s.get("服内TOP2联盟名称", "未知")
                top3 = s.get("服内TOP3联盟名称", "未知")
                pattern = s.get("权力格局", "未知")
                
                server_info = (
                    f"\n━━━ 服务器生态（{server}服）━━━\n"
                    f"🏛️ 权力格局: {pattern}\n"
                    f"👑 总统: {president}（{president_alliance}）\n"
                    f"🥇 TOP1: {top1}\n"
                    f"🥈 TOP2: {top2}\n"
                    f"🥉 TOP3: {top3}"
                )
        
        # 3. 查B5社交关系
        social_info = ""
        b5_records = search_records(TABLE_B5, "玩家A_UID（聊天的人）", uid, token)
        if b5_records:
            allies = []
            enemies = []
            for r in b5_records:
                rel_type = r.get("关系类型", "")
                b_name = r.get("玩家B名称", "未知")
                desc = r.get("关系描述", "")
                if "盟友" in str(rel_type) or "友" in str(rel_type):
                    allies.append(f"{b_name}")
                elif "敌" in str(rel_type) or "冲突" in str(rel_type):
                    enemies.append(f"{b_name}")
            
            if allies or enemies:
                social_info = "\n━━━ 社交关系 ━━━"
                if allies:
                    social_info += f"\n🤝 盟友: {', '.join(allies[:5])}"
                if enemies:
                    social_info += f"\n⚔️ 敌对: {', '.join(enemies[:5])}"
        
        # 4. 格式化战力/付费
        if isinstance(power, (int, float)):
            if power >= 100000000:
                power_str = f"{power/100000000:.1f}亿"
            elif power >= 10000:
                power_str = f"{power/10000:.0f}万"
            else:
                power_str = str(power)
        else:
            power_str = str(power)
        
        if isinstance(total_pay, (int, float)):
            pay_str = f"${total_pay:,.0f}"
        else:
            pay_str = str(total_pay)
        
        # 5. 拼装卡片
        result = (
            f"━━━ 玩家档案 ━━━\n"
            f"👤 {name} | {server}服 | {segment}\n"
            f"⚔️ 战力: {power_str} | 区段排名: #{power_rank}\n"
            f"💰 总付费: {pay_str} | 区段排名: #{pay_rank}\n"
            f"📅 7天付费: ${pay_7d} | 30天: ${pay_30d}\n"
            f"🏰 联盟: {alliance} | 职级: {role}\n"
            f"🕐 最后登录: {last_login}\n"
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
        logger.error(f"查询异常: {e}")
        return f"❌ 查询出错: {str(e)}"