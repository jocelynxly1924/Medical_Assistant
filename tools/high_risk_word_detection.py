# 高危词识别
# 改进：大模型辅助识别：负责识别由于表述问题被漏掉的高危情况

from langchain_core.tools import tool

LEVEL_1_CRITICAL = {
    # 窒息/气道梗阻
    "窒息": {
        "keywords": ["窒息", "掐脖子", "透不过气", "憋死了", "气道堵塞"],
        "action": "立即转人工+建议急救",
        "reason": "可能急性气道梗阻"
    },

    # 严重呼吸困难
    "重度呼吸困难": {
        "keywords": [
            "呼吸困难", "喘不上气", "气不够用", "无法呼吸",
            "呼吸停止", "呼吸衰竭", "濒死感", "吸不进氧气"
        ],
        "action": "立即转人工",
        "reason": "急性呼吸窘迫"
    },

    # 意识改变（缺氧表现）
    "缺氧意识改变": {
        "keywords": [
            "昏迷", "意识模糊", "叫不醒", "昏过去了",
            "晕倒", "不省人事", "失去知觉"
        ],
        "action": "立即转人工+建议120",
        "reason": "严重缺氧导致意识障碍"
    },

    # 大咯血
    "咯血": {
        "keywords": [
            "咳血", "吐血", "咯血", "血块", "鲜血",
            "一口血", "痰中带血块", "出血不止"
        ],
        "action": "立即转人工",
        "reason": "可能大咯血窒息"
    }
}

LEVEL_2_URGENT = {
    # 急性哮喘
    "哮喘急性发作": {
        "keywords": [
            "哮喘发作", "喘鸣", "哮鸣音", "吱吱响",
            "憋喘", "喘不过气", "吸不进药"
        ],
        "action": "立即转人工",
        "reason": "哮喘急性发作"
    },

    # 胸部剧痛（警惕气胸/心梗）
    "急性胸痛": {
        "keywords": [
            "胸痛剧烈", "胸口撕裂痛", "刺痛", "压榨感",
            "胸闷痛", "胸骨后痛", "深呼吸痛"
        ],
        "action": "立即转人工",
        "reason": "可能气胸/胸膜炎/心梗"
    },

    # 发绀（缺氧体征）
    "发绀": {
        "keywords": [
            "嘴唇发紫", "指甲发紫", "脸色发紫",
            "口唇青紫", "紫绀", "缺氧发紫"
        ],
        "action": "立即转人工",
        "reason": "明显缺氧表现"
    },

    # 急性喉炎/喉头水肿
    "喉头水肿": {
        "keywords": [
            "喉咙堵", "喉头水肿", "嗓子肿说不出话",
            "喉咙像被掐住", "吞不下口水"
        ],
        "action": "立即转人工",
        "reason": "可能急性喉梗阻"
    }
}

LEVEL_3_WARNING = {
    # 重症肺炎表现
    "重症肺炎": {
        "keywords": [
            "高烧不退", "呼吸困难加重", "咳脓痰",
            "胸痛伴发热", "呼吸急促", "神志改变"
        ],
        "action": "建议转人工",
        "reason": "可能重症肺炎"
    },

    # 肺栓塞可能
    "肺栓塞": {
        "keywords": [
            "突发呼吸困难", "胸痛伴咯血", "单侧腿肿后气喘",
            "术后气喘", "长期卧床后气喘"
        ],
        "action": "建议转人工",
        "reason": "警惕肺栓塞"
    },

    # 气胸
    "气胸": {
        "keywords": [
            "突发胸痛", "单侧胸痛", "左侧胸痛", "右侧胸痛""呼吸时胸痛加重",
            "年轻瘦高个胸痛", "咳嗽后胸痛"
        ],
        "action": "建议转人工",
        "reason": "可能自发性气胸"
    }
}

def high_risk_word_detection(question):
    for symptom, info in LEVEL_1_CRITICAL.items():
        for keyword in info["keywords"]:
            if keyword in question:
                return "⚠️Level1", {
                    "condition": symptom,
                    "info": info
                }
    for symptom, info in LEVEL_2_URGENT.items():
        for keyword in info["keywords"]:
            if keyword in question:
                return "⚠️Level2", {
                    "condition": symptom,
                    "info": info
                }
    for symptom, info in LEVEL_3_WARNING.items():
        for keyword in info["keywords"]:
            if keyword in question:
                return "⚠️Level3", {
                    "condition": symptom,
                    "info": info
                }
    return "✅Normal", None


def input_detection(intent, input_text):
    if intent in ['疾病科普','药品信息']:
        return False
    else:
        result, info = high_risk_word_detection(input_text)
        if result == "✅Normal":
            return False
        else:
            return True

if __name__ == '__main__':
    print(high_risk_word_detection("我有点透不过气"))
    print(high_risk_word_detection("我胸闷"))
    print(high_risk_word_detection("我呼吸急促"))
    print(high_risk_word_detection("我有点咳嗽"))
    print(high_risk_word_detection("我发高烧"))
    print(high_risk_word_detection("我咳血"))
