# -*- coding: utf-8 -*-
"""通用工具函数。"""

import re
import sys


def configure_stdout():
    """支持编码设置时启用 UTF-8，兼容测试捕获和 Notebook 输出流。"""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")


def extract_text(ele):
    """尽量从元素中提取可见文字，兼容部分页面 .text 为空的情况。"""
    candidates = []
    for attr_name in ("text", "raw_text"):
        try:
            candidates.append(getattr(ele, attr_name, ""))
        except Exception:
            pass

    for attr_name in ("title", "aria-label"):
        try:
            candidates.append(ele.attr(attr_name))
        except Exception:
            pass

    try:
        candidates.append(ele.run_js('return this.innerText || this.textContent || "";'))
    except Exception:
        pass

    for text in candidates:
        text = (text or "").strip()
        if text:
            return text
    return ""


def normalize_url(link):
    """只保留京东商品详情页链接，避免误打开客服/店铺等入口。"""
    link = (link or "").strip()
    if not link:
        return ""
    if link.startswith("//"):
        link = "https:" + link
    elif link.startswith("/"):
        link = "https://item.jd.com" + link

    match = re.search(r"https?://item\.jd\.com/(\d+)\.html", link)
    if match:
        return f"https://item.jd.com/{match.group(1)}.html"
    return ""


def get_sku_from_link(link):
    """从京东商品详情链接中提取 SKU。"""
    match = re.search(r"item\.jd\.com/(\d+)\.html", link or "")
    return match.group(1) if match else ""


def normalize_column(values, target_length, fill_value=""):
    """把字段列表统一成相同长度，避免 DataFrame 创建失败。"""
    values = list(values)[:target_length]
    if len(values) < target_length:
        values.extend([fill_value] * (target_length - len(values)))
    return values


def sanitize_sheet_name(name, max_length=31):
    """清理 Excel 工作表名称。"""
    for char in r"[]:*?/\\":
        name = name.replace(char, "-")
    name = name.strip()[:max_length]
    return name or "Sheet"


def parse_sales_num(text):
    """从销量文案中解析销量数值，解析不出返回 0。

    支持常见京东销量格式：
    - "已售3万" / "已售3万+"          → 30000
    - "已售5000" / "已售5000+"        → 5000
    - "3万+" / "2万+条评价"           → 30000 / 20000
    - "5000+" / "5000+条评价"         → 5000
    """
    text = str(text or "")

    # 已售X万 / 已售X万+
    m = re.search(r"已售(\d+(?:\.\d+)?)万\+?", text)
    if m:
        return int(float(m.group(1)) * 10000)

    # 已售X / 已售X+
    m = re.search(r"已售(\d+)\+?", text)
    if m:
        return int(m.group(1))

    # X万+ / X万+条评价
    m = re.search(r"(\d+(?:\.\d+)?)万\+?", text)
    if m:
        return int(float(m.group(1)) * 10000)

    # X+ / X+条评价
    m = re.search(r"(\d+)\+", text)
    if m:
        return int(m.group(1))

    return 0


def parse_good_rate(text):
    """从销量/好评文案中解析好评率(%)，解析不出返回 0。

    京东的写法不固定，之前只认 "98%好评" 一种语序，"好评率98%" 会被丢成 0，
    而 0 会直接把"平均好评率"这类统计拉低。这里按「好评率X% → X%好评 →
    好评X%」的顺序逐个尝试，数字与"好评"之间允许少量标点/空格。

    小数按截断处理（99.5% → 99），不四舍五入，避免高估好评率。
    """
    text = str(text or "")
    for pattern in (
        r"好评率[：:\s]*(\d+(?:\.\d+)?)\s*%",       # 好评率98% / 好评率：98% / 好评率 98 %
        r"(\d+(?:\.\d+)?)\s*%[^\d]{0,4}好评",       # 98%好评 / 98% 的好评
        r"好评[：:\s]*(\d+(?:\.\d+)?)\s*%",         # 好评98%
    ):
        m = re.search(pattern, text)
        if m:
            return int(float(m.group(1)))
    return 0
