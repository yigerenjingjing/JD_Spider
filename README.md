# 京东商品数据爬虫

基于 Python + DrissionPage 的京东商品数据采集项目。当前默认搜索关键词为“宠物玩具”，支持抓取京东搜索结果页的商品信息和商品评论，输出为 Excel，并提供基于 ECharts 的 HTML 数据看板。

> 本项目仅供学习与数据分析练习使用。请合理控制访问频率，并遵守目标网站规则。

## 功能概览

- 自动打开京东搜索结果页，并点击“销量”排序。
- 首次扫码登录后保存浏览器用户数据，后续运行自动复用登录态。
- 启动时检测登录态，失效时提示重新扫码。
- 支持服务器无头模式运行。
- 抓取商品名称、价格、活动、店铺名称、销量和详情页链接。
- 从商品详情页进入评论区，按配置数量采集评论。
- 自动过滤空评论、“此用户未填写评价内容”等无效评论。
- 输出 Excel：`商品总览` 工作表 + 按商品拆分的评论工作表。
- 可生成商品价格、销量、好评率、评论情感、关键词和评论长度等可视化看板。

## 项目结构

```text
JD_Spider/
├── README.md                       # 项目说明
├── requirements.txt                # 运行依赖
├── requirements-dev.txt            # 开发/测试依赖（pytest）
├── jd_config.py                    # 全局配置
├── jd_sentiment.py                 # 情感词典与判定（公共模块）
├── dashboard_common.py             # 看板公共工具（HTML 转义 / 安全 JSON / 统计结论文案）
├── analysis_notebook.ipynb         # 分析流程 Notebook（jieba/TF-IDF/统计检验）
├── crawler/                        # 爬虫核心模块
│   ├── __init__.py
│   ├── jd_browser.py               # 浏览器初始化、登录态检测、页面导航
│   ├── jd_product_extractor.py     # 搜索结果页商品信息提取
│   ├── jd_comment_crawler.py       # 商品详情页评论采集
│   └── jd_utils.py                 # URL、文本、SKU、工作表名、销量/好评率解析
├── excel/                          # 存储与看板
│   ├── __init__.py
│   ├── jd_main.py                  # 固定关键词入口
│   ├── jd_search.py                # 交互式关键词入口
│   ├── jd_excel_writer.py          # Excel 写入
│   ├── generate_dashboard.py       # 生成看板（默认输出 excel/dashboard.html）
│   └── dashboard.html              # 看板效果预览（由上面的脚本生成）
├── dashboard_mysql.html            # MySQL 版看板效果预览（生成脚本未包含在本仓库）
├── tests/                          # 单元测试（pytest，不依赖浏览器/数据库）
│   ├── test_comment_crawler.py     # 模拟页面：选择器回退、有效数量、有序去重与断连传播
│   ├── test_dashboard_calculations.py # 看板统计精度、评论均长与 Excel 资源关闭
│   ├── test_dashboard_common.py    # 看板转义与统计结论文案
│   ├── test_excel_writer.py        # Excel 写入
│   ├── test_jd_utils.py            # 销量/好评率解析、链接与工作表名处理
│   └── test_sentiment.py           # 情感分析（含否定窗口翻转）
├── .github/workflows/tests.yml     # CI：push / PR 时跑 pytest
└── 样例图片/
    ├── 商品总览.png
    └── 商品评论.png
```

运行后还会生成 `jd_user_data/` 浏览器用户数据目录、`jd_result.xlsx` 结果文件和 Python 的 `__pycache__/` 缓存目录，这些都属于运行产物，已在 `.gitignore` 中忽略。

## 环境要求

- Python 3.10 或更高版本。
- 本地需要安装 Chrome 或 Chromium。

安装依赖（推荐直接使用 `requirements.txt`）：

```bash
pip install -r requirements.txt
```

也可以手动安装：

```bash
pip install DrissionPage pandas openpyxl jieba numpy scipy matplotlib wordcloud
```

| 依赖 | 用途 |
| --- | --- |
| DrissionPage | 浏览器自动化、页面元素定位和操作 |
| pandas | 数据处理、Excel 读取 |
| openpyxl | Excel 写入引擎 |
| jieba | 中文分词、TF-IDF 关键词提取 |
| numpy / scipy | 数值计算与统计检验（Pearson 相关、t 检验） |
| matplotlib / wordcloud | Notebook 中的图表与词云 |

> 仅跑爬虫 + Excel 写入时，`jieba`、`numpy`、`scipy`、`matplotlib`、`wordcloud` 不是必需的；生成看板或运行 `analysis_notebook.ipynb` 时才需要。

跑单元测试需要额外的开发依赖（`pytest`）：

```bash
pip install -r requirements-dev.txt
pytest tests/
```

