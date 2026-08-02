from __future__ import annotations

import json
import os
import random
import threading
from typing import Any, Callable

try:
    import flet as ft
except ImportError as exc:
    raise ImportError('Install GUI support with: pip install "hust_helper[gui]"') from exc

from hust_helper.llm import FoodChatAgent, LLMConfig
from hust_helper.realtime import (
    MCPHub,
    MCPServerConfig,
    RealtimeFoodAgent,
    parse_server_configs,
)
from hust_helper.tools.hust_eater.service import HustEaterService

from .compat import (
    button,
    color,
    icon,
    image_from_bytes,
    padding_symmetric,
    run_app,
)


def _dropdown_option(value: str, label: str | None = None):
    old_option = getattr(getattr(ft, "dropdown", None), "Option", None)
    if old_option is not None:
        try:
            return old_option(value, text=label or value)
        except TypeError:
            return old_option(value)
    new_option = getattr(ft, "DropdownOption", None)
    if new_option is not None:
        try:
            return new_option(key=value, text=label or value)
        except TypeError:
            return new_option(value=value, label=label or value)
    return value


def _scroll_auto():
    mode = getattr(ft, "ScrollMode", None)
    return getattr(mode, "AUTO", "auto") if mode else "auto"


def _scroll_always():
    mode = getattr(ft, "ScrollMode", None)
    return getattr(mode, "ALWAYS", "always") if mode else "always"


def _bold():
    weight = getattr(ft, "FontWeight", None)
    return getattr(weight, "BOLD", "bold") if weight else "bold"


def _medium():
    weight = getattr(ft, "FontWeight", None)
    return getattr(weight, "W_500", "w500") if weight else "w500"


def _card(content, *, padding: int = 16, bgcolor: str | None = None, expand: bool = False):
    return ft.Container(
        content=content,
        padding=padding,
        bgcolor=bgcolor,
        border_radius=16,
        expand=expand,
    )


def _metric(ft_module, value: str, label: str, icon_name: str):
    return _card(
        ft.Row(
            [
                ft.Icon(icon(ft_module, icon_name), size=25),
                ft.Column(
                    [
                        ft.Text(value, size=22, weight=_bold()),
                        ft.Text(label, size=12),
                    ],
                    spacing=1,
                ),
            ],
            spacing=12,
        ),
        padding=14,
        bgcolor=color(ft_module, "SURFACE_CONTAINER_LOW", "#F6F7FB"),
    )


def _parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.replace("，", ",").split(",") if item.strip()]


