# -*- coding: utf-8 -*-
"""京东爬虫配置。"""

import os

# 项目根目录（本文件所在目录），用于把相对路径锚定到固定位置，
# 避免从不同目录运行时生成重复的 jd_user_data 嵌套目录。
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

URL = "https://search.jd.com/Search?keyword=%E5%AE%A0%E7%89%A9%E7%8E%A9%E5%85%B7&enc=utf-8&wq=%E5%AE%A0%E7%89%A9wan%27jv&pvid=a31833d4f6ba4a038b51e97e9aa91ab7"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
}

# Excel 输出路径：默认输出到项目根目录，可用环境变量 JD_OUTPUT_PATH 覆盖，
# 避免写死 D:\ 导致 Linux 服务器上无法运行。
OUTPUT_PATH = os.getenv("JD_OUTPUT_PATH", os.path.join(BASE_DIR, "jd_result.xlsx"))

MAX_PRODUCTS = 4
MAX_COMMENTS_PER_PRODUCT = 20
TIMEOUT = 15
SHORT_TIMEOUT = 5
# 页面已加载后，用 page.eles() 查找选择器是否匹配的超时。
# 设短一点，避免京东页面结构变化或出现风控/验证码时，多个选择器
# 逐个等待默认 10s 导致程序长时间“卡住”。
ELEMENT_TIMEOUT = 3
SCROLL_RETRIES = 5
MIN_COMMENT_LENGTH = 5

# ── 浏览器持久化 & 登录态 ──
USER_DATA_PATH = os.path.join(BASE_DIR, "jd_user_data")
SESSION_CHECK_URL = "https://order.jd.com/center/list.action"

# ── 无头模式（服务器部署时启用） ──
HEADLESS = False

# 京东搜索页于 2026-09 改版：商品卡片由 <li class="gl-item"> 改为带 data-sku 的
# <div>，字段的哈希类名（_text_xxx / _price_xxx 等）也全部变更。选择器按
# 「当前结构 → 语义前缀兜底 → 旧版兼容」排序，逐个尝试，匹配到即用。
CARD_SELECTORS = [
    "css:[data-sku]",                            # 当前卡片容器（div 带 data-sku）
    "css:[class*=\"plugin_goodsCardWrapper\"]",  # 当前卡片容器类名
    "css:li.gl-item",                            # 旧版
    "css:.gl-item",
    "css:[class*=\"_goods_item_\"]",
]

NAME_SELECTORS = [
    "css:[class*=\"_goods_title_container\"]",   # 当前标题容器
    "css:._newStyle_1k2fi_39",                   # 当前标题 span
    "css:._text_1x4i2_30",                       # 旧版
    "css:.p-name em",
    "css:.p-name a",
    "css:[class*=\"_text_\"]",
]

PRICE_SELECTORS = [
    "css:._price_9y3st_31",                      # 当前价格 span
    "css:._price_1tn4o_13",                      # 旧版
    "css:.p-price i",
    "css:.p-price",
    "css:[class*=\"_price_\"]",
]

PROMOTION_SELECTORS = [
    "css:[class*=\"_text-list\"]",               # 当前促销文案
    "css:._tags_hzhkm_2",                        # 促销标签（当前多为图标）
    "css:.p-icons",                              # 旧版
    "css:[class*=\"_tags_\"]",
]

STORE_SELECTORS = [
    "css:._name_3z0zc_15",                       # 当前店铺 span
    "css:._name_d19t5_35",                       # 旧版
    "css:.p-shop a",
    "css:.p-shop",
    "css:[class*=\"_name_\"]",
]

SALES_SELECTORS = [
    "css:._goods_volume_1d8up_1",                # 当前销量/好评 span
    "css:._goods_volume_1xkku_1",                # 旧版
    "css:.p-commit",
    "css:[class*=\"_goods_volume_\"]",
]

ALL_COMMENT_BUTTON_SELECTORS = [
    "css:.all-btn",
    "text:全部评价",
    "css:#comment",
]

# 销量排序按钮选择器（按文本优先，逐个尝试；全部失败则降级为默认排序继续跑）
SORT_SALES_SELECTORS = [
    "text:销量",
    "text:按销量",
    "text:销量排序",
    "text:销量优先",
]

COMMENT_TEXT_SELECTORS = [
    "css:.jdc-pc-rate-card-main-desc",
    "css:.comment-con",
    "css:[class*=\"rate-card-main-desc\"]",
]

INVALID_COMMENT = "此用户未填写评价内容"

# ── 限速配置（防止 IP 被封，随机化避免固定节奏被识别） ──
CRAWL_DELAY_MIN = 3.0       # 每个商品之间最小等待秒数
CRAWL_DELAY_MAX = 8.0       # 每个商品之间最大等待秒数
COMMENT_SCROLL_DELAY_MIN = 0.8   # 评论滚动加载最小等待秒数
COMMENT_SCROLL_DELAY_MAX = 2.0   # 评论滚动加载最大等待秒数
PAGE_LOAD_DELAY_MIN = 0.8   # 页面加载后额外最小等待秒数
PAGE_LOAD_DELAY_MAX = 1.5   # 页面加载后额外最大等待秒数
# 评论小步滚动参数（模拟人慢慢看，避免整页一步到底）
SCROLL_STEP_MIN = 1         # 每次小步滚动最小步数
SCROLL_STEP_MAX = 3         # 每次小步滚动最大步数
SCROLL_PIXEL_MIN = 200      # 每步滚动最小像素
SCROLL_PIXEL_MAX = 600      # 每步滚动最大像素