`tests/` 覆盖纯函数、Excel 往返和使用模拟页面的评论采集逻辑。CI 安装 DrissionPage 以导入被测模块，但不启动浏览器、不访问京东。

## 配置说明

主要配置集中在 `jd_config.py`：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `URL` | 京东“宠物玩具”搜索结果页 | 固定关键词入口使用的搜索 URL |
| `OUTPUT_PATH` | `项目根目录/jd_result.xlsx` | Excel 输出路径（可用环境变量 `JD_OUTPUT_PATH` 覆盖，兼容 Linux 服务器） |
| `MAX_PRODUCTS` | `4` | 每次抓取的商品数量 |
| `MAX_COMMENTS_PER_PRODUCT` | `20` | 每个商品最多抓取的评论数 |
| `MIN_COMMENT_LENGTH` | `5` | 评论最小有效长度 |
| `TIMEOUT` | `15` | 常规等待超时时间，单位秒 |
| `SHORT_TIMEOUT` | `5` | 短等待超时时间，单位秒 |
| `ELEMENT_TIMEOUT` | `3` | 页面加载后查找元素是否匹配的超时，设短可避免风控/页面结构变化时长时间卡住 |
| `SCROLL_RETRIES` | `5` | 评论滚动加载重试次数 |
| `CRAWL_DELAY_MIN` / `CRAWL_DELAY_MAX` | `3` / `8` | 每个商品之间随机等待秒数范围（限速） |
| `COMMENT_SCROLL_DELAY_MIN` / `COMMENT_SCROLL_DELAY_MAX` | `0.8` / `2` | 评论滚动加载随机等待秒数范围 |
| `PAGE_LOAD_DELAY_MIN` / `PAGE_LOAD_DELAY_MAX` | `0.8` / `1.5` | 页面加载后随机等待秒数范围 |
| `USER_DATA_PATH` | `项目根目录/jd_user_data` | 浏览器登录态保存目录（已锚定到项目根目录） |
| `HEADLESS` | `False` | 是否启用无头浏览器（保持 `False` 更不容易被风控识别） |

京东页面结构变化时，优先检查 `jd_config.py` 中的 `*_SELECTORS` 选择器列表。代码会按列表顺序尝试，匹配到可用元素后继续执行。

## 限速与反爬

本项目定位为学习与数据分析，反爬只做「克制 + 拟人」层面，不追求绕过风控：

- **随机延迟**：商品间、评论滚动、页面加载都使用随机等待区间，避免固定节奏。
- **拟人滚动**：评论加载采用小步多段滚动 + 随机停顿，而非整页一步到底。
- **隐藏自动化特征**：浏览器启动时加 `--disable-blink-features=AutomationControlled`，并保持真实浏览器窗口（`HEADLESS = False`）与持久登录态。
- **控制频率**：单次量小（`MAX_PRODUCTS`×`MAX_COMMENTS_PER_PRODUCT`），并建议同一关键词一天最多跑 1–2 次，两次之间间隔数小时。

仍请注意：任何大规模、高频、刻意绕过风控的行为都不可取，且迟早会被识别。

## 快速开始

所有命令建议在项目根目录执行：

```bash
cd /path/to/JD_Spider
```

### 首次登录

首次运行爬虫时，程序会打开浏览器并检测京东登录态。如果未登录，会提示在浏览器中扫码登录。

```bash
python excel/jd_main.py
```

扫码完成后回到终端按回车。登录成功后，Cookie 和 Session 会保存在 `jd_user_data/`，后续运行会自动复用。

### 采集数据

固定使用 `jd_config.py` 中的默认搜索 URL：

```bash
python excel/jd_main.py
```

交互式输入搜索关键词：

```bash
python excel/jd_search.py
```

默认输出文件为项目根目录下的 `jd_result.xlsx`（可用环境变量 `JD_OUTPUT_PATH` 覆盖）。Excel 中包含 `商品总览` 工作表，以及按商品拆分的评论工作表。

## 生成可视化看板

使用默认 Excel 路径（项目根目录 `jd_result.xlsx`）：

```bash
python excel/generate_dashboard.py
```

指定 Excel 文件：

```bash
python excel/generate_dashboard.py path/to/jd_result.xlsx
```

默认输出：

```text
excel/dashboard.html
```

仓库中的 `excel/dashboard.html` 就是上面这条命令产出的一份效果预览；`dashboard_mysql.html` 是同一套看板接 MySQL 数据源时的效果预览（对应的生成脚本未包含在本仓库）。

看板包含以下内容：

- 商品数量、评论数量、平均好评率、平均评论长度。
- 商品价格对比。
- 销量与好评率对比。
- 评论情感分布。
- 评论长度分布。
- 全局和分商品热门关键词。
- 商品明细表。

## 分析 Notebook

