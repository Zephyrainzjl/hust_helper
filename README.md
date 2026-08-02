<p align="center">
  <img src="docs/assets/hust_helper_cover.png" alt="hust_helper cover / hust_helper 封面图" width="100%">
</p>

<!--
封面图占位说明：
后续确定正式封面后，直接用新图片覆盖 docs/assets/hust_helper_cover.png 即可，README 无需修改。
Cover placeholder: replace docs/assets/hust_helper_cover.png with the final cover image.
-->

<h1 align="center">hust_helper</h1>

<p align="center">
  <strong>华中科技大学校园生活助手 · 从“今天吃什么”开始</strong><br>
  <strong>An extensible HUST campus-life assistant, starting with food discovery</strong>
</p>

<p align="center">
  <a href="#中文说明">中文</a> ·
  <a href="#english-version">English</a> ·
  <a href="https://github.com/Zephyrainzjl/hust_helper/releases/latest/download/hust_helper-windows-x64.exe">直接下载 Windows EXE</a> ·
  <a href="https://github.com/Zephyrainzjl/hust_helper/releases">Releases</a>
</p>

---

<a id="中文说明"></a>

# 中文说明

> [!IMPORTANT]
> ## 项目缘起与致谢
>
> `hust_helper` 不只是一个软件项目，也是一份由真实校园生活积累而成的共同记忆。
>
> 1. **本项目源于作者所在某材料学院课题组在华中科技大学多年的学习、科研与共同吃饭经历。**
> 2. **项目的首个工具 `hust_eater` 参考了某位华中科技大学机械学院师兄编写并提供的 PDF《HUSTer 的干饭修养——HUST 求学七年的干饭经验》。**原 PDF 署名为“许少 著”。
> 3. **项目中的推荐、补充、修订与口味判断，凝结了作者每一位朋友在华科校园及武汉各处的真实饮食体验总结。**
>
> 感谢课题组的每一次聚餐，感谢那位机械学院师兄整理并分享原始指南，也感谢每一位朋友认真讲述“哪里好吃、什么值得点、哪些地方需要避坑”。这些经验共同构成了 `hust_helper` 的起点。

## 不想写代码？直接下载 EXE

<p align="center">
  <a href="https://github.com/Zephyrainzjl/hust_helper/releases/latest/download/hust_helper-windows-x64.exe">
    <strong>⬇️ 直接下载 hust_helper Windows 版（EXE）</strong>
  </a>
</p>

你不需要安装 Python，也不需要配置开发环境。下载后直接运行即可。

> [!NOTE]
> 固定下载地址对应 GitHub Releases 中名为 `hust_helper-windows-x64.exe` 的最新发布资产。首次发布 EXE 时，请确保上传文件使用这一名称；此后链接会自动指向最新版本。

## 项目简介

`hust_helper` 是一个面向华中科技大学学生、校友和访客的可扩展校园生活助手。项目采用标准 Python `src/` 布局，既可以作为 Python 包安装，也可以构建为 Windows 桌面程序和 Android 应用。

当前首个工具为：

```text
src/hust_helper/tools/hust_eater
```

`hust_eater` 将原始饮食指南整理为可检索、可编辑、可扩展、可追溯的数据系统，并提供：

- Python API 与 Jupyter Notebook 调用；
- 命令行检索；
- 桌面与移动端图形界面；
- 菜名、店名、区域、菜系、预算、辣度、时间等多条件搜索；
- 图片浏览、添加、替换、隐藏与删除；
- 用户自定义餐厅、食堂窗口和推荐菜；
- OpenAI、SiliconFlow、OpenRouter、DeepSeek、DashScope 兼容接口及自定义 OpenAI-compatible API；
- 面向后续校园工具的插件化扩展框架。

## 核心特点

### 1. 来源可追溯的数据

基础数据保留原 PDF 的页面、段落、图片、来源页码和结构化条目。搜索结果可以追溯到原始内容，而不是只保留二次摘要。

### 2. 可持续扩展

基础数据与用户数据分离：

