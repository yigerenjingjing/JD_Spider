# -*- coding: utf-8 -*-
"""浏览器初始化、登录态持久化、页面导航。"""

import sys
import time

from DrissionPage import Chromium, ChromiumOptions

import jd_config

# 登录态检测的请求重试次数：网络抖动/超时不应被误判成"未登录"
LOGIN_PROBE_RETRIES = 3


def _create_options():
    co = ChromiumOptions()
    co.set_user_data_path(jd_config.USER_DATA_PATH)

    # 隐藏自动化特征，降低被风控识别的概率
    co.set_argument("--disable-blink-features=AutomationControlled")

    if jd_config.HEADLESS:
        co.set_argument("--headless=new")
        co.set_argument("--no-sandbox")
        co.set_argument("--disable-gpu")
        co.set_argument("--disable-dev-shm-usage")

    return co


def _probe_login_state(tab):
    """访问需登录的订单页探测登录态。

    返回 "logged_in" / "need_login" / "unknown" 三种状态。

    之前把任何异常都当成"未登录"，于是超时、DNS 失败这类网络问题也会走到
    扫码分支并阻塞在 input()，无人值守时更会直接退出。这里把「确实被重定向
    到登录页」和「请求本身失败」分开：前者是 need_login，后者重试若干次
    仍失败则返回 unknown，由调用方明确报错。
    """
    print("[系统] 正在检测京东登录态...", flush=True)
    last_error = None
    for attempt in range(1, LOGIN_PROBE_RETRIES + 1):
        try:
            tab.get(jd_config.SESSION_CHECK_URL)
            tab.wait.load_start()
            current_url = (tab.url or "").lower()
        except Exception as e:
            last_error = e
            if attempt < LOGIN_PROBE_RETRIES:
                time.sleep(attempt)
            continue

        if "login" in current_url or "passport" in current_url:
            return "need_login"
        return "logged_in"

    print(
        f"[警告] 登录态检测请求连续 {LOGIN_PROBE_RETRIES} 次失败：{last_error}",
        flush=True,
    )
    return "unknown"


def _can_prompt_interactively():
    """当前是否有可交互的终端（服务器/重定向/无 stdin 时不能阻塞 input()）。"""
    stdin = getattr(sys, "stdin", None)
    return bool(stdin) and bool(getattr(stdin, "isatty", lambda: False)())


def _ensure_login(tab):
    """确保已登录。若未登录，提示扫码并阻塞等待人工操作。"""
    state = _probe_login_state(tab)

    if state == "logged_in":
        print("[系统] 已恢复京东登录状态，无需重复登录。", flush=True)
        return

    if state == "unknown":
        raise RuntimeError(
            "无法确认京东登录态：检测请求连续失败（通常是网络不通、超时或被拦截），"
            "请检查网络后重试。为避免误判为'未登录'，本轮不进入扫码流程。"
        )

    print("", flush=True)
    print("=" * 60, flush=True)
    print("  [警告] 京东登录态已过期或首次使用，需要扫码登录。", flush=True)
    print("  请在浏览器中完成登录后，回到终端按回车继续...", flush=True)
    print("=" * 60, flush=True)

    # 打开京东首页供扫码
    tab.get("https://www.jd.com/")
    tab.wait.load_start()

    if not _can_prompt_interactively():
        # 非交互环境（cron / 重定向 / 无 stdin）下 input() 会立刻 EOFError，
        # 之前会 sys.exit(0) 静默"成功退出"，任务消失得无影无踪。
        raise RuntimeError(
            "当前不是可交互终端，无法等待人工扫码登录。请先在本地登录并把 "
            "jd_user_data/ 上传到项目根目录，或改用可交互的终端运行。"
        )

    try:
        input()
    except (EOFError, KeyboardInterrupt):
        print("\n[系统] 用户取消，程序退出。", flush=True)
        sys.exit(1)

    if _probe_login_state(tab) == "logged_in":
        print("[系统] 登录成功！后续运行将自动恢复登录态。", flush=True)
    else:
        print("[警告] 仍未检测到登录态，继续尝试运行（可能部分功能不可用）。", flush=True)


def _click_sales_sort(tab):
    """点击销量排序；逐个尝试选择器，全部失败则降级为默认排序继续。

    其它定位（商品卡片、名称、价格等）都有 fallback 列表，唯独销量排序
    之前是单选择器直接 click，页面稍一改版整个入口就崩，这里补齐兜底。
    """
    for selector in jd_config.SORT_SALES_SELECTORS:
        try:
            tab.wait.ele_displayed(selector, timeout=jd_config.SHORT_TIMEOUT)
            ele = tab.ele(selector)
            if ele:
                ele.click()
                print(f"[系统] 已点击销量排序（选择器: {selector}）。", flush=True)
                return True
        except Exception:
            continue
    print("[警告] 未找到销量排序按钮，已降级为默认排序继续。", flush=True)
    return False


def initialize_list_browser():
    """初始化浏览器、检测/恢复登录态、打开搜索列表页并点击销量排序。"""
    print("\n[系统] 正在初始化浏览器...", flush=True)
    dp = Chromium(_create_options())
    tab = dp.new_tab()

    _ensure_login(tab)

    print("[系统] 正在打开搜索列表页...", flush=True)
    tab.get(jd_config.URL)
    tab.wait.load_start()

    print("[系统] 正在等待并点击销量排序...", flush=True)
    _click_sales_sort(tab)
    tab.wait.ele_displayed(jd_config.NAME_SELECTORS[0], timeout=jd_config.TIMEOUT)

    print("[系统] 浏览器初始化完成，已进入商品列表页。", flush=True)
    return dp, tab


def create_product_tab(dp):
    """创建可复用的商品工作标签页。"""
    return dp.new_tab()