def main(page: ft.Page) -> None:
    page.title = "HUST Helper · 华科生活助手"
    page.padding = 0

    # Flet 0.85 raises a layout error when ResponsiveRow receives unbounded
    # horizontal constraints. Explicitly stretch root controls so every view
    # receives a finite window width.
    cross_axis = getattr(ft, "CrossAxisAlignment", None)
    if cross_axis is not None:
        page.horizontal_alignment = getattr(cross_axis, "STRETCH", None)
    # The root page must remain height-bounded. Each workspace view owns
    # its scrolling; otherwise an expanded child inside a scrollable Page
    # can be laid out with zero height and appear completely blank.
    page.scroll = None
    theme_mode = getattr(ft, "ThemeMode", None)
    if theme_mode is not None:
        page.theme_mode = getattr(theme_mode, "SYSTEM", None)
    theme_cls = getattr(ft, "Theme", None)
    if theme_cls is not None:
        try:
            page.theme = theme_cls(color_scheme_seed="#E64A19", use_material3=True)
        except TypeError:
            try:
                page.theme = theme_cls(color_scheme_seed="#E64A19")
            except TypeError:
                pass

    service = HustEaterService()
    catalog = service.repository.catalog()
    entries = service.entries()
    counts = catalog["counts"]
    chapters = sorted({entry.chapter_title for entry in entries if entry.chapter_title})
    sections = sorted({entry.section_title for entry in entries if entry.section_title})
    venue_types = sorted({entry.venue_type for entry in entries if entry.venue_type})
    categories = sorted({entry.category for entry in entries if entry.category})
    selected_id: dict[str, str | None] = {"value": None}

    primary_container = color(ft, "PRIMARY_CONTAINER", "#FFE2D6")
    surface = color(ft, "SURFACE", "#FFFFFF")
    surface_low = color(ft, "SURFACE_CONTAINER_LOW", "#F6F7FB")
    surface_panel = color(ft, "SURFACE_CONTAINER", "#2A211E")
    surface_high = color(ft, "SURFACE_CONTAINER_HIGH", "#ECEEF4")
    error_container = color(ft, "ERROR_CONTAINER", "#FFDAD6")

    # ==================================================================
    # Discover / local structured search
    # ==================================================================
    search_status = ft.Text("正在准备本地指南…", size=12)
    search_query = ft.TextField(
        label="搜索店名、菜品、区域、口味或原文描述",
        hint_text="例如：不辣的鸡汤、东区早餐、便宜的火锅",
        autofocus=True,
    )
    search_chapter = ft.Dropdown(
        label="章节",
        options=[_dropdown_option("", "全部章节")]
        + [_dropdown_option(item) for item in chapters],
        width=220,
    )
    search_section = ft.Dropdown(
        label="区域 / 小节",
        options=[_dropdown_option("", "全部区域")]
        + [_dropdown_option(item) for item in sections],
        width=190,
    )
    search_venue = ft.Dropdown(
        label="场景",
        options=[_dropdown_option("", "全部场景")]
        + [_dropdown_option(item) for item in venue_types],
        width=175,
    )
    search_category = ft.Dropdown(
        label="菜系 / 类型",
        options=[_dropdown_option("", "全部类型")]
        + [_dropdown_option(item) for item in categories],
        width=180,
    )
    search_meal = ft.Dropdown(
        label="时段",
        options=[
            _dropdown_option("", "全部时段"),
            _dropdown_option("breakfast", "早餐 / 过早"),
            _dropdown_option("lunch", "午餐"),
            _dropdown_option("dinner", "晚餐"),
            _dropdown_option("late_day", "夜市 / 宵夜"),
        ],
        width=175,
    )
    search_visit = ft.Dropdown(
        label="体验来源",
        options=[
            _dropdown_option("", "全部来源"),
            _dropdown_option("visited_by_author", "作者亲自去过"),
            _dropdown_option("not_visited_by_author", "外部推荐 / 未去过"),
            _dropdown_option("unspecified", "未明确说明"),
        ],
        width=190,
    )
    search_sort = ft.Dropdown(
        label="排序",
        value="relevance",
        options=[
            _dropdown_option("relevance", "相关度"),
            _dropdown_option("recommendations", "推荐菜数量"),
            _dropdown_option("visited", "作者体验优先"),
            _dropdown_option("source_page", "PDF 页码"),
            _dropdown_option("name", "名称"),
        ],
        width=175,
    )
    search_mode = ft.Dropdown(
        label="匹配方式",
        value="smart",
        options=[
            _dropdown_option("smart", "智能模糊匹配"),
            _dropdown_option("all", "包含全部关键词"),
            _dropdown_option("exact", "包含完整短语"),
        ],
        width=185,
    )
    search_limit = ft.Dropdown(
        label="结果数",
        value="40",
        options=[_dropdown_option(value) for value in ("20", "40", "80", "144")],
        width=120,
    )
    search_tags = ft.TextField(label="标签（逗号分隔）", width=230)
    search_excludes = ft.TextField(label="排除词（逗号分隔）", width=230)
    recommended_only = ft.Checkbox(label="只看明确推荐")
    avoid_spicy = ft.Checkbox(label="尽量避辣")
    with_images = ft.Checkbox(label="有图片")
    with_price = ft.Checkbox(label="有价格提示")
    external_only = ft.Checkbox(label="只看外部推荐")
    min_recommendations = ft.Dropdown(
        label="最少推荐菜",
        value="0",
        options=[_dropdown_option(str(value)) for value in (0, 1, 3, 5)],
        width=140,
    )

    result_column = ft.Column(spacing=10)
    detail_column = ft.Column(spacing=10)
    last_results: dict[str, list[Any]] = {"value": []}

    def _visit_label(status: str) -> str:
        return {
            "visited_by_author": "作者亲测",
            "not_visited_by_author": "外部推荐",
            "unspecified": "来源未明确",
        }.get(status, status)

    def show_entry(entry) -> None:
        selected_id["value"] = entry.id
        detail_column.controls.clear()
        detail_column.controls.extend(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(entry.name, size=26, weight=_bold()),
                                ft.Text(
                                    f"{entry.chapter_title}  ·  {entry.section_title}",
                                    size=13,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        _card(
                            ft.Text(_visit_label(entry.author_visit_status), size=12, weight=_medium()),
                            padding=8,
                            bgcolor=primary_container,
                        ),
                    ]
                ),
                ft.Text(
                    f"类型：{entry.category or entry.venue_type or '未分类'}    "
                    f"来源页：{', '.join(map(str, entry.source_pages)) or '未知'}",
                    size=12,
                ),
            ]
        )
        if entry.recommended_items:
            detail_column.controls.append(
                _card(
                    ft.Column(
                        [
                            ft.Text("推荐吃什么", weight=_bold()),
                            ft.Text("、".join(entry.recommended_items), selectable=True),
                        ],
                        spacing=6,
                    ),
                    bgcolor=primary_container,
                )
            )
        if entry.spice_notes or entry.price_notes:
            detail_column.controls.append(
                ft.Row(
                    [
                        _card(
                            ft.Column(
                                [
                                    ft.Text("辣度提示", weight=_bold()),
                                    ft.Text("；".join(entry.spice_notes) or "无"),
                                ],
                                spacing=4,
                            ),
                            bgcolor=surface_low,
                            expand=True,
                        ),
                        _card(
                            ft.Column(
                                [
                                    ft.Text("价格 / 性价比", weight=_bold()),
                                    ft.Text("；".join(entry.price_notes) or "无"),
                                ],
                                spacing=4,
                            ),
                            bgcolor=surface_low,
                            expand=True,
                        ),
                    ],
                    wrap=True,
                )
            )
        detail_column.controls.append(ft.Text(entry.description or "（原文无补充描述）", selectable=True))
        if entry.tags:
            detail_column.controls.append(ft.Text("标签：" + " · ".join(entry.tags), size=12))
        if entry.media_ids:
            detail_column.controls.append(ft.Text("原 PDF 图片", weight=_bold()))

            # Follow Flet's documented image-gallery layout: a single,
            # non-wrapping, horizontally scrollable Row. A wrapping Row inside
            # the vertically scrolling workspace can receive unstable height
            # constraints in the desktop renderer and become a large grey
            # ErrorWidget.
            gallery = ft.Row(
                wrap=False,
                scroll=_scroll_always(),
                spacing=10,
                height=215,
            )
            for media_id in entry.media_ids[:12]:
                try:
                    image_data = service.repository.image_bytes(media_id)
                    record = service.repository.media_record(media_id)
                    caption = record.get("caption") or media_id

                    gallery.controls.append(
                        ft.Container(
                            width=250,
                            height=205,
                            content=_card(
                                ft.Column(
                                    [
                                        image_from_bytes(
                                            ft,
                                            image_data,
                                            width=230,
                                            height=155,
                                        ),
                                        ft.Text(
                                            caption,
                                            size=11,
                                            width=230,
                                            max_lines=2,
                                        ),
                                    ],
                                    spacing=6,
                                ),
                                padding=8,
                                bgcolor=surface_low,
                            ),
                        )
                    )
                except Exception as exc:
                    gallery.controls.append(
                        ft.Container(
                            width=250,
                            height=205,
                            content=_card(
                                ft.Column(
                                    [
                                        ft.Icon(icon(ft, "BROKEN_IMAGE"), size=36),
                                        ft.Text(
                                            f"{media_id}\n{type(exc).__name__}: {exc}",
                                            size=11,
                                            selectable=True,
                                        ),
                                    ],
                                    spacing=8,
                                ),
                                padding=12,
                                bgcolor=error_container,
                            ),
                        )
                    )
            detail_column.controls.append(gallery)
        page.update()

    def result_card(result):
        entry = result.entry
        dishes = "、".join(entry.recommended_items[:4]) or "查看原文介绍"
        subtitle = (
            f"{entry.section_title} · {_visit_label(entry.author_visit_status)} · "
            f"PDF {','.join(map(str, entry.source_pages))}\n{dishes}"
        )
        tile_cls = getattr(ft, "ListTile", None)
        if tile_cls is not None:
            tile = tile_cls(
                leading=ft.Icon(icon(ft, "RESTAURANT")),
                title=ft.Text(entry.name, weight=_medium()),
                subtitle=ft.Text(subtitle, max_lines=3),
                trailing=ft.Text(f"{result.score:.1f}", size=12),
                on_click=lambda _e, item=entry: show_entry(item),
            )
            return _card(tile, padding=4, bgcolor=surface_low)
        return button(ft, entry.name, on_click=lambda _e, item=entry: show_entry(item))

    def do_search(_event=None) -> None:
        result_column.controls.clear()
        results = service.search(
            search_query.value or "",
            chapter=search_chapter.value or None,
            section=search_section.value or None,
            category=search_category.value or None,
            venue_type=search_venue.value or None,
            meal_period=search_meal.value or None,
            visited=search_visit.value or None,
            has_images=True if with_images.value else None,
            avoid_spicy=bool(avoid_spicy.value),
            recommended_only=bool(recommended_only.value),
            has_price_notes=True if with_price.value else None,
            external_recommended=True if external_only.value else None,
            min_recommendations=int(min_recommendations.value or 0),
            tags=_parse_csv(search_tags.value),
            exclude_terms=_parse_csv(search_excludes.value),
            query_mode=search_mode.value or "smart",
            sort_by=search_sort.value or "relevance",
            limit=int(search_limit.value or 40),
        )
        last_results["value"] = results
        result_column.controls.extend(result_card(item) for item in results)
        search_status.value = (
            f"找到 {len(results)} 条 · 当前显示 {search_sort.value or 'relevance'} 排序 · "
            f"本地结构化记录共 {len(service.entries())} 条"
        )
        if results and selected_id["value"] is None:
            show_entry(results[0].entry)
        else:
            page.update()

    def clear_search(_event=None) -> None:
        search_query.value = ""
        for dropdown in (
            search_chapter,
            search_section,
            search_venue,
            search_category,
            search_meal,
            search_visit,
        ):
            dropdown.value = ""
        search_sort.value = "relevance"
        search_mode.value = "smart"
        search_limit.value = "40"
        search_tags.value = ""
        search_excludes.value = ""
        min_recommendations.value = "0"
        for checkbox in (recommended_only, avoid_spicy, with_images, with_price, external_only):
            checkbox.value = False
        do_search()

    def random_pick(_event=None) -> None:
        results = last_results["value"]
        if not results:
            do_search()
            results = last_results["value"]
        if results:
            show_entry(random.choice(results).entry)
            search_status.value = "已从当前筛选结果中随机选择一家。"
            page.update()

    def preset(*pairs: tuple[Any, Any]):
        def handler(_event=None):
            for field, value in pairs:
                field.value = value
            do_search()

        return handler

    search_query.on_submit = do_search
    discover_view = ft.ListView(
        [
            _card(
                ft.Column(
                    [
                        ft.Column(
                            [
                                ft.Text("今天吃什么？", size=31, weight=_bold()),
                                ft.Text(
                                    "从华科食堂、学校周边、武汉过早、全城餐馆和夜市中快速筛选。",
                                    size=14,
                                ),
                                ft.Row(
                                    [
                                        button(ft, "早餐", on_click=preset((search_meal, "breakfast"))),
                                        button(
                                            ft,
                                            "校内食堂",
                                            on_click=preset((search_venue, "campus_dining")),
                                        ),
                                        button(ft, "作者亲测", on_click=preset((search_visit, "visited_by_author"))),
                                        button(ft, "尽量不辣", on_click=preset((avoid_spicy, True))),
                                        button(ft, "夜市", on_click=preset((search_venue, "night_market"))),
                                    ],
                                    wrap=True,
                                ),
                            ],
                            spacing=10,
                        ),
                        ft.Row(
                            [
                                ft.Container(
                                    _metric(ft, str(counts["entries"]), "结构化地点", "STORE"),
                                    width=220,
                                ),
                                ft.Container(
                                    _metric(ft, str(counts["images"]), "原始图片", "IMAGE"),
                                    width=220,
                                ),
                                ft.Container(
                                    _metric(ft, str(counts["chapters"]), "主题章节", "MENU_BOOK"),
                                    width=220,
                                ),
                                ft.Container(
                                    _metric(ft, "49", "PDF 页面", "PICTURE_AS_PDF"),
                                    width=220,
                                ),
                            ],
                            wrap=True,
                            spacing=10,
                            run_spacing=10,
                        ),
                    ],
                    spacing=16,
                ),
                padding=22,
                bgcolor=primary_container,
            ),
            _card(
                ft.Column(
                    [
                        search_query,
                        ft.Row(
                            [
                                button(ft, "搜索", icon=icon(ft, "SEARCH"), on_click=do_search),
                                button(ft, "随机一家", icon=icon(ft, "CASINO"), on_click=random_pick),
                                button(ft, "清空", icon=icon(ft, "RESTART_ALT"), on_click=clear_search),
                            ],
                            wrap=True,
                            spacing=10,
                            run_spacing=10,
                        ),
                    ],
                    spacing=10,
                ),
                bgcolor=surface_panel,
            ),
            _card(
                ft.Column(
                    [
                        ft.Text("筛选与排序", weight=_bold()),
                        ft.Row(
                            [
                                search_chapter,
                                search_section,
                                search_venue,
                                search_category,
                                search_meal,
                                search_visit,
                            ],
                            wrap=True,
                        ),
                        ft.Row(
                            [
                                search_mode,
                                search_sort,
                                search_limit,
                                min_recommendations,
                                search_tags,
                                search_excludes,
                            ],
                            wrap=True,
                        ),
                        ft.Row(
                            [recommended_only, avoid_spicy, with_images, with_price, external_only],
                            wrap=True,
                        ),
                    ],
                    spacing=10,
                ),
                bgcolor=surface_low,
            ),
            search_status,
            ft.Row(
                [
                    ft.Container(
                        content=_card(
                            ft.Column(
                                [ft.Text("搜索结果", size=18, weight=_bold()), result_column],
                                spacing=10,
                            ),
                            bgcolor=surface,
                        ),
                        expand=5,
                    ),
                    ft.Container(
                        content=_card(
                            ft.Column(
                                [ft.Text("地点详情", size=18, weight=_bold()), detail_column],
                                spacing=10,
                            ),
                            bgcolor=surface,
                        ),
                        expand=7,
                    ),
                ],
                spacing=14,
                vertical_alignment=getattr(
                    getattr(ft, "CrossAxisAlignment", None),
                    "START",
                    None,
                ),
            ),
        ],
        spacing=14,
        expand=True,
        padding=0,
        build_controls_on_demand=False,
    )

    # ==================================================================
    # Local PDF chat (independent from live MCP)
    # ==================================================================
    local_provider = ft.Dropdown(
        label="LLM 提供商",
        value="openai",
        options=[
            _dropdown_option(x)
            for x in ["openai", "siliconflow", "openrouter", "deepseek", "dashscope", "custom", "litellm"]
        ],
        width=175,
    )
    local_model = ft.TextField(
        label="模型 ID",
        value=os.environ.get("HUST_HELPER_MODEL", "gpt-5.6"),
        width=260,
    )
    local_base_url = ft.TextField(label="自定义 Base URL（预设可留空）", width=315)
    local_api_key = ft.TextField(
        label="API Key（仅当前会话）",
        password=True,
        can_reveal_password=True,
        width=300,
    )
    local_chat_input = ft.TextField(
        label="根据内置指南问我",
        hint_text="例如：华科附近适合三个人、不太辣、预算友好的店",
        multiline=True,
        min_lines=2,
        max_lines=5,
    )
    local_chat_log = ft.Column(
        controls=[ft.Text("对话内容会显示在这里。", size=12)],
        spacing=10,
        scroll=_scroll_auto(),
    )
    local_chat_status = ft.Text("没有 API Key 时，使用本地关键词检索，不调用网络模型。", size=12)
    local_agent_holder: dict[str, Any] = {"signature": None, "agent": None}

    def append_chat(log: ft.Column, role: str, text: str, *, error: bool = False) -> None:
        log.controls.append(
            _card(
                ft.Column(
                    [
                        ft.Text(role, weight=_bold()),
                        ft.Text(text, selectable=True),
                    ],
                    spacing=6,
                ),
                bgcolor=error_container if error else (primary_container if role == "你" else surface_low),
            )
        )

    def reset_local_chat(_event=None) -> None:
        agent = local_agent_holder.get("agent")
        if agent is not None:
            agent.reset()
        local_chat_log.controls[:] = [ft.Text("对话内容会显示在这里。", size=12)]
        local_chat_status.value = "本地指南对话已重置；模型配置保持不变。"
        page.update()

    def send_local_chat(_event=None, preset_text: str | None = None) -> None:
        question = (preset_text or local_chat_input.value or "").strip()
        if not question:
            return
        if len(local_chat_log.controls) == 1:
            local_chat_log.controls.clear()
        append_chat(local_chat_log, "你", question)
        local_chat_input.value = ""
        local_chat_status.value = "正在查询内置指南并整理答案…"
        page.update()

        def worker() -> None:
            try:
                signature = (
                    local_provider.value,
                    local_model.value,
                    local_base_url.value,
                    local_api_key.value,
                )
                if local_agent_holder["signature"] != signature:
                    config = LLMConfig.from_preset(
                        local_provider.value or "openai",
                        model=local_model.value or None,
                        api_key=local_api_key.value or None,
                        base_url=local_base_url.value or None,
                    )
                    local_agent_holder["agent"] = FoodChatAgent(config=config, service=service)
                    local_agent_holder["signature"] = signature
                reply = local_agent_holder["agent"].ask(question)
                append_chat(local_chat_log, "本地指南助手", reply.text)
                local_chat_status.value = f"引用 {len(reply.sources)} 个本地指南条目。"
            except Exception as exc:
                append_chat(local_chat_log, "错误", str(exc), error=True)
                local_chat_status.value = "调用失败，请检查模型、Key、Base URL 与网络。"
            page.update()

        threading.Thread(target=worker, daemon=True).start()

    local_chat_input.on_submit = send_local_chat
    local_chat_view = ft.ListView(
        [
            _card(
                ft.Column(
                    [
                        ft.Text("内置指南 AI", size=28, weight=_bold()),
                        ft.Text(
                            "只使用项目内置 PDF 数据，不查询实时营业、路线或平台评分。适合总结师兄和朋友们的长期饮食体验。"
                        ),
                        ft.Row(
                            [local_provider, local_model, local_base_url, local_api_key],
                            wrap=True,
                        ),
                    ],
                    spacing=12,
                ),
                bgcolor=primary_container,
            ),
            ft.Row(
                [
                    button(
                        ft,
                        "给我推荐不辣的",
                        on_click=lambda _e: send_local_chat(preset_text="根据内置指南，推荐几家不太辣的店，并说明作者是否去过。"),
                    ),
                    button(
                        ft,
                        "适合聚餐",
                        on_click=lambda _e: send_local_chat(preset_text="根据内置指南，推荐适合三到五个人聚餐的店。"),
                    ),
                    button(
                        ft,
                        "华科早餐",
                        on_click=lambda _e: send_local_chat(preset_text="根据内置指南，华科附近过早最值得吃什么？"),
                    ),
                    button(ft, "重置对话", icon=icon(ft, "RESTART_ALT"), on_click=reset_local_chat),
                ],
                wrap=True,
            ),
            ft.Container(
                content=local_chat_log,
                height=300,
                padding=16,
                bgcolor=surface_panel,
                border_radius=16,
            ),
            _card(
                ft.Column(
                    [
                        local_chat_input,
                        ft.Row(
                            [
                                button(
                                    ft,
                                    "发送",
                                    icon=icon(ft, "SEND"),
                                    on_click=send_local_chat,
                                )
                            ],
                            spacing=10,
                        ),
                    ],
                    spacing=10,
                ),
                bgcolor=surface_panel,
            ),
            local_chat_status,
        ],
        spacing=14,
        expand=True,
        padding=0,
        build_controls_on_demand=False,
    )

    # ==================================================================
    # Live MCP chat — completely independent from local PDF agent
    # ==================================================================
    live_provider = ft.Dropdown(
        label="LLM 提供商",
        value="siliconflow",
        options=[
            _dropdown_option(x)
            for x in ["openai", "siliconflow", "openrouter", "deepseek", "dashscope", "custom", "litellm"]
        ],
        width=175,
    )
    live_model = ft.TextField(
        label="模型 ID",
        value=os.environ.get("HUST_HELPER_LIVE_MODEL", ""),
        hint_text="选择支持 tools/function calling 的对话模型",
        width=285,
    )
    live_base_url = ft.TextField(label="LLM Base URL（预设可留空）", width=300)
    live_api_key = ft.TextField(
        label="LLM API Key",
        password=True,
        can_reveal_password=True,
        width=285,
    )
    amap_key = ft.TextField(
        label="高德 Web 服务 Key / MCP Key",
        password=True,
        can_reveal_password=True,
        width=310,
    )
    live_city = ft.TextField(label="默认城市", value="武汉", width=150)
    live_center = ft.TextField(
        label="默认中心点",
        value="华中科技大学",
        hint_text="地名或经纬度",
        width=220,
    )
    live_radius = ft.Dropdown(
        label="默认半径",
        value="3000",
        options=[
            _dropdown_option("1000", "1 km"),
            _dropdown_option("3000", "3 km"),
            _dropdown_option("5000", "5 km"),
            _dropdown_option("10000", "10 km"),
        ],
        width=135,
    )
    extra_mcp = ft.TextField(
        label="额外 MCP servers（JSON 数组，可接已授权的美团 / 大众点评 / 自建服务）",
        value="[]",
        multiline=True,
        min_lines=4,
        max_lines=10,
    )
    live_chat_input = ft.TextField(
        label="实时找吃的",
        hint_text="例如：华科东门 3 公里内，现在营业、评分较高、适合两个人的清淡餐馆",
        multiline=True,
        min_lines=2,
        max_lines=5,
    )
    live_chat_log = ft.Column(
        controls=[ft.Text("实时 MCP 查询结果会显示在这里。", size=12)],
        spacing=10,
        scroll=_scroll_auto(),
    )
    live_status = ft.Text("尚未连接 MCP。高德可直接使用官方 MCP；其他平台需要合法授权的连接器。", size=12)
    live_tools = ft.Text("可用工具：尚未检测", selectable=True, size=12)
    live_agent_holder: dict[str, Any] = {"signature": None, "agent": None, "hub": None}

    def load_mcp_template(_event=None) -> None:
        extra_mcp.value = json.dumps(
            [
                {
                    "name": "meituan-authorized",
                    "transport": "streamable_http",
                    "url": "${MEITUAN_MCP_URL}",
                    "headers": {"Authorization": "Bearer ${MEITUAN_MCP_TOKEN}"},
                    "enabled": False,
                },
                {
                    "name": "dianping-authorized",
                    "transport": "streamable_http",
                    "url": "${DIANPING_MCP_URL}",
                    "headers": {"Authorization": "Bearer ${DIANPING_MCP_TOKEN}"},
                    "enabled": False,
                },
            ],
            ensure_ascii=False,
            indent=2,
        )
        page.update()

    def build_live_stack() -> tuple[RealtimeFoodAgent, MCPHub, tuple[Any, ...]]:
        servers = []
        if (amap_key.value or "").strip():
            servers.append(MCPServerConfig.amap(amap_key.value))
        servers.extend(parse_server_configs(extra_mcp.value or "[]"))
        enabled_servers = [server for server in servers if server.enabled]
        if not enabled_servers:
            raise ValueError("至少配置一个启用的 MCP server；推荐先填写高德 Key。")
        config = LLMConfig.from_preset(
            live_provider.value or "siliconflow",
            model=live_model.value or None,
            api_key=live_api_key.value or None,
            base_url=live_base_url.value or None,
        )
        signature = (
            live_provider.value,
            live_model.value,
            live_base_url.value,
            live_api_key.value,
            amap_key.value,
            extra_mcp.value,
        )
        if live_agent_holder["signature"] != signature:
            hub = MCPHub(enabled_servers)
            live_agent_holder["hub"] = hub
            live_agent_holder["agent"] = RealtimeFoodAgent(config=config, hub=hub)
            live_agent_holder["signature"] = signature
        return live_agent_holder["agent"], live_agent_holder["hub"], signature

    def test_mcp(_event=None) -> None:
        live_status.value = "正在连接 MCP servers 并读取工具列表…"
        page.update()

        def worker() -> None:
            try:
                _agent, hub, _signature = build_live_stack()
                descriptors, statuses = hub.list_tools_sync(refresh=True)
                live_tools.value = "可用工具：\n" + "\n".join(
                    f"• {item.server_name} / {item.name}" for item in descriptors
                )
                live_status.value = "；".join(
                    f"{item.name}: {'已连接' if item.connected else '失败'}"
                    f"（{item.tool_count} tools）"
                    + (f" {item.error}" if item.error else "")
                    for item in statuses
                )
            except Exception as exc:
                live_status.value = f"MCP 连接测试失败：{exc}"
                live_tools.value = "可用工具：0"
            page.update()

        threading.Thread(target=worker, daemon=True).start()

    def reset_live_chat(_event=None) -> None:
        agent = live_agent_holder.get("agent")
        if agent is not None:
            agent.reset()
        live_chat_log.controls[:] = [ft.Text("实时 MCP 查询结果会显示在这里。", size=12)]
        live_status.value = "实时 MCP 对话已重置；连接配置保持不变。"
        page.update()

    def send_live_chat(_event=None, preset_text: str | None = None) -> None:
        question = (preset_text or live_chat_input.value or "").strip()
        if not question:
            return
        if len(live_chat_log.controls) == 1:
            live_chat_log.controls.clear()
        append_chat(live_chat_log, "你", question)
        live_chat_input.value = ""
        live_status.value = "正在让模型调用实时 MCP 工具…"
        page.update()

        def worker() -> None:
            try:
                agent, _hub, _signature = build_live_stack()
                context = (
                    f"默认城市：{live_city.value or '武汉'}；"
                    f"默认中心点：{live_center.value or '华中科技大学'}；"
                    f"默认搜索半径：{live_radius.value or '3000'} 米。\n"
                )
                reply = agent.ask(context + "用户问题：" + question)
                append_chat(live_chat_log, "实时 MCP 助手", reply.text)
                source_text = "、".join(
                    f"{item['server']}/{item['tool']}" for item in reply.sources
                ) or "无成功工具来源"
                live_status.value = f"本轮工具来源：{source_text}"
                if reply.server_status:
                    live_tools.value = "连接状态：\n" + "\n".join(
                        f"• {item['name']}: {'正常' if item['connected'] else '失败'}"
                        + (f"，{item['tool_count']} tools" if item.get("tool_count") else "")
                        + (f"，{item['error']}" if item.get("error") else "")
                        for item in reply.server_status
                    )
            except Exception as exc:
                append_chat(live_chat_log, "错误", str(exc), error=True)
                live_status.value = "实时查询失败，请检查 LLM、MCP Key、授权连接器和网络。"
            page.update()

        threading.Thread(target=worker, daemon=True).start()

    live_chat_input.on_submit = send_live_chat
    live_chat_view = ft.ListView(
        [
            _card(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text("实时 MCP 探店", size=28, weight=_bold()),
                                        ft.Text(
                                            "独立于内置 PDF：通过高德或你已获授权的平台连接器查询高鲜度地点、周边、路线与营业字段。"
                                        ),
                                    ],
                                    expand=True,
                                ),
                                _card(ft.Text("LIVE", weight=_bold()), padding=10, bgcolor=surface),
                            ]
                        ),
                        ft.Row([live_provider, live_model, live_base_url, live_api_key], wrap=True),
                        ft.Row([amap_key, live_city, live_center, live_radius], wrap=True),
                    ],
                    spacing=12,
                ),
                bgcolor=primary_container,
            ),
            _card(
                ft.Column(
                    [
                        ft.Column(
                            [
                                ft.Text("MCP 数据源", size=18, weight=_bold()),
                                ft.Row(
                                    [
                                        button(
                                            ft,
                                            "载入授权连接器模板",
                                            on_click=load_mcp_template,
                                        ),
                                        button(
                                            ft,
                                            "测试连接",
                                            icon=icon(ft, "CLOUD_SYNC"),
                                            on_click=test_mcp,
                                        ),
                                    ],
                                    wrap=True,
                                    spacing=10,
                                    run_spacing=10,
                                ),
                            ],
                            spacing=8,
                        ),
                        extra_mcp,
                        ft.Text(
                            "提示：模板不会绕过平台授权。将 enabled 改为 true 前，必须填写你依法获得的 MCP URL 和 Token。",
                            size=12,
                        ),
                        live_tools,
                    ],
                    spacing=8,
                ),
                bgcolor=surface_low,
            ),
            ft.Row(
                [
                    button(
                        ft,
                        "现在营业",
                        on_click=lambda _e: send_live_chat(
                            preset_text="搜索默认中心点附近现在营业的餐馆，优先给出工具明确返回营业状态的结果。"
                        ),
                    ),
                    button(
                        ft,
                        "步行可达",
                        on_click=lambda _e: send_live_chat(
                            preset_text="找默认中心点附近适合步行前往的餐馆，并给出距离或路线信息。"
                        ),
                    ),
                    button(
                        ft,
                        "清淡聚餐",
                        on_click=lambda _e: send_live_chat(
                            preset_text="找附近适合两到四人、口味偏清淡的餐馆；仅在工具有数据时写评分和营业状态。"
                        ),
                    ),
                    button(ft, "重置实时对话", icon=icon(ft, "RESTART_ALT"), on_click=reset_live_chat),
                ],
                wrap=True,
            ),
            ft.Container(
                content=live_chat_log,
                height=300,
                padding=16,
                bgcolor=surface_panel,
                border_radius=16,
            ),
            _card(
                ft.Column(
                    [
                        live_chat_input,
                        ft.Row(
                            [
                                button(
                                    ft,
                                    "实时查询",
                                    icon=icon(ft, "TRAVEL_EXPLORE"),
                                    on_click=send_live_chat,
                                )
                            ],
                            spacing=10,
                        ),
                    ],
                    spacing=10,
                ),
                bgcolor=surface_panel,
            ),
            live_status,
        ],
        spacing=14,
        expand=True,
        padding=0,
        build_controls_on_demand=False,
    )

    # ==================================================================
    # Data / image editor
    # ==================================================================
    editor_id = ft.TextField(label="记录 ID（更新、删除和图片操作）")
    editor_name = ft.TextField(label="名称")
    editor_chapter = ft.TextField(label="章节", value="用户扩展")
    editor_section = ft.TextField(label="区域 / 小节", value="用户扩展")
    editor_category = ft.TextField(label="类型")
    editor_description = ft.TextField(label="描述", multiline=True, min_lines=5, max_lines=12)
    media_id = ft.TextField(label="图片 Media ID")
    media_path = ft.TextField(label="本地图片路径（添加 / 替换）")
    media_caption = ft.TextField(label="图片说明")
    media_list = ft.Text("当前图片：无", selectable=True)
    editor_status = ft.Text("所有修改进入用户目录 overlay，不改动包内原始数据。")

    def fill_selected(_event=None) -> None:
        if not selected_id["value"]:
            editor_status.value = "请先在搜索页选择记录。"
            page.update()
            return
        entry = service.get(selected_id["value"])
        editor_id.value = entry.id
        editor_name.value = entry.name
        editor_chapter.value = entry.chapter_title
        editor_section.value = entry.section_title
        editor_category.value = entry.category
        editor_description.value = entry.description
        media_list.value = "当前图片：" + ("、".join(entry.media_ids) if entry.media_ids else "无")
        if entry.media_ids:
            media_id.value = entry.media_ids[0]
            try:
                media_caption.value = service.repository.media_record(entry.media_ids[0]).get("caption", "")
            except Exception:
                pass
        page.update()

    def guarded(action: Callable[[], str]) -> Callable[[Any], None]:
        def handler(_event=None) -> None:
            try:
                editor_status.value = action()
            except Exception as exc:
                editor_status.value = str(exc)
            page.update()

        return handler

    def _add_record() -> str:
        entry = service.add(
            name=editor_name.value or "未命名地点",
            chapter_title=editor_chapter.value or "用户扩展",
            section_title=editor_section.value or "用户扩展",
            category=editor_category.value or "",
            description=editor_description.value or "",
            tags=["用户扩展"],
        )
        editor_id.value = entry.id
        selected_id["value"] = entry.id
        return f"已添加：{entry.id}"

    def _update_record() -> str:
        entry = service.update(
            editor_id.value,
            name=editor_name.value,
            chapter_title=editor_chapter.value,
            section_title=editor_section.value,
            category=editor_category.value,
            description=editor_description.value,
        )
        return f"已更新：{entry.id}"

    def _attach_image() -> str:
        new_id = service.add_image(editor_id.value, media_path.value, media_caption.value or "")
        media_id.value = new_id
        entry = service.get(editor_id.value)
        media_list.value = "当前图片：" + ("、".join(entry.media_ids) if entry.media_ids else "无")
        return f"已添加图片：{new_id}"

    def _detach_image() -> str:
        entry = service.remove_image(editor_id.value, media_id.value)
        media_list.value = "当前图片：" + ("、".join(entry.media_ids) if entry.media_ids else "无")
        return f"已从记录移除图片：{media_id.value}"

    add_record = guarded(_add_record)
    update_record = guarded(_update_record)
    delete_record = guarded(lambda: (service.delete(editor_id.value) or f"已删除 / 隐藏：{editor_id.value}"))
    restore_record = guarded(lambda: f"已恢复：{service.restore(editor_id.value).id}")
    attach_image = guarded(_attach_image)
    update_caption = guarded(
        lambda: (
            service.update_image_caption(media_id.value, media_caption.value or "")
            and f"已修改图片说明：{media_id.value}"
        )
    )
    replace_image = guarded(
        lambda: (
            service.replace_image(media_id.value, media_path.value, media_caption.value or None)
            and f"已替换图片：{media_id.value}"
        )
    )
    detach_image = guarded(_detach_image)

    editor_view = ft.ListView(
        [
            _card(
                ft.Column(
                    [
                        ft.Text("数据与图片工作台", size=28, weight=_bold()),
                        ft.Text("新增、修订、隐藏地点以及管理用户图片；所有操作采用非破坏式 overlay。"),
                        button(ft, "载入搜索页当前地点", icon=icon(ft, "DOWNLOAD"), on_click=fill_selected),
                    ],
                    spacing=10,
                ),
                bgcolor=primary_container,
            ),
            _card(
                ft.Column(
                    [
                        editor_id,
                        ft.Row([editor_name, editor_chapter, editor_section, editor_category], wrap=True),
                        editor_description,
                        ft.Row(
                            [
                                button(ft, "新增", icon=icon(ft, "ADD"), on_click=add_record),
                                button(ft, "保存", icon=icon(ft, "SAVE"), on_click=update_record),
                                button(ft, "删除 / 隐藏", icon=icon(ft, "DELETE"), on_click=delete_record),
                                button(ft, "恢复", icon=icon(ft, "RESTORE"), on_click=restore_record),
                            ],
                            wrap=True,
                        ),
                    ],
                    spacing=10,
                ),
                bgcolor=surface,
            ),
            _card(
                ft.Column(
                    [
                        ft.Text("图片管理", size=18, weight=_bold()),
                        media_list,
                        ft.Row([media_id, media_path, media_caption], wrap=True),
                        ft.Row(
                            [
                                button(ft, "添加图片", on_click=attach_image),
                                button(ft, "修改说明", on_click=update_caption),
                                button(ft, "替换文件", on_click=replace_image),
                                button(ft, "从记录移除", on_click=detach_image),
                            ],
                            wrap=True,
                        ),
                    ],
                    spacing=10,
                ),
                bgcolor=surface_low,
            ),
            editor_status,
        ],
        spacing=14,
        expand=True,
        padding=0,
        build_controls_on_demand=False,
    )

    # ==================================================================
    # About / architecture
    # ==================================================================
    about_view = ft.ListView(
        [
            _card(
                ft.Column(
                    [
                        ft.Text("HUST Helper", size=30, weight=_bold()),
                        ft.Text("华中科技大学生活指南的可扩展 Python / Desktop / Android 应用框架。"),
                    ],
                    spacing=8,
                ),
                bgcolor=primary_container,
            ),
            ft.Row(
                [
                    ft.Container(_metric(ft, str(counts["entries"]), "地点记录", "PLACE"), width=220),
                    ft.Container(_metric(ft, str(counts["sections"]), "区域小节", "MAP"), width=220),
                    ft.Container(_metric(ft, str(counts["images"]), "提取图片", "IMAGE"), width=220),
                    ft.Container(_metric(ft, "2", "独立 AI 模式", "SMART_TOY"), width=220),
                ],
                wrap=True,
                spacing=10,
                run_spacing=10,
            ),
            _card(
                ft.Column(
                    [
                        ft.Text("两种 AI 模式", size=18, weight=_bold()),
                        ft.Text("1. 内置指南 AI：只读取 PDF 结构化数据，稳定、可离线检索。"),
                        ft.Text("2. 实时 MCP 探店：连接高德及用户已获授权的第三方 MCP，查询高鲜度外部信息。"),
                        ft.Text("两种模式的历史、工具和错误状态完全独立，不会互相污染。"),
                    ],
                    spacing=8,
                ),
                bgcolor=surface_low,
            ),
            _card(
                ft.Column(
                    [
                        ft.Text("数据与许可", size=18, weight=_bold()),
                        ft.Text("参考资料：《HUSTer 的干饭修养——HUST 求学七年的干饭经验》，许少 著。"),
                        ft.Text("代码：MIT License，Copyright (c) 2026 Jialiu Zeng。"),
                        ft.Text("源 PDF、平台截图及第三方内容不因收录到代码仓库而重新按 MIT 授权。"),
                        ft.Text(f"用户 overlay：{service.repository.overlay_path}", selectable=True),
                    ],
                    spacing=8,
                ),
                bgcolor=surface,
            ),
        ],
        spacing=14,
        expand=True,
        padding=0,
        build_controls_on_demand=False,
    )

    # ==================================================================
    # Application shell
    # ==================================================================
    # The content slot itself is the expanding direct child of the root
    # Column. Views are swapped through Container.content instead of nesting
    # an expanded Column inside an unconstrained Container.
    alignment_cls = getattr(ft, "Alignment", None)
    top_left = getattr(alignment_cls, "TOP_LEFT", None) if alignment_cls else None

    view_host = ft.Container(
        content=discover_view,
        padding=padding_symmetric(ft, horizontal=18, vertical=16),
        expand=True,
        alignment=top_left,
    )
    nav_buttons: list[Any] = []

    def switch(view, title: str):
        def handler(_event=None):
            view_host.content = view
            section_title.value = title
            page.update()

        return handler

    section_title = ft.Text("发现美食", size=18, weight=_bold())
    navigation = ft.Row(
        [
            button(ft, "发现", icon=icon(ft, "EXPLORE"), on_click=switch(discover_view, "发现美食")),
            button(ft, "指南 AI", icon=icon(ft, "AUTO_AWESOME"), on_click=switch(local_chat_view, "内置指南 AI")),
            button(ft, "实时 MCP", icon=icon(ft, "TRAVEL_EXPLORE"), on_click=switch(live_chat_view, "实时 MCP 探店")),
            button(ft, "数据工作台", icon=icon(ft, "EDIT_NOTE"), on_click=switch(editor_view, "数据与图片工作台")),
            button(ft, "关于", icon=icon(ft, "INFO"), on_click=switch(about_view, "关于 HUST Helper")),
        ],
        wrap=True,
    )
    nav_buttons.extend(navigation.controls)

    header = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(icon(ft, "RESTAURANT_MENU"), size=30),
                        ft.Column(
                            [
                                ft.Text("HUST Helper", size=20, weight=_bold()),
                                section_title,
                            ],
                            spacing=0,
                        ),
                    ],
                    spacing=10,
                ),
                navigation,
            ],
            spacing=10,
        ),
        padding=padding_symmetric(ft, horizontal=20, vertical=12),
        bgcolor=surface_high,
    )
    # A single bounded root layout prevents the workspace from collapsing
    # to zero height on desktop/Web builds.
    app_shell = ft.Column(
        [
            header,
            view_host,
        ],
        spacing=0,
        expand=True,
        horizontal_alignment=getattr(
            getattr(ft, "CrossAxisAlignment", None),
            "STRETCH",
            None,
        ),
    )

    safe_area_cls = getattr(ft, "SafeArea", None)
    root_control = (
        safe_area_cls(content=app_shell, expand=True)
        if safe_area_cls is not None
        else app_shell
    )
    page.add(root_control)

    # Populate after the controls are mounted. Any startup search failure is
    # rendered as text instead of leaving a silent empty workspace.
    try:
        do_search()
    except Exception as exc:
        search_status.value = f"初始化搜索失败：{type(exc).__name__}: {exc}"
        result_column.controls[:] = [
            ft.Text(
                "界面已加载，但本地数据初始化失败。请复制此错误信息进行排查。",
                selectable=True,
            )
        ]
        page.update()


def run() -> None:
    run_app(ft, main)


if __name__ == "__main__":
    run()
