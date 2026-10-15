# -*- coding: utf-8 -*-
"""商品评论爬取。

优化版策略：复用同一个浏览器实例和一个商品工作标签页，避免每个商品重复启动浏览器。
"""

import random
import time

from DrissionPage.errors import PageDisconnectedError

from jd_config import (
    ALL_COMMENT_BUTTON_SELECTORS,
    COMMENT_SCROLL_DELAY_MAX,
    COMMENT_SCROLL_DELAY_MIN,
    COMMENT_TEXT_SELECTORS,
    CRAWL_DELAY_MAX,
    CRAWL_DELAY_MIN,
    INVALID_COMMENT,
    MAX_COMMENTS_PER_PRODUCT,
    MIN_COMMENT_LENGTH,
    PAGE_LOAD_DELAY_MAX,
    PAGE_LOAD_DELAY_MIN,
    SCROLL_PIXEL_MAX,
    SCROLL_PIXEL_MIN,
    SCROLL_RETRIES,
    SCROLL_STEP_MAX,
    SCROLL_STEP_MIN,
    SHORT_TIMEOUT,
)
from crawler.jd_utils import extract_text, get_sku_from_link


def clean_comments(comments):
    """过滤无效评论。"""
    cleaned = []
    for text in comments:
        stripped = text.strip()
        if stripped == INVALID_COMMENT:
            continue
        if len(stripped) < MIN_COMMENT_LENGTH:
            continue
        cleaned.append(stripped)
    return cleaned


def first_displayed(page, selectors, timeout=SHORT_TIMEOUT):
    """返回第一个显示出来的元素。"""
    for selector in selectors:
        try:
            if not page.wait.ele_displayed(selector, timeout=timeout):
                continue
            element = page.ele(selector)
            if element:
                return element
        except PageDisconnectedError:
            raise
        except Exception:
            pass
    return None


def visible_comment_selector(page):
    """返回当前页面可用的评论选择器。"""
    for selector in COMMENT_TEXT_SELECTORS:
        try:
            if page.wait.ele_displayed(selector, timeout=SHORT_TIMEOUT):
                return selector
        except PageDisconnectedError:
            raise
        except Exception:
            pass
    raise RuntimeError("未找到可用的评论内容选择器，请检查页面或更新选择器。")


def human_scroll(comments_page, last_ele):
    """小步多段滚动并随机停顿，模拟人慢慢浏览，避免固定节奏被识别。"""
    steps = random.randint(SCROLL_STEP_MIN, SCROLL_STEP_MAX)
    for _ in range(steps):
        comments_page.scroll.down(random.randint(SCROLL_PIXEL_MIN, SCROLL_PIXEL_MAX))
        time.sleep(random.uniform(0.2, 0.5))
    if last_ele:
        last_ele.scroll.to_see()
    time.sleep(random.uniform(COMMENT_SCROLL_DELAY_MIN, COMMENT_SCROLL_DELAY_MAX))


def open_comment_page(dp, product_tab, product_link):
    """打开评论页。优先点击页面按钮，失败时用 SKU 构造评论页地址。"""
    button = first_displayed(product_tab, ALL_COMMENT_BUTTON_SELECTORS)
    if button:
        before_tab_ids = set(dp.tab_ids)
        button.click()
        try:
            new_tab_id = dp.wait.new_tab(timeout=3, curr_tab=product_tab.tab_id, raise_err=False)
        except PageDisconnectedError:
            raise
        except Exception:
            new_tab_id = None

        if new_tab_id and new_tab_id not in before_tab_ids:
            return dp.get_tab(new_tab_id)
        return product_tab

    sku = get_sku_from_link(product_link)
    if not sku:
        raise RuntimeError("无法找到全部评价按钮，也无法从商品链接解析 SKU。")

    comment_url = f"https://club.jd.com/comment/sku/{sku}/page/1.html"
    print(f"[调试] 未找到全部评价按钮，改用评论页 URL: {comment_url}", flush=True)
    product_tab.get(comment_url)
    product_tab.wait.load_start()
    return product_tab


def collect_comments(comments_page):
    """按有效文本数量收集评论，文本去重后保留首次出现的页面顺序。"""
    if MAX_COMMENTS_PER_PRODUCT <= 0:
        return []

    selector = visible_comment_selector(comments_page)
    comments = []
    seen = set()
    retries = SCROLL_RETRIES

    while retries > 0:
        current_comments_eles = comments_page.eles(selector)
        previous_count = len(comments)
        for comment in current_comments_eles:
            # 先清洗再计数，空文本、短文本和默认评价不占有效评论配额。
            for text in clean_comments([extract_text(comment)]):
                if text not in seen:
                    seen.add(text)
                    comments.append(text)
                if len(comments) >= MAX_COMMENTS_PER_PRODUCT:
                    return comments

        if len(comments) > previous_count:
            retries = SCROLL_RETRIES
        else:
            retries -= 1

        if not current_comments_eles or retries == 0:
            break
        human_scroll(comments_page, current_comments_eles[-1])

    return comments


def crawl_product_comments(dp, product_tab, product):
    """复用商品工作标签页爬取单个商品评论。"""
    product_name = product["商品名称"]
    product_link = product.get("详情链接", "")

    if not product_link:
        print("[警告] 未提取到合法商品详情链接，跳过该商品，避免误打开客服/店铺页。", flush=True)
        return []

    try:
        print(f"[调试] 使用详情链接打开商品页: {product_link}", flush=True)
        product_tab.get(product_link)
        product_tab.wait.load_start()
        time.sleep(random.uniform(PAGE_LOAD_DELAY_MIN, PAGE_LOAD_DELAY_MAX))
        print("已进入商品详情页。", flush=True)

        comments_page = open_comment_page(dp, product_tab, product_link)
        comments_page.wait.load_start()
        time.sleep(random.uniform(PAGE_LOAD_DELAY_MIN, PAGE_LOAD_DELAY_MAX))
        comments = collect_comments(comments_page)
        print(f"成功采集 {len(comments)} 条评论到内存。", flush=True)

        delay = random.uniform(CRAWL_DELAY_MIN, CRAWL_DELAY_MAX)
        print(f"[限速] 等待 {delay:.1f} 秒后处理下一个商品...", flush=True)
        time.sleep(delay)
        return comments

    except PageDisconnectedError as e:
        # 断连是全局性故障，返回空列表会让主循环把剩余商品全部静默失败，
        # 最后还把空结果写入文件并显示"成功"。这里向上抛出，由主循环中止本轮。
        print(f"[严重错误] 与浏览器连接已断开: {e}", flush=True)
        raise
    except Exception as e:
        print(f"[未知错误] 处理 '{product_name}' 时发生错误: {e}", flush=True)
        return []


def print_crawl_summary(results):
    """打印本轮商品抓取成功/失败汇总。

    Args:
        results: [(商品名, 是否成功, 说明), ...]
    """
    print("\n" + "=" * 60, flush=True)
    print("  本轮商品抓取汇总", flush=True)
    print("=" * 60, flush=True)
    succeeded = 0
    failed = 0
    for name, ok, detail in results:
        if ok:
            succeeded += 1
            print(f"  [成功] {name[:30]} —— {detail}", flush=True)
        else:
            failed += 1
            print(f"  [失败] {name[:30]} —— {detail}", flush=True)
    print(f"  成功 {succeeded} 个，失败 {failed} 个，共 {len(results)} 个。", flush=True)
    print("=" * 60, flush=True)
