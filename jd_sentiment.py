# -*- coding: utf-8 -*-
"""中文评论情感分析（基于词典匹配）与停用词表。

把原本散落在 excel/generate_dashboard.py 等各入口里重复的词典统一到这里，
保证 Excel 看板、Notebook 与写入流程使用同一套规则，避免改一处漏一处。
"""

# ── 正面情感词 ──
POSITIVE_WORDS = {
    "好", "棒", "满意", "喜欢", "推荐", "不错", "赞", "超赞", "完美", "优秀",
    "给力", "好评", "耐用", "结实", "厚实", "稳固", "方便", "舒服", "舒适",
    "安全", "开心", "迅速", "很快", "靠谱", "信赖", "回购", "划算", "超值",
    "惊喜", "漂亮", "可爱", "精细", "放心", "贴心", "爱不释手", "一流",
    "高品质", "省心", "物美价廉", "性价比高", "值得", "必备", "神器",
    "不占地", "良心", "到位", "周到", "及时", "好看", "整洁", "干净",
    "温和", "柔软", "有弹性", "尽情", "挺好", "非常好", "很棒", "便宜",
    "物超所值", "棒棒哒", "不贵",
}

# ── 负面情感词 ──
NEGATIVE_WORDS = {
    "差", "不好", "失望", "垃圾", "坑", "差劲", "烂", "糟糕", "坏",
    "异味", "气味", "味道大", "臭", "难闻", "刺鼻",
    "掉屑", "飞渣", "掉渣", "坏了", "破损", "损坏", "烂了",
    "不值", "贵", "稍贵", "不推荐", "后悔", "退", "换货",
    "问题", "缺陷", "缺点", "瑕疵", "不足", "有点大", "太小",
    "不喜欢", "不爱", "没兴趣", "不玩", "不怎么样",
    "差评", "不好用", "不耐用", "容易坏", "很快坏", "质量差",
    "闹心", "糟心", "差很多",
}

# ── 停用词（关键词提取时过滤） ──
STOPWORDS = {
    "的", "了", "是", "我", "很", "也", "都", "不", "就", "和", "还", "一个",
    "这个", "已经", "可以", "没有", "比较", "觉得", "知道", "因为", "所以",
    "但是", "如果", "虽然", "而且", "或者", "不过", "然后", "之后", "还是",
    "非常", "真的", "挺", "有点", "蛮", "太", "比较", "特别", "会", "要",
    "在", "有", "买", "用", "给", "让", "把", "被", "对", "从", "到",
    "出", "过", "着", "之", "中", "上", "下", "大", "小", "多", "少",
    "好", "等", "该", "这", "那", "其", "它", "他", "她", "们",
    "款式", "型号", "颜色", "规格", "京东", "物流", "快递", "配送",
    "包装", "客服", "售后", "购物", "宝贝", "卖家", "店铺", "东西",
    "收到", "打开", "拿到", "送来", "到货", "下单", "购买", "发货",
}


# ── 否定词：命中情感词后回看前 N 个字符，若含否定词则翻转极性 ──
NEGATION_WORDS = {"不", "没", "无", "别", "非", "莫", "未", "否"}
# 否定词与情感词之间的最大距离（字符数）。京东评论里"没什么异味""没有什么问题"
# 这类否定前置很常见，否定词距情感词 3~4 字，窗口设 4 才能覆盖。
NEGATION_WINDOW = 4
# 否定范围不跨标点或已匹配的情感词。此规则仍不处理双重否定和复杂从句。
_CLAUSE_BOUNDARIES = set("，。！？；：、,.!?;:\n\r")

# 情感词按长度降序排列，贪心最长匹配，避免 "不好" 里的 "好" 被重复计数
_SENTIMENT_WORDS = sorted(
    [(w, 1) for w in POSITIVE_WORDS] + [(w, -1) for w in NEGATIVE_WORDS],
    key=lambda item: len(item[0]),
    reverse=True,
)


def count_sentiment(text):
    """统计正/负面情感词命中数（含否定窗口翻转），返回 (pos, neg)。

    逐字符贪心最长匹配情感词：命中后回看前 NEGATION_WINDOW（4）个字符，
    窗口不跨标点或已匹配的情感词，排除“非常”中的“非”；
    若其余前缀出现否定词（不/没/无/别/非/莫/未/否）则翻转极性。例如：
    - "不满意"：命中"满意"（正），前有"不" → 翻转为负；
    - "没有问题"：命中"问题"（负），前有"没有" → 翻转为正；
    - "没有什么问题"：命中"问题"（负），前有"没有什么" → 翻转为正；
    - "不太好"：命中"好"（正），前有"不太" → 翻转为负；
    - "不太贵"：命中"贵"（负），前有"不太" → 翻转为正。
    说明：仅做单次翻转，不处理"不无满意"这类双重否定；"不得不承认好用"
    这类含双否定成语的句子可能被误翻转（见 tests/test_sentiment.py 的已知局限）。
    """
    pos = 0
    neg = 0
    i = 0
    negation_start = 0
    n = len(text)
    while i < n:
        if text[i] in _CLAUSE_BOUNDARIES:
            negation_start = i + 1
            i += 1
            continue
        polarity = None
        matched_len = 0
        for word, word_polarity in _SENTIMENT_WORDS:
            if text.startswith(word, i):
                polarity = word_polarity
                matched_len = len(word)
                break
        if polarity is None:
            i += 1
            continue

        prefix = text[max(negation_start, i - NEGATION_WINDOW):i]
        # “非常”是程度副词，其中的“非”不表达否定；保留前面的真实否定词。
        prefix = prefix.replace("非常", "")
        if any(negator in prefix for negator in NEGATION_WORDS):
            polarity = -polarity

        if polarity > 0:
            pos += 1
        else:
            neg += 1
        i += matched_len
        negation_start = i
    return pos, neg


def classify_sentiment(pos, neg):
    """根据正负面词命中数返回情感标签。"""
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def analyze_sentiment(text):
    """对单条评论文本做情感分析，返回 (label, pos, neg)。"""
    pos, neg = count_sentiment(text)
    return classify_sentiment(pos, neg), pos, neg