`analysis_notebook.ipynb` 是一个完整的 Jupyter 分析流程，与看板互补，适合交互式探索：

- 从爬取产出的 Excel 加载数据。
- 情感分析（词典匹配）、jieba + TF-IDF 关键词提取、词云。
- 价格-销量 Pearson 相关分析、正面 vs 负面评论长度 t 检验。
- 商品维度综合可视化与数据明细表。

用 Jupyter 打开：

```bash
jupyter notebook analysis_notebook.ipynb
```

> 需要额外安装 `jupyter`、`matplotlib`、`wordcloud`（见 `requirements.txt`）。

## 示例截图

项目包含两张样例图片：

![商品总览](样例图片/商品总览.png)

![商品评论](样例图片/商品评论.png)

## 情感分析

项目使用简单词典匹配法进行中文评论情感分析：

- 正面词命中数大于负面词命中数，标记为 `positive`。
- 负面词命中数大于正面词命中数，标记为 `negative`。
- 两者相等，标记为 `neutral`。

情感词匹配带否定窗口：命中情感词后回看前 **4** 个字符（`NEGATION_WINDOW = 4`），若出现「不 / 没 / 无 / 别 / 非 / 莫 / 未 / 否」则翻转极性。窗口取 4 而不是 2，是为了覆盖「没有什么问题」「没什么异味」这类否定词距情感词 3~4 字的常见句式。

否定窗口不跨常见标点、换行或已匹配的情感词，并排除程度副词“非常”中的“非”。例如“非常满意”“不错，好用”均判为正面。

情感词典和判定逻辑统一位于 `jd_sentiment.py`，Excel 看板与 Notebook 都使用这里的公共函数。Notebook 的停用词仍有本地副本，统一数据接口留待后续改造。

### 已知局限

词典法（逐字符贪心最长匹配 + 固定 4 字否定窗口）的实现简单、可解释，但有几类句子会判错，使用结论时请留意：

- **构词歧义**：「差不多」会命中「差」被判成负面。
- **双重否定**：「不得不承认很好用」只做单次翻转，会被判成负面；`tests/test_sentiment.py` 里有对应的 `xfail` 用例标注这是已知局限。
- **固定窗口与复杂语义**：已有常见标点和已匹配词边界，但仍不理解复杂从句、否定作用范围和省略表达，较长句子仍可能误判。

如果将来评论量级大幅增长，可以把逐字符匹配换成 Aho-Corasick 多模式匹配（`pyahocorasick` / `flashtext`）；当前每商品 20 条的规模没有必要。

## 服务器部署

服务器通常无法直接扫码登录，推荐先在本地生成登录态，再上传到服务器。

1. 本地运行一次并扫码登录：

```bash
python excel/jd_main.py
```

2. 将 `jd_user_data/` 上传到服务器项目根目录。

```bash
tar -czf jd_user_data.tar.gz jd_user_data/
scp jd_user_data.tar.gz user@your-server:/path/to/JD_Spider/
```

3. 在服务器解压：

```bash
cd /path/to/JD_Spider
tar -xzf jd_user_data.tar.gz
```

4. 修改 `jd_config.py`：

```python
HEADLESS = True
```

5. 运行爬虫：

```bash
python excel/jd_main.py
```

如果登录态失效，需要在本地重新扫码并重新上传 `jd_user_data/`。

## 常见问题

### PowerShell 查看 README 出现乱码

README 使用 UTF-8 编码。PowerShell 读取时建议显式指定编码：

```powershell
Get-Content README.md -Encoding UTF8
```

### 没有抓到商品

优先检查：

- 是否已经成功登录京东。
- 京东页面是否出现验证码或风控提示。
- `jd_config.py` 中的商品卡片、名称、价格等 CSS 选择器是否仍然有效。
- `MAX_PRODUCTS` 是否设置过大导致加载不稳定。

### 没有抓到评论

优先检查：

- 商品详情页链接是否为 `https://item.jd.com/数字.html` 格式。
- 评论入口选择器是否变化。
- 是否被京东要求重新登录或验证。
- `MAX_COMMENTS_PER_PRODUCT` 和 `SCROLL_RETRIES` 是否设置合理。

## 注意事项

- 京东页面结构和反爬策略可能变化，脚本失效时优先更新选择器。
- 不建议大批量、高频率采集，避免触发风控。
- 运行产物（`jd_user_data/`、`jd_result.xlsx`、`__pycache__/`）已在 `.gitignore` 中忽略，不会进入版本库。
- `jd_user_data/` 内含登录态，请勿提交或分享。

## 相关项目

- [plugin_JD](https://github.com/yigerenjingjing/plugin_JD) —— 同一套采集思路的浏览器扩展版（Chrome 插件），属于本项目的附属产品，独立维护，不在本仓库内。
