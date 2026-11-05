# 极趣墨水屏 NewsNow 风格看板

**⏱️ 复刻本项目仅需 5 分钟，即可快速拥有专属于你的桌面智能信息看板。**

这是一个专为极趣墨水屏 (Zectrix) 打造的自动化信息看板项目。

无需自行编写代码，只需按照下方步骤配置，即可让你的墨水屏实现全自动推送。完全免费，无需自建服务器。

<img src="./images/preview.jpg" width="60%">
<img src="./images/zhihu.jpg" width="60%">
<img src="./images/weather.jpg" width="60%">

---

## 📌 看板显示内容

本项目适配 400×300 分辨率墨水屏，共包含以下页面：

- **第 1、3 页：可配置信息页** – 每页可选择知乎、B站、GitHub 或任意 RSS/Atom 订阅。两个页面可以使用同一信息源，并自动连续分页。
- **第 2 页：NBA 看板** – 显示当天全部比赛（开赛时间、比分或「进行中」）；15:00 后自动切换为次日赛程预告。
- **第 4 页：综合天气** – 使用彩云天气数据，包含实时温湿度、体感温度、未来预报、日出日落、紫外线及舒适度。

---

## 🛠️ 部署指南

小白用户请依次按照以下 6 个步骤进行操作：

### 1. 复制项目 (Fork)
点击本页面右上角的 **`Fork`** 按钮，将本项目复制到你自己的 GitHub 账号下。

### 2. 更换字体(可选)
1. 项目默认使用 `resources/fonts/zfull-gb.ttf` 点阵字体，更适合 400×300 纯黑白墨水屏。
2. 如需更换字体，准备一个中文字体文件（后缀为 `.ttf`）上传到仓库，再把 `config.py` 中的 `DEFAULT_FONT_PATH` 指向它。

### 3. 配置隐私密钥 (Secrets)
由于涉及个人设备和 API 额度，需要将密钥配置在 GitHub 隐藏设置中。
1. 点击仓库顶部的 **`Settings`** 选项卡。
2. 在左侧菜单栏找到 **`Secrets and variables`**，点击展开后选择 **`Actions`**。
3. 点击 **`New repository secret`** 按钮，**分别添加**以下 3 个密钥：