- 安装包中的基础数据保持只读；
- 用户新增、修改和隐藏内容写入独立 overlay；
- 软件升级不会自动覆盖个人记录；
- 后续可以接入住宿、交通、学习、办事、运动和校园服务等新工具。

### 3. 多种搜索方式

可以使用：

- 店铺名、食堂名、窗口名和菜名；
- 自然语言，例如“东区不辣、便宜一点的晚饭”；
- 章节、区域、类别、用餐时段、价格、辣度和标签；
- 作者亲自体验、朋友推荐或公开来源推荐等状态；
- 本地搜索或大语言模型对话搜索。

### 4. 多端使用

- `pip` 安装；
- Python / Notebook API；
- CLI；
- Flet 图形界面；
- Windows EXE；
- Android APK / AAB。

## 项目结构

```text
hust_helper/
├── docs/
│   ├── assets/
│   │   └── hust_helper_cover.png   
│   ├── architecture.md
│   ├── building.md
│   └── data_model.md
├── examples/
│   └── hust_eater_api.ipynb
├── scripts/
│   ├── build_desktop.ps1
│   ├── build_desktop.sh
│   ├── build_android.ps1
│   ├── build_android.sh
│   └── extract_hust_eater_pdf.py
├── src/
│   ├── main.py
│   └── hust_helper/
│       ├── core/
│       ├── llm/
│       ├── tools/
│       │   └── hust_eater/
│       └── ui/
├── tests/
├── DATA_LICENSE.md
├── LICENSE
├── pyproject.toml
└── README.md
```

## 安装

### 从 PyPI 或本地 Wheel 安装

```bash
python -m pip install hust_helper
```

或：

```bash
python -m pip install ./hust_helper-0.1.0-py3-none-any.whl
```

### 从源码安装

仅使用核心 API：

```bash
git clone https://github.com/Zephyrainzjl/hust_helper.git
cd hust_helper
python -m pip install -e .
```

安装 GUI、Notebook、LLM 与开发依赖：

```bash
python -m pip install -e ".[all,dev]"
```

## 快速开始

### Python / Jupyter Notebook

```python
from hust_helper import eater

print(eater.stats())

results = eater.search(
    "不辣 鸡汤",
    limit=10,
)

for item in results:
    print(item.name)
    print(item.section_title)
    print(item.recommended_items)
```

组合筛选：

```python
near_hust = eater.search(
    "炸鸡",
    chapter="华科周边美食篇",
    visited="visited_by_author",
    limit=5,
)
```

读取原始页面和图片：

```python
page_10 = eater.page(10)
page_10_markdown = eater.page_markdown(10)
image_bytes = eater.image_bytes("media-p010-01")
```

新增或修改自己的记录：

```python
entry = eater.add(
    name="我的新发现",
    chapter_title="用户扩展",
    section_title="华科周边",
    description="朋友推荐的新店，适合多人聚餐。",
    tags=["朋友推荐", "用户扩展"],
)

eater.update(entry.id, description="第二次体验后更新的说明。")
eater.add_image(entry.id, "food.jpg", caption="朋友聚餐实拍")
```

完整示例见：

```text
examples/hust_eater_api.ipynb
```

### 命令行

```bash
hust-helper stats
hust-helper search "热干面" --section 洪山区 --limit 10
hust-helper search "东区 不辣 便宜" --limit 10
hust-helper export --format json --output my_food_catalog.json
hust-helper gui
```

## 图形界面

安装 GUI 依赖：

```bash
python -m pip install -e ".[gui]"
```

启动：

```bash
hust-helper gui
```

也可以：

```bash
python src/main.py
```

图形界面包含：

- 多条件食物搜索；
- AI 对话式搜索；
- 餐厅与食堂详情；
- 图片浏览与管理；
- 数据新增、编辑、隐藏和恢复；
- API 厂商、模型和密钥配置；
- 数据来源与许可说明。

## 大语言模型 API

项目支持统一的模型配置接口。建议通过环境变量提供 API Key，不要把密钥写入代码或提交到 Git。

