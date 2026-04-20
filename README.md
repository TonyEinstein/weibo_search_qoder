# 微博搜索爬虫 - Weibo Search Qoder

## 项目简介

本项目是一个基于 `requests` + `lxml` 实现的高性能微博搜索爬虫，用于抓取微博搜索结果数据并保存为 CSV 格式。项目采用轻量化设计，无需依赖 Scrapy 框架，支持多线程并发、智能反爬优化、IDE 一键运行，易于集成到其他项目中。

## 致谢

本项目基于 [dataabc/weibo-search](https://github.com/dataabc/weibo-search) 项目进行实现，感谢原作者 [dataabc](https://github.com/dataabc) 的无私奉献和开源精神。原始项目提供了优秀的微博搜索爬虫实现思路，为本项目的开发提供了重要的参考基础。

## 如何获取cookie
1. 用Chrome打开 https://weibo.com/
2. 点击"立即登录", 完成私信验证或手机验证码验证, 进入新版微博. 如下图所示:
<img src="https://user-images.githubusercontent.com/41314224/144813569-cfb5ad32-22f0-4841-afa9-83184b2ccf6f.png" width="400px" alt="...">
3. 按F12打开开发者工具, 在开发者工具的 Network->Name->weibo.cn->Headers->Request Headers, 找到"Cookie:"后的值, 这就是我们要找的cookie值, 复制即可, 如图所示:
<img src="https://github.com/dataabc/media/blob/master/weiboSpider/images/cookie3.png" width="400px" alt="...">

> ## 兼容性说明: 获取旧版微博的Cookie【以此为准】
> 1.用Chrome打开<https://passport.weibo.cn/signin/login>；<br>
> 2.输入微博的用户名、密码，登录，如图所示：
> ![](https://github.com/dataabc/media/blob/master/weiboSpider/images/cookie1.png)
> 登录成功后会跳转到<https://m.weibo.cn>;<br>
> 3.按F12键打开Chrome开发者工具，在地址栏输入并跳转到<https://weibo.cn>，跳转后会显示如下类似界面:
> ![](https://github.com/dataabc/media/blob/master/weiboSpider/images/cookie2.png)
> 4.依此点击Chrome开发者工具中的Network->Name中的weibo.cn->Headers->Request Headers，"Cookie:"后的值即为我们要找的cookie值，复制即可，如图所示：
> ![](https://github.com/dataabc/media/blob/master/weiboSpider/images/cookie3.png)

## 环境要求

- **Python 版本**: Python 3.8 或更高版本
- **操作系统**: Windows / macOS / Linux 均可运行
- **网络环境**: 需要能够访问微博网站 (weibo.com / weibo.cn)

## 如何使用

### 快速开始（3步运行）

1. **配置 Cookie**: 编辑 `config.py` 文件，将获取到的 Cookie 填入 `COOKIE` 变量
2. **设置关键词**: 在 `config.py` 中修改 `KEYWORD_LIST` 为你要搜索的关键词
3. **运行程序**: 使用 IDE 运行 `main.py`，或在命令行执行 `python main.py`

### 使用方式详解

#### 方式1: IDE 一键运行（推荐）

1. 打开 PyCharm / VS Code 等 IDE
2. 打开项目文件夹 `weibo_search_qoder`
3. 编辑 `config.py` 配置 Cookie 和搜索参数
4. 点击运行按钮运行 `main.py`

#### 方式2: 命令行运行

```bash
cd weibo_search_qoder

# 安装依赖
pip install -r requirements.txt

# 运行爬虫
python main.py
```

#### 方式3: 作为模块导入使用

```python
from main import run_crawler, run_crawler_with_params

# 使用默认配置运行
run_crawler()

# 使用自定义参数运行
run_crawler_with_params(
    keyword_list=['迪丽热巴'],
    start_date='2026-01-01',
    end_date='2026-01-31',
    limit_result=100
)
```

#### 方式4: 使用链式 API（高级）

```python
from spider import WeiboSpider

with WeiboSpider() as spider:
    spider.set_keywords(['周杰伦', '林俊杰']) \
          .set_date_range('2026-01-01', '2026-01-31') \
          .set_weibo_type([2, 5]) \
          .set_limit(100) \
          .run()
```

## 配置项说明

所有配置项集中在 `config.py` 文件中，以下是详细说明：

### 搜索参数配置

| 配置项 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `KEYWORD_LIST` | list/str | 搜索关键词列表，或关键词文件路径 | `['迪丽热巴']` 或 `'keywords.txt'` |
| `COOKIE` | str | 微博登录 Cookie（必填） | 从浏览器复制 |
| `START_DATE` | str | 搜索起始日期 (yyyy-mm-dd) | `'2026-01-01'` |
| `END_DATE` | str | 搜索终止日期 (yyyy-mm-dd) | `'2026-01-31'` |
| `WEIBO_TYPE` | int/list | 微博类型筛选 | `0`=全部, `1`=原创, `2`=热门, `5`=媒体 |
| `CONTAIN_TYPE` | int | 内容类型筛选 | `0`=全部, `1`=图片, `2`=视频, `3`=音乐, `4`=链接 |
| `REGION` | list | 发布地区筛选 | `['北京', '上海']` 或 `['全部']` |
| `LIMIT_RESULT` | int | 结果数量限制（0=无限制） | `300` |
| `FURTHER_THRESHOLD` | int | 细分搜索阈值（建议40-50） | `46` |

### 多线程配置

| 配置项 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `ENABLE_MULTITHREAD` | bool | 是否启用多线程 | `True` |
| `MAX_WORKERS` | int | 最大并发线程数（建议2-5） | `4` |

### 反爬优化配置

| 配置项 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `ENABLE_ANTI_DETECT` | bool | 启用反爬优化 | `True` |
| `ENABLE_HEADER_SPOOFING` | bool | 启用请求头伪装 | `True` |
| `ENABLE_PROXY` | bool | 启用代理 | `False` |
| `PROXY_LIST` | list | 代理池列表 | `['http://ip:port']` |
| `PROXY_STRATEGY` | str | 代理策略: 'random'/'round_robin' | `'random'` |
| `VERIFY_PROXY` | bool | 启动时验证代理 | `False` |
| `COOKIE_POOL` | list | Cookie池（多账号轮换） | `[{'name': '账号1', 'cookie': 'xxx'}]` |

### 请求配置

| 配置项 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `DOWNLOAD_DELAY` | list | 请求间隔随机范围（秒） | `[2, 5]` |
| `REQUEST_TIMEOUT` | list | 请求超时随机范围（秒） | `[5, 20]` |
| `RETRY_TIMES` | list | 重试次数随机范围 | `[2, 4]` |
| `USE_RANDOM_USER_AGENT` | bool | 使用随机 User-Agent | `True` |
| `USER_AGENT` | str | 固定 User-Agent | 浏览器 UA 字符串 |

### 输出配置

| 配置项 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `OUTPUT_DIR` | str | 结果输出目录 | `'结果'` |
| `LOG_LEVEL` | str | 日志级别: DEBUG/INFO/WARNING/ERROR | `'INFO'` |
| `LOG_TO_FILE` | bool | 是否输出日志到文件 | `True` |

> **注意**：日志文件默认保存在 `log/YYYY-MM-DD.log` 路径下（如 `log/2026-04-20.log`），按日期自动命名。

## 抓取的数据结果字段

抓取的数据将保存为 CSV 格式，包含以下字段：

| 字段名 | 说明 | 数据类型 | 示例 |
|--------|------|----------|------|
| `id` | 微博唯一ID | string | `5123456789012345` |
| `bid` | 微博bid标识 | string | `O8xK7fF3L` |
| `user_id` | 发布用户ID | string | `1234567890` |
| `用户昵称` | 发布用户昵称 | string | `微博小助手` |
| `微博正文` | 微博文字内容 | string | `今天天气真好！` |
| `头条文章url` | 头条文章链接 | string | `https://weibo.com/...` |
| `发布位置` | 地理位置信息 | string | `北京·朝阳区` |
| `艾特用户` | @的用户列表 | string | `@用户1 @用户2` |
| `话题` | 包含的话题标签 | string | `#天气# #生活#` |
| `转发数` | 被转发次数 | string | `128` |
| `评论数` | 评论数量 | string | `56` |
| `点赞数` | 点赞数量 | string | `1024` |
| `发布时间` | 发布日期时间 | string | `2026-01-15 14:30:00` |
| `发布工具` | 发布来源设备 | string | `iPhone 15 Pro` |
| `微博图片url` | 图片链接列表 | string | `url1,url2,url3` |
| `微博视频url` | 视频链接 | string | `https://video.weibo.com/...` |
| `retweet_id` | 转发微博ID | string | `5123456789012344` |
| `ip` | IP属地 | string | `北京` |
| `user_authentication` | 用户认证信息 | string | `微博认证用户` |
| `会员类型` | 会员类型 | string | `年费会员` |
| `会员等级` | 会员等级 | int | `7` |

## 功能特性

### 核心功能
- **关键词搜索**：支持多关键词搜索，支持话题格式（#话题#）
- **时间范围筛选**：支持按日期范围筛选微博
- **微博类型筛选**：支持原创、热门、认证用户等多种类型，支持多类型组合
- **内容类型筛选**：支持图片、视频、音乐、链接筛选
- **地区筛选**：支持按省份/城市筛选
- **数据去重**：自动去重，避免重复抓取

### 高级特性
- **多线程并发**：支持多关键词并行抓取，提升采集效率
- **智能反爬优化**：自适应延迟、请求头伪装、反爬检测与自动恢复
- **Cookie 池管理**：支持多账号轮换，提高抗封能力
- **代理池支持**：支持 HTTP/HTTPS 代理，支持随机/轮询策略
- **随机 User-Agent**：支持随机 User-Agent 防止被封
- **智能细分策略**：当结果过多时自动按天/小时/地区细分抓取
- **日志记录**：完整的日志记录，支持文件和控制台输出
- **CSV 导出**：数据自动保存为 CSV 格式，支持中文文件名，带时间戳

## 项目结构

```
weibo_search_qoder/
├── config.py           # 配置文件（搜索参数、Cookie、输出路径等）
├── main.py             # 项目入口，支持 IDE 一键运行
├── spider.py           # 爬虫类封装，提供链式调用 API
├── weibo_crawler.py    # 核心爬虫类，实现请求、解析、存储逻辑
├── weibo_item.py       # 微博数据模型，定义数据结构
├── utils.py            # 工具函数（日期转换、URL构建等）
├── region.py           # 地区数据字典
├── user_agents.py      # User-Agent 列表和随机生成器
├── anti_detect.py      # 反爬优化模块（代理、Cookie池、自适应延迟）
├── requirements.txt    # 项目依赖
├── log/                # 日志目录（按日期存储）
│   └── 2026-04-20.log
└── 结果/               # 结果输出目录
    └── 关键词-20260420120000.csv
```

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        项目入口层                            │
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   main.py   │  │  spider.py      │  │  第三方导入      │ │
│  │  (IDE运行)   │  │ (WeiboSpider类) │  │  (run_crawler)  │ │
│  └──────┬──────┘  └────────┬────────┘  └─────────────────┘ │
└─────────┼──────────────────┼───────────────────────────────┘
          │                  │
          ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                      核心爬虫层                              │
│                    ┌──────────────┐                         │
│                    │ WeiboCrawler │                         │
│                    │  (核心类)     │                         │
│                    └──────┬───────┘                         │
│           ┌───────────────┼───────────────┐                 │
│           ▼               ▼               ▼                 │
│    ┌────────────┐  ┌────────────┐  ┌────────────┐          │
│    │ 请求模块   │  │ 解析模块   │  │ 存储模块   │          │
│    │ _make_     │  │ _parse_    │  │ _save_to_  │          │
│    │ _request() │  │ weibo()    │  │ _csv()     │          │
│    └────────────┘  └────────────┘  └────────────┘          │
└─────────────────────────────────────────────────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                      基础设施层                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Config类   │  │ WeiboItem类 │  │      utils.py       │ │
│  │  (配置管理)  │  │ (数据模型)   │  │ (工具函数:日期/URL) │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ user_agents │  │   region.py │  │      log/           │ │
│  │ (UA管理)    │  │ (地区数据)   │  │    (日志存储)        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 运行流程图

```
┌──────────┐     ┌──────────────┐     ┌──────────────────┐
│  启动程序 │────▶│ 加载配置文件  │────▶│ 检查Cookie有效性 │
└──────────┘     └──────────────┘     └────────┬─────────┘
                                                │
                        ┌───────────────────────┘
                        ▼
              ┌────────────────────┐
              │ Cookie无效?        │────▶ 退出程序
              │ 提示配置方法       │
              └────────┬───────────┘
                       │ Cookie有效
                       ▼
              ┌────────────────────┐
              │ 初始化日志系统      │
              │ (log/日期.log)     │
              └────────┬───────────┘
                       ▼
              ┌────────────────────┐
              │ 初始化WeiboCrawler │
              │ - 关键词处理        │
              │ - URL编码/解码      │
              │ - 创建映射关系      │
              └────────┬───────────┘
                       ▼
              ┌────────────────────┐
              │ 循环处理每个关键词  │◀────────────────┐
              │ (keyword_list)     │                 │
              └────────┬───────────┘                 │
                       │                             │
                       ▼                             │
              ┌────────────────────┐                 │
              │ 构建搜索URL        │                 │
              │ - 时间范围          │                 │
              │ - 微博类型          │                 │
              │ - 内容筛选          │                 │
              └────────┬───────────┘                 │
                       │                             │
                       ▼                             │
              ┌────────────────────┐                 │
              │ 发送HTTP请求       │                 │
              │ - 禁用代理          │                 │
              │ - 随机UA(可选)      │                 │
              │ - 重试机制          │                 │
              └────────┬───────────┘                 │
                       │                             │
                       ▼                             │
              ┌────────────────────┐                 │
              │ 解析HTML响应       │                 │
              │ - lxml XPath      │                 │
              │ - 提取微博列表      │                 │
              └────────┬───────────┘                 │
                       │                             │
                       ▼                             │
              ┌────────────────────┐                 │
              │ 循环处理每条微博   │◀──────────────┐ │
              │ (card-wrap)        │               │ │
              └────────┬───────────┘               │ │
                       │                           │ │
                       ▼                           │ │
              ┌────────────────────┐               │ │
              │ 检查是否已抓取     │               │ │
              │ (seen_ids去重)     │               │ │
              └────────┬───────────┘               │ │
                       │ 已抓取                     │ │
                       ▼                           │ │
              ┌────────────────────┐               │ │
              │ 跳过该微博         │───────────────┘ │
              └────────────────────┘                 │
                       │ 未抓取
                       ▼
              ┌────────────────────┐
              │ 解析微博详情       │
              │ - 用户昵称          │
              │ - 正文内容          │
              │ - 互动数据          │
              │ - 图片/视频         │
              └────────┬───────────┘
                       │
                       ▼
              ┌────────────────────┐
              │ 保存到CSV          │
              │ - 按关键词分目录    │
              │ - UTF-8编码        │
              │ - 实时刷新          │
              └────────┬───────────┘
                       │
                       ▼
              ┌────────────────────┐
              │ 输出抓取日志       │
              │ [序号] 昵称 - 内容  │
              └────────┬───────────┘
                       │
                       └───────────────────────────────┘
                       │
                       ▼ (所有关键词处理完毕)
              ┌────────────────────┐
              │ 关闭CSV文件句柄    │
              │ 输出统计信息        │
              └────────┬───────────┘
                       ▼
              ┌────────────────────┐
              │    程序结束        │
              └────────────────────┘
```

## 模块功能说明

### 1. config.py - 配置模块

集中管理所有配置参数，包括：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `KEYWORD_LIST` | 搜索关键词列表 | `['迪丽热巴', '周杰伦']` |
| `COOKIE` | 微博登录Cookie | 从浏览器复制 |
| `START_DATE` / `END_DATE` | 搜索时间范围 | `'2026-01-01'` |
| `WEIBO_TYPE` | 微博类型 (0-6) | `[2, 5]` 表示热门+媒体 |
| `CONTAIN_TYPE` | 内容筛选 (0-4) | `1` 表示仅图片 |
| `REGION` | 地区筛选 | `['北京', '上海']` |
| `LIMIT_RESULT` | 结果数量限制 | `300` (0表示无限制) |
| `DOWNLOAD_DELAY` | 请求间隔(秒) | `[2, 5]` 随机范围 |
| `OUTPUT_DIR` | 结果输出目录 | `'结果'` |
| `ENABLE_MULTITHREAD` | 启用多线程 | `True` |
| `MAX_WORKERS` | 最大线程数 | `5` |
| `ENABLE_ANTI_DETECT` | 启用反爬优化 | `True` |
| `ENABLE_PROXY` | 启用代理 | `False` |
| `COOKIE_POOL` | Cookie池 | `[{'name': '账号1', 'cookie': 'xxx'}]` |

### 2. main.py - 入口模块

提供三种启动方式：

```python
# 方式1: 使用默认配置
from main import run_crawler
run_crawler()

# 方式2: 使用自定义配置
from main import run_crawler
from config import Config

config = Config()
config.KEYWORD_LIST = ['周杰伦']
config.LIMIT_RESULT = 50
run_crawler(config)

# 方式3: 使用参数
from main import run_crawler_with_params
run_crawler_with_params(
    keyword_list=['周杰伦'],
    start_date='2026-01-01',
    limit_result=100
)
```

### 3. weibo_crawler.py - 核心爬虫模块

核心类 `WeiboCrawler` 的主要方法：

| 方法 | 功能 |
|------|------|
| `__init__()` | 初始化配置、日志、Session、反爬管理器 |
| `crawl()` | 主爬取入口，支持多线程/单线程模式 |
| `_make_request()` | 发送HTTP请求，带重试机制和反爬检测 |
| `_parse_weibo()` | 解析单条微博数据 |
| `_parse_page()` | 解析搜索结果页面 |
| `_crawl_by_day()` | 按天细分抓取策略 |
| `_crawl_by_hour()` | 按小时细分抓取策略 |
| `_crawl_single_keyword()` | 单关键词爬取（多线程使用） |
| `_save_to_csv()` | 保存数据到CSV文件 |
| `_check_limit()` | 检查抓取数量限制（线程安全） |

### 6. anti_detect.py - 反爬优化模块

提供完整的反爬解决方案：

| 类/函数 | 功能 |
|---------|------|
| `AntiDetectManager` | 反爬管理器，统一管理代理、Cookie、请求头 |
| `AdaptiveDelay` | 自适应延迟控制器，根据成功率动态调整延迟 |
| `build_headers()` | 构建伪装请求头 |
| `get_proxy()` | 获取代理（支持随机/轮询策略） |
| `check_response()` | 检测是否触发反爬 |
| `get_session_config()` | 获取完整的会话配置 |

### 4. weibo_item.py - 数据模型

`WeiboItem` 类定义微博数据结构：

```python
weibo.id              # 微博ID
weibo.bid             # 微博bid
weibo.user_id         # 用户ID
weibo.screen_name     # 用户昵称
weibo.text            # 微博正文
weibo.created_at      # 发布时间
weibo.source          # 发布来源
weibo.pics            # 图片URL列表
weibo.video_url       # 视频URL
weibo.reposts_count   # 转发数
weibo.comments_count  # 评论数
weibo.attitudes_count # 点赞数
weibo.location        # 发布位置
weibo.at_users        # @用户列表
weibo.topics          # 话题列表
```

### 5. utils.py - 工具模块

提供辅助函数：

| 函数 | 功能 |
|------|------|
| `convert_weibo_type()` | 转换微博类型为URL参数 |
| `convert_contain_type()` | 转换内容筛选为URL参数 |
| `get_keyword_list()` | 从文件或列表获取关键词 |
| `process_keywords()` | 处理话题格式 |
| `standardize_date()` | 标准化微博时间格式 |
| `validate_dates()` | 验证日期范围合法性 |

### 7. spider.py - 高级封装

提供链式调用 API，支持 fluent interface：

```python
from spider import WeiboSpider

# 基础链式调用
with WeiboSpider() as spider:
    spider.set_keywords(['周杰伦', '林俊杰']) \
          .set_date_range('2026-01-01', '2026-01-31') \
          .set_limit(100) \
          .run()

# 高级配置（多线程+反爬优化）
with WeiboSpider() as spider:
    spider.set_keywords(['迪丽热巴']) \
          .set_date_range('2026-01-01', '2026-01-31') \
          .set_weibo_type([2, 5]) \
          .set_multithread(True, max_workers=5) \
          .set_anti_detect(True, random_delay_min=2, random_delay_max=8) \
          .set_limit(300) \
          .run()
```

**WeiboSpider 支持的方法：**

| 方法 | 说明 |
|------|------|
| `set_keywords()` | 设置关键词列表 |
| `set_cookie()` | 设置Cookie |
| `set_date_range()` | 设置日期范围 |
| `set_weibo_type()` | 设置微博类型（支持列表） |
| `set_contain_type()` | 设置内容筛选类型 |
| `set_region()` | 设置地区筛选 |
| `set_limit()` | 设置结果数量限制 |
| `set_delay()` | 设置下载延迟 |
| `set_multithread()` | 设置多线程模式 |
| `set_anti_detect()` | 设置反爬优化 |
| `set_output_dir()` | 设置输出目录 |
| `set_log_level()` | 设置日志级别 |
| `run()` | 运行爬虫 |
| `get_stats()` | 获取统计信息 |

## 项目启动方式

### 方式1: IDE 一键运行（推荐）

1. 打开 PyCharm / VS Code
2. 打开 `weibo_search_qoder` 文件夹
3. 编辑 `config.py`，配置 `COOKIE`
4. 点击运行按钮运行 `main.py`

### 方式2: 命令行运行

```bash
cd weibo_search_qoder

# 安装依赖
pip install -r requirements.txt

# 运行爬虫
python main.py
```

### 方式3: 作为模块导入

```python
from weibo_search_qoder.main import run_crawler, run_crawler_with_params
from weibo_search_qoder.spider import WeiboSpider

# 使用函数
run_crawler_with_params(
    keyword_list=['迪丽热巴'],
    start_date='2026-01-01',
    end_date='2026-01-31',
    limit_result=50
)
```

## 依赖安装

```bash
pip install -r requirements.txt
```

依赖列表：
- `requests>=2.28.0` - HTTP请求库
- `lxml>=4.9.0` - HTML解析库
- `fake-useragent` - 随机User-Agent生成

## 高级配置示例

### 1. 多线程配置

```python
# config.py
ENABLE_MULTITHREAD = True      # 启用多线程
MAX_WORKERS = 5                # 最大并发线程数（建议2-5）
```

### 2. 反爬优化配置

```python
# config.py
ENABLE_ANTI_DETECT = True      # 启用反爬优化
ENABLE_HEADER_SPOOFING = True  # 启用请求头伪装

# 下载延迟（支持范围配置，每次请求随机取值）
DOWNLOAD_DELAY = [2, 5]        # 2-5秒随机延迟

# 请求超时（支持范围配置）
REQUEST_TIMEOUT = [5, 20]      # 5-20秒随机超时

# 重试次数（支持范围配置）
RETRY_TIMES = [2, 4]           # 2-4次随机重试
```

### 3. Cookie 池配置

```python
# config.py
# 主Cookie（必须配置）
COOKIE = 'your_cookie_here'

# Cookie池（用于多账号轮换）
COOKIE_POOL = [
    {'name': '账号1', 'cookie': 'cookie1'},
    {'name': '账号2', 'cookie': 'cookie2'},
]
```

### 4. 代理池配置

```python
# config.py
ENABLE_PROXY = True            # 启用代理
PROXY_LIST = [                 # 代理列表
    'http://ip1:port',
    'http://user:pass@ip2:port',
]
PROXY_STRATEGY = 'random'      # 轮换策略: 'random'随机 / 'round_robin'轮询
VERIFY_PROXY = False           # 是否验证代理可用性
```

## 注意事项

1. **Cookie 配置**：必须在 `config.py` 中配置有效的微博 Cookie 才能获取数据
2. **请求频率**：建议保持 `DOWNLOAD_DELAY` 在 2-10 秒范围，避免被封IP
3. **多线程建议**：`MAX_WORKERS` 建议设置为 2-5，过高容易触发反爬
4. **数据去重**：程序会自动去重，同一微博不会重复保存
5. **日志查看**：日志保存在 `log/日期.log` 文件中
6. **结果查看**：CSV 文件保存在 `结果/` 目录下，文件名格式为 `关键词-时间戳.csv`
7. **反爬检测**：启用 `ENABLE_ANTI_DETECT` 后，程序会自动检测反爬并调整策略
8. **代理验证**：启用 `VERIFY_PROXY` 会在启动时验证所有代理，可能增加启动时间

## 技术栈

- **语言**: Python 3.8+
- **HTTP请求**: requests
- **HTML解析**: lxml
- **数据存储**: CSV
- **日志**: logging
- **并发**: concurrent.futures (ThreadPoolExecutor)

## 更新日志

### v2.2 (2026-04-20)
- **Bug 修复**: 修复 `_get_csv_writer` 非线程安全问题，添加锁保护文件创建和表头写入
- **Bug 修复**: 修复 `standardize_date` 日期解析异常处理问题，增强健壮性
- **Bug 修复**: 修复 `get_keyword_list` 文件资源管理问题，优化文件关闭逻辑
- **Bug 修复**: 修复 `_verify_proxy` 代理验证超时问题，减少启动阻塞时间
- **Bug 修复**: 修复 `weibo_type_list` 为空时的潜在问题，添加默认值保护
- **Bug 修复**: 修复多线程下 `result_count` 读取非原子操作问题，确保日志序号准确
- **Bug 修复**: 修复 `_close_csv_files` 字典遍历线程安全问题，添加锁保护

### v2.1 (2026-04-20)
- **Bug 修复**: 修复地区筛选+分页时的缩进错误，解决数据丢失问题
- **Bug 修复**: 修复多线程模式下 CSV 文件写入冲突问题，添加线程锁保护
- **Bug 修复**: 修复日志文件被覆盖问题，改为追加模式保存历史日志
- **Bug 修复**: 修复 Cookie 空值检测逻辑，完善空字符串检测
- **Bug 修复**: 修复转发微博缺少去重检查问题，避免重复保存
- **Bug 修复**: 修复日期格式验证缺少异常处理问题，提供友好错误提示
- **Bug 修复**: 修复 pics/video_url 赋值逻辑重复问题，优化媒体资源分配
- **Bug 修复**: 修复转发微博去重后的空指针问题

### v2.0 (2026-04)
- 新增多线程并发抓取功能
- 新增智能反爬优化模块 (`anti_detect.py`)
- 新增 Cookie 池管理支持
- 新增代理池支持（随机/轮询策略）
- 新增自适应延迟控制器
- 支持范围配置的延迟/超时/重试次数
- 优化 CSV 文件存储结构（扁平化目录+时间戳）
- 增强线程安全性

### v1.0 (2026-03)
- 初始版本发布
- 基于 requests + lxml 的轻量化实现
- 支持关键词搜索、时间筛选、地区筛选
- 支持微博类型和内容类型筛选
- 数据去重和 CSV 导出功能

## 许可证

本项目仅供学习研究使用，请遵守微博平台相关协议。