| 填在 Name 里 | 填在 Secret 里 | 获取方式 |
|---|---|---|
| `ZECTRIX_API_KEY` | 你的极趣云 API Key | 登录 [极趣云控制台](https://cloud.zectrix.com) 获取 |
| `ZECTRIX_MAC` | 墨水屏 MAC 地址 | 格式如 `AA:BB:CC:DD:EE:FF` |
| `CAIYUN_API_TOKEN` | 彩云天气 API Token | 在彩云天气开放平台申请 |

### 4. 自定义城市与页面
你需要修改代码中的几个参数，把天气换成你所在的城市。
1. 在仓库首页，点击打开 **`config.py`** 文件。
2. 点击右上角的 ✏️ (编辑图标)。
3. 在代码顶部的**用户自定义区**，修改引号内的内容：
   - `PAGE_SOURCES`：配置第 1、3 页的信息源（第 2 页固定为 NBA 看板，不能配置信息源）。
   - `NBA_SCORE_SOURCE`：NBA 赛事数据源，默认 `espn`（免 key）；可改为 `official` 使用 NBA 官方 CDN。
   - `CAIYUN_LONGITUDE`：你所在位置的 GCJ-02 经度（高德坐标）。
   - `CAIYUN_LATITUDE`：你所在位置的 GCJ-02 纬度（高德坐标）。
   - `CITY_DISPLAY_NAME`：屏幕左上角显示的标题（如 `北京市 | 我的桌面`）。
   - `ENABLED_PAGES`：控制生成和推送哪些页面，例如只显示第 1、2、4 页时填写 `"1,2,4"`。
4. 修改完成后，点击右上角 **`Commit changes`** 保存。

`PAGE_SOURCES` 的默认配置如下：

```python
PAGE_SOURCES = {
    1: {"source": "github", "title": "GitHub 热门"},
    3: {"source": "zhihu", "title": "知乎热榜"},
}
```

第 1、3 页使用相同来源时，只请求一次数据，并分别显示连续的内容。

使用普通 RSS、Atom 或 RSSHub 地址时，将页面的 `source` 设置为 `rss`：

```python
PAGE_SOURCES = {
    1: {
        "source": "rss",
        "title": "我的技术资讯",
        "url": "https://example.com/feed.xml",
    },
    3: {"source": "github", "title": "GitHub 热门"},
}
```

同一个 RSS 地址配置到多个页面时也会自动连续分页。不同 RSS 地址会被视为不同的信息源。

### NBA 看板（第 2 页）

第 2 页固定为 NBA 单页看板，不需要额外配置或 API Key。每次运行会抓取北京时间昨天/今天/明天/后天的赛程：

- **15:00 前**：显示当天全部比赛。已结束显示比分，直播中显示比分 + 右侧「进行中」标签，未开始显示开赛时间和 `vs`。
- **15:00 起**：显示次日赛程预告，只有对阵和开赛时间。
- 当天 0 场时显示「今日无比赛」，并给出下一比赛日和首场时间。
- 场次多时自动压缩行高：≤8 场用 16–18px 字，14 场用 13px 字，15 场用 12px 字；15 场实测能完整放下。
- 不再显示新闻栏，保证 15 场也能排下。

- **赛事数据**：默认使用 ESPN 公开 scoreboard（免 key，可回查未来数日），并把每场比赛按**北京时间开赛日**重新分桶；设置 `NBA_SCORE_SOURCE=official` 可切换为 NBA 官方 CDN。
- **容错**：数据源失败会重试并回退到最近一次成功缓存，不会清空画面；第 2 页生成失败也不会影响第 1、3、4 页的推送。
- **缓存**：位于 `~/.cache/resoukanban-nba`，可用 `RESOUKANBAN_NBA_CACHE` 改到其它目录；GitHub Actions 上每次都是全新环境，缓存不会跨运行保留。

> **关于刷新频率**：GitHub 的定时任务在高峰期经常延迟，实际间隔可能到 4～11 小时。每次运行会打印 `NBA 第 2 页: 今日 11月05日 · 14 场` 或 `明日 11月06日 · 2 场`，方便判断画面新鲜度。如果想更及时，见下面的「外部定时触发」；同时记得把设备的同步周期调到 30 分钟以内（极趣云支持 10/30/60/180/720 分钟），否则推送再频繁屏幕也不会刷新。

### 外部定时触发（可选）

GitHub 自带的 `schedule` 是尽力而为的队列，高峰时可能延迟数小时甚至跳过。如果想在第 2 页获得更稳定的刷新，可以用外部定时器调用 `workflow_dispatch`，只刷新第 2 页：

1. 新建一个 **fine-grained token**（Settings → Developer settings → Personal access tokens → Fine-grained tokens），只授权 `siduam/resoukanban`，权限只勾 **Actions: Read and write**。这个 token 只用于触发，不要用于推送代码。
2. 手动验证（返回 `HTTP/2 204` 即成功）：
   ```bash
   curl -i -X POST \
     -H "Authorization: Bearer github_pat_xxx" \
     -H "Accept: application/vnd.github+json" \
     -H "X-GitHub-Api-Version: 2022-11-28" \
     https://api.github.com/repos/siduam/resoukanban/actions/workflows/run.yml/dispatches \
     -d '{"ref":"main","inputs":{"pages":"2"}}'
   ```
3. 在 [cron-job.org](https://cron-job.org) 新建任务：
   - URL：上面的接口地址
   - 方法：`POST`
   - 间隔：15 或 30 分钟（试运行建议先 30 分钟）
   - Headers：`Authorization: Bearer github_pat_xxx`、`Accept: application/vnd.github+json`、`X-GitHub-Api-Version: 2022-11-28`、`Content-Type: application/json`
   - Body：`{"ref":"main","inputs":{"pages":"2"}}`（想连第 4 页天气一起刷新就改成 `"pages":"2,4"`）
4. 触发后去 Actions 页面确认：事件是 `workflow_dispatch`，日志里出现 `本次推送页面: 2`，并且只推送了 Page 2。

外部定时器只负责“敲门”，真正的抓取和推送仍由 GitHub Actions 完成；原来的每小时定时任务继续刷新全部页面，两者互不影响。

### 本地预览（推荐）

修改布局或增加页面时，可以先在本地生成图片，不推送到真实设备：

```bash
python3 -m pip install -r requirements.txt
python3 main.py --preview
```

生成的图片位于 `preview/` 目录。预览模式不需要配置
`ZECTRIX_API_KEY` 和 `ZECTRIX_MAC`，但天气页面仍需要
`CAIYUN_API_TOKEN` 才能获取真实天气数据；NBA 页面需要联网抓取赛程，
离线时会显示“今日无比赛”。

如需指定输出目录，或只预览某一页：

```bash
python3 main.py --preview --output-dir output
python3 main.py --preview --pages 2
```

### 代码结构

| 文件 | 职责 |
|---|---|
| `config.py` | 页面、城市、字体和密钥配置 |
| `data_sources.py` | 获取热榜、RSS/Atom 和天气数据 |
| `nba.py` | 抓取 NBA 赛程/赛况并按北京时间分桶 |
| `renderers.py` | 将数据绘制为 400×300 黑白图片 |
| `push.py` | 保存预览图或推送到极趣云 |
| `main.py` | 命令行入口和任务编排 |
| `assets/nba-logo.png` | 由 `assets/nba-script.svg` 预渲染的 NBA 字标（避免运行期依赖 CairoSVG） |

### 5. 修改推送频率 (可选)
默认情况下，系统每小时自动推送一次（`run.yml` 中 `cron: '37 */1 * * *'`）。如需修改：
1. 进入仓库的 `.github/workflows/` 文件夹，点击编辑里面的 `.yml` 文件。
2. 找到 `cron: '37 */1 * * *'` 这一行进行修改。
3. **注意：此处使用的是 UTC 时间，比北京时间慢 8 小时。**
   - 每小时更新一次：`cron: '37 * * * *'`
   - 每 2 小时更新一次：`cron: '0 */2 * * *'`
   - 每天早上 8 点更新一次（北京时间 8点 = UTC 0点）：`cron: '0 0 * * *'`
4. 修改后点击 **`Commit changes`** 保存。

> GitHub Actions 的定时任务在整点前后经常排队延迟，实际执行间隔可能明显长于设定值；对 NBA 比分有实时性要求时，请参考上面的「NBA 看板」小节。

### 6. 手动运行并激活
配置完成后，我们需要手动让它运行一次。
1. 点击仓库顶部的 **`Actions`** 选项卡。
2. 若弹出绿色提示框，请点击 **`I understand my workflows, go ahead and enable them`**。
3. 在左侧列表找到推送任务，点击选中它。
4. 点击右侧的 **`Run workflow`** 按钮，再点击弹出框中的确认按钮。

---

## 🚀 未来规划

本项目将持续迭代，计划增加以下功能：

1. 📈 **B 站粉丝看板**：增加专门的页面，实时显示 B 站粉丝数及动态。

---

## 💖 致谢
- 天气数据支持：彩云天气
- 信息源支持：[知乎](https://www.zhihu.com)、[Bilibili](https://www.bilibili.com)、[GitHub](https://github.com) 与 RSS/Atom
- NBA 数据：ESPN 公开 scoreboard、NBA 官方 Live CDN
- NBA 页面逻辑移植自 [zectrix-nba-board](https://github.com/happynailinzz/zectrix-nba-board)，感谢原作者
- 硬件及推送接口：[极趣云 Zectrix](https://cloud.zectrix.com)

---
如果觉得这个项目有用，欢迎给个 ⭐ 支持一下！