```python
from hust_helper.llm import FoodChatAgent, LLMConfig

config = LLMConfig.from_preset(
    "openai",
    model="your-model-id",
)

agent = FoodChatAgent(config=config)
reply = agent.ask("我在东区，想吃不辣、预算低一点的晚饭")
print(reply.text)
```

OpenAI-compatible 厂商：

```python
config = LLMConfig.from_preset(
    "siliconflow",
    model="your-model-id",
)
```

自定义服务：

```python
config = LLMConfig(
    provider="openai_compatible",
    model="vendor/model",
    api_key="...",
    base_url="https://example.com/v1",
)
```

环境变量示例见 `.env.example`。

## 构建 Windows EXE

在 Windows 环境执行：

```powershell
python -m pip install -e ".[gui]"
.\scripts\build_desktop.ps1 -Target windows
```

或者直接使用 Flet：

```powershell
flet build windows src
```

发布到 GitHub Releases 时，建议将最终可下载文件命名为：

```text
hust_helper-windows-x64.exe
```

这样 README 顶部的固定链接始终可以下载最新版本：

```text
https://github.com/Zephyrainzjl/hust_helper/releases/latest/download/hust_helper-windows-x64.exe
```

## 构建 Android APK / AAB

```bash
python -m pip install -e ".[gui]"
bash scripts/build_android.sh apk
```

用于应用商店发布：

```bash
bash scripts/build_android.sh aab
```

构建环境、签名和发布说明见 `docs/building.md`。

## 重新导入更新后的 PDF

```bash
python scripts/extract_hust_eater_pdf.py \
  /path/to/guide.pdf \
  --output src/hust_helper/tools/hust_eater/data

python scripts/validate_data.py
```

导入器会保留原始页面数据和图片。即使某些内容暂时不能自动识别为独立店铺，也不会被静默丢弃。

## 贡献

欢迎补充：

- 新发现的食堂窗口、餐厅、早餐店和夜市；
- 菜品、价格、营业状态和口味变化；
- 图片、菜单和路线说明；
- 搜索规则与界面改进；
- 华科住宿、交通、学习、办事等新工具。

提交贡献时，请尽量注明体验时间、信息来源和图片权利状态。详细规范见 `CONTRIBUTING.md`。

## 许可、数据来源与版权

### 软件代码

`hust_helper` 的软件代码使用 **MIT License**：

```text
Copyright (c) 2026, Jialiu Zeng
```

MIT 许可允许使用、复制、修改、合并、发布和分发软件代码，但必须保留版权和许可声明。

### 项目来源与致谢声明

MIT License 之前附有一段不改变 MIT 法律条款的项目来源说明，用于永久记录：

- 项目源于作者所在课题组在华中科技大学多年的共同饮食经历；
- 初始资料参考某位机械学院师兄编写并提供的《HUSTer 的干饭修养》PDF；
- 内容持续吸收作者每一位朋友的真实饮食体验总结。

### 原始指南与第三方内容

原 PDF 的文字、菜单、地图、平台截图、店铺图片及其他第三方素材**不因被收录到本项目而自动适用 MIT License**。公开再分发、商业发布或上架应用商店前，应核查并取得必要授权。

完整说明见 `DATA_LICENSE.md`。

## 免责声明

餐厅名称、价格、营业时间、菜单、评分、地址和口味可能发生变化。项目内容主要来自历史体验和资料整理，仅供校园生活参考。涉及过敏原、宗教饮食、医疗饮食或食品安全时，请以商家最新信息和个人实际情况为准。

---

<a id="english-version"></a>

# English Version

> [!IMPORTANT]
> ## Project origin and acknowledgements
>
> `hust_helper` is not only a software project. It is a collection of real campus-life experiences accumulated and shared over many years.
>
> 1. **The project grew out of years of study, research, and shared dining experiences within the author's research group at Huazhong University of Science and Technology (HUST).**
> 2. **Its first tool, `hust_eater`, was developed with reference to the PDF guide *HUSTer 的干饭修养——HUST 求学七年的干饭经验*, written and provided by a senior fellow from the HUST School of Mechanical Science and Engineering.** The source PDF is credited to “许少”.
> 3. **Its recommendations, additions, corrections, and taste notes reflect the real dining experiences shared by every friend of the author across the HUST campus and Wuhan.**
>
> We sincerely thank every research-group meal, the senior fellow who compiled and shared the original guide, and every friend who contributed practical advice on where to eat, what to order, and what to keep in mind.

## Prefer not to write code? Download the EXE

<p align="center">
  <a href="https://github.com/Zephyrainzjl/hust_helper/releases/latest/download/hust_helper-windows-x64.exe">
    <strong>⬇️ Download hust_helper for Windows (EXE)</strong>
  </a>
</p>

No Python installation or development environment is required. Download the application and run it directly.

> [!NOTE]
> This permanent URL expects the latest GitHub Release to contain an asset named `hust_helper-windows-x64.exe`. Use this exact filename when publishing the first executable so the link continues to point to the newest release.

## Overview

`hust_helper` is an extensible campus-life assistant for HUST students, alumni, and visitors. It follows the standard Python `src/` layout and can be used as a Python package, a Windows desktop application, or an Android application.

The first tool is located at:

```text
src/hust_helper/tools/hust_eater
```

`hust_eater` transforms the original food guide into a searchable, editable, extensible, and source-traceable data system with:

- Python and Jupyter Notebook APIs;
- command-line search;
- desktop and mobile graphical interfaces;
- searches by venue, dish, area, cuisine, budget, spice level, and meal period;
- image browsing, addition, replacement, hiding, and deletion;
- user-created restaurants, canteen stalls, dishes, and notes;
- OpenAI, SiliconFlow, OpenRouter, DeepSeek, DashScope-compatible, and custom OpenAI-compatible APIs;
- a plugin architecture for future campus-life tools.

## Highlights

### Source-traceable data

The base dataset preserves source pages, paragraphs, images, page numbers, and structured entries from the PDF. Search results can be traced back to source material instead of relying only on secondary summaries.

### Sustainable extension

Base data and user data are separated:

- packaged data remains read-only;
- user additions and edits are stored in a separate overlay;
- software upgrades do not automatically overwrite personal records;
- future tools can cover accommodation, transportation, study, administration, sports, and campus services.

### Multiple search modes

Search by:

- restaurant, canteen, stall, and dish names;
- natural language, such as “a cheap, non-spicy dinner near the east campus”;
- chapter, area, category, meal period, price, spice notes, and tags;
- author visit status, friend recommendations, or public-source recommendations;
- local retrieval or LLM-assisted conversation.

### Multiple platforms

- `pip` installation;
- Python and Notebook API;
- CLI;
- Flet GUI;
- Windows EXE;
- Android APK / AAB.

## Installation

From PyPI or a local wheel:

```bash
python -m pip install hust_helper
```

```bash
python -m pip install ./hust_helper-0.1.0-py3-none-any.whl
```

From source:

```bash
git clone https://github.com/Zephyrainzjl/hust_helper.git
cd hust_helper
python -m pip install -e .
```

Install GUI, Notebook, LLM, and development dependencies:

```bash
python -m pip install -e ".[all,dev]"
```

## Quick start

### Python / Jupyter Notebook

```python
from hust_helper import eater

results = eater.search("non-spicy chicken soup", limit=10)
for item in results:
    print(item.name, item.section_title, item.recommended_items)
```

Composable filters:

```python
near_hust = eater.search(
    "炸鸡",
    chapter="华科周边美食篇",
    visited="visited_by_author",
    limit=5,
)
```

Access source pages and images:

```python
page_10 = eater.page(10)
page_10_markdown = eater.page_markdown(10)
image_bytes = eater.image_bytes("media-p010-01")
```

Create a personal record:

```python
entry = eater.add(
    name="A new discovery",
    chapter_title="User extensions",
    section_title="Around HUST",
    description="Recommended by a friend for group dinners.",
    tags=["friend recommendation", "user extension"],
)
```

See `examples/hust_eater_api.ipynb` for a complete workflow.

### CLI

```bash
hust-helper stats
hust-helper search "热干面" --section 洪山区 --limit 10
hust-helper search "东区 不辣 便宜" --limit 10
hust-helper export --format json --output my_food_catalog.json
hust-helper gui
```

## GUI

Install GUI dependencies:

```bash
python -m pip install -e ".[gui]"
```

Launch the application:

```bash
hust-helper gui
```

or:

```bash
python src/main.py
```

The GUI provides multi-filter search, AI-assisted food discovery, venue details, image management, data editing, provider configuration, and source/license information.

## LLM APIs

Use environment variables for API keys whenever possible. Do not commit secrets to source control.

```python
from hust_helper.llm import FoodChatAgent, LLMConfig

config = LLMConfig.from_preset(
    "openai",
    model="your-model-id",
)

agent = FoodChatAgent(config=config)
reply = agent.ask("I am near the east campus and want a cheap, non-spicy dinner.")
print(reply.text)
```

OpenAI-compatible provider:

```python
config = LLMConfig.from_preset(
    "siliconflow",
    model="your-model-id",
)
```

Custom endpoint:

```python
config = LLMConfig(
    provider="openai_compatible",
    model="vendor/model",
    api_key="...",
    base_url="https://example.com/v1",
)
```

See `.env.example` for environment-variable examples.

## Build the Windows EXE

Run on Windows:

```powershell
python -m pip install -e ".[gui]"
.\scripts\build_desktop.ps1 -Target windows
```

or:

```powershell
flet build windows src
```

When publishing the executable to GitHub Releases, use:

```text
hust_helper-windows-x64.exe
```

The permanent latest-release download URL is:

```text
https://github.com/Zephyrainzjl/hust_helper/releases/latest/download/hust_helper-windows-x64.exe
```

## Build Android APK / AAB

```bash
python -m pip install -e ".[gui]"
bash scripts/build_android.sh apk
```

For application-store distribution:

```bash
bash scripts/build_android.sh aab
```

See `docs/building.md` for toolchain, signing, and release details.

## Re-import an updated PDF

```bash
python scripts/extract_hust_eater_pdf.py \
  /path/to/guide.pdf \
  --output src/hust_helper/tools/hust_eater/data

python scripts/validate_data.py
```

Raw page records and media remain preserved even when a passage cannot yet be converted into an independent structured venue entry.

## Contributing

Contributions may include new canteen stalls, restaurants, breakfast shops, night markets, dishes, prices, operating-status updates, images, directions, search improvements, interface improvements, or entirely new HUST campus tools.

Please record the approximate experience date, information source, and image-rights status whenever possible. See `CONTRIBUTING.md` for details.

## License, source data, and copyright

### Software code

The `hust_helper` software code is released under the **MIT License**:

```text
Copyright (c) 2026, Jialiu Zeng
```

### Origin and acknowledgement notice

An informational origin notice appears before the MIT terms without modifying the legal effect of the MIT License. It permanently records that:

- the project grew out of years of dining experiences within the author's HUST research group;
- the initial guide was developed with reference to a PDF prepared and provided by a senior fellow from the School of Mechanical Science and Engineering;
- the project continues to incorporate the real dining experiences of every friend of the author.

### Source guide and third-party content

Text, menus, maps, platform screenshots, store images, and other third-party materials from the source PDF are **not automatically relicensed under MIT merely because they are included in this repository**. Necessary permissions should be reviewed before public redistribution, commercial release, or app-store publication.

See `DATA_LICENSE.md` for the full notice.

## Disclaimer

Restaurant names, prices, opening hours, menus, ratings, addresses, and food quality may change. This project records historical experiences and compiled information for campus-life reference only. For allergens, religious dietary requirements, medical diets, and food safety, rely on current merchant information and personal circumstances.
