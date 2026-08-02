from __future__ import annotations

import base64
import os
import threading
from typing import Any

try:
    import flet as ft
except ImportError as exc:
    raise ImportError('Install GUI support with: pip install "hust_helper[gui]"') from exc

from hust_helper.llm import FoodChatAgent, LLMConfig
from hust_helper.tools.hust_eater.service import HustEaterService

from .compat import button, icon, image_from_base64, run_app


def _dropdown_option(value: str):
    old_option = getattr(getattr(ft, "dropdown", None), "Option", None)
    if old_option is not None:
        return old_option(value)
    new_option = getattr(ft, "DropdownOption", None)
    if new_option is not None:
        try:
            return new_option(key=value, text=value)
        except TypeError:
            return new_option(value=value, label=value)
    return value


def _scroll_auto():
    mode = getattr(ft, "ScrollMode", None)
    return getattr(mode, "AUTO", "auto") if mode else "auto"


def _bold():
    weight = getattr(ft, "FontWeight", None)
    return getattr(weight, "BOLD", "bold") if weight else "bold"


def main(page: ft.Page) -> None:
    page.title = "HUST Helper · 干饭助手"
    page.padding = 16
    page.scroll = _scroll_auto()
    theme_mode = getattr(ft, "ThemeMode", None)
    if theme_mode is not None:
        page.theme_mode = getattr(theme_mode, "SYSTEM", None)

    service = HustEaterService()
    catalog = service.repository.catalog()
    entries = service.entries()
    chapters = sorted({entry.chapter_title for entry in entries if entry.chapter_title})
    sections = sorted({entry.section_title for entry in entries if entry.section_title})
    selected_id: dict[str, str | None] = {"value": None}

    # ------------------------------------------------------------------
    # Search view
    # ------------------------------------------------------------------
    status = ft.Text("数据已加载", size=12)
    query = ft.TextField(label="搜索菜名、地点、口味、描述", expand=True)
    chapter = ft.Dropdown(
        label="章节",
        options=[_dropdown_option("")] + [_dropdown_option(item) for item in chapters],
        width=230,
    )
    section = ft.Dropdown(
        label="区域/小节",
        options=[_dropdown_option("")] + [_dropdown_option(item) for item in sections],
        width=190,
    )
    visit = ft.Dropdown(
        label="作者状态",
        options=[
            _dropdown_option(""),
            _dropdown_option("visited_by_author"),
            _dropdown_option("not_visited_by_author"),
            _dropdown_option("unspecified"),
        ],
        width=210,
    )
    spicy = ft.Checkbox(label="有辣度提示")
    with_images = ft.Checkbox(label="含图片")
    result_column = ft.Column(spacing=8)
    detail = ft.Column(spacing=8)

    def show_entry(entry) -> None:
        selected_id["value"] = entry.id
        detail.controls.clear()
        detail.controls.extend(
            [
                ft.Text(entry.name, size=24, weight=_bold()),
                ft.Text(f"{entry.chapter_title} / {entry.section_title} · {entry.category or entry.venue_type}"),
                ft.Text(f"作者状态：{entry.author_visit_status} · PDF 页：{entry.source_pages}"),
            ]
        )
        if entry.recommended_items:
            detail.controls.append(ft.Text("推荐：" + "、".join(entry.recommended_items)))
        detail.controls.append(ft.Text(entry.description or "（原文无补充描述）", selectable=True))
        if entry.media_ids:
            detail.controls.append(ft.Text("相关图片", weight=_bold()))
            gallery = ft.Row(wrap=True, spacing=8, run_spacing=8)
            for media_id in entry.media_ids[:16]:
                try:
                    encoded = base64.b64encode(service.repository.image_bytes(media_id)).decode("ascii")
                    record = service.repository.media_record(media_id)
                    image = image_from_base64(ft, encoded, width=220, height=150)
                    gallery.controls.append(
                        ft.Column(
                            [
                                image,
                                ft.Text(record.get("caption") or media_id, size=11, width=220),
                                ft.Text(media_id, size=10, width=220),
                            ],
                            spacing=3,
                        )
                    )
                except Exception as exc:
                    gallery.controls.append(ft.Text(f"{media_id}: {exc}", size=11))
            detail.controls.append(gallery)
        page.update()

    def result_card(result):
        entry = result.entry
        subtitle = f"{entry.section_title} · {entry.category or entry.venue_type} · 第 {','.join(map(str, entry.source_pages))} 页"
        dishes = "、".join(entry.recommended_items[:5])
        tile_cls = getattr(ft, "ListTile", None)
        if tile_cls is not None:
            tile = tile_cls(
                title=ft.Text(entry.name),
                subtitle=ft.Text(subtitle + (f"\n推荐：{dishes}" if dishes else "")),
                trailing=ft.Text(f"{result.score:.1f}"),
                on_click=lambda _e, item=entry: show_entry(item),
            )
            return ft.Container(content=tile, padding=4, border_radius=10)
        return button(ft, entry.name, on_click=lambda _e, item=entry: show_entry(item))

    def do_search(_event=None) -> None:
        result_column.controls.clear()
        results = service.search(
            query.value or "",
            chapter=chapter.value or None,
            section=section.value or None,
            visited=visit.value or None,
            spicy=True if spicy.value else None,
            has_images=True if with_images.value else None,
            limit=60,
        )
        result_column.controls.extend(result_card(item) for item in results)
        status.value = f"找到 {len(results)} 条；结构化总记录 {len(service.entries())} 条"
        page.update()

    query.on_submit = do_search
    search_view = ft.Column(
        [
            ft.Text("多条件搜索", size=20, weight=_bold()),
            ft.Row([query, button(ft, "搜索", icon=icon(ft, "SEARCH"), on_click=do_search)]),
            ft.Row([chapter, section, visit, spicy, with_images], wrap=True),
            status,
            ft.ResponsiveRow(
                [
                    ft.Container(content=result_column, col={"sm": 12, "md": 5}, padding=8),
                    ft.Container(content=detail, col={"sm": 12, "md": 7}, padding=8),
                ]
            ),
        ],
        spacing=10,
    )

    # ------------------------------------------------------------------
    # Chat view
    # ------------------------------------------------------------------
    provider = ft.Dropdown(
        label="API 提供商",
        value="openai",
        options=[
            _dropdown_option(x)
            for x in ["openai", "siliconflow", "openrouter", "deepseek", "dashscope", "custom", "litellm"]
        ],
        width=190,
    )
    model = ft.TextField(label="模型 ID", value=os.environ.get("HUST_HELPER_MODEL", "gpt-5.6"), width=260)
    base_url = ft.TextField(label="自定义 Base URL（预设可留空）", width=330)
    api_key = ft.TextField(label="API Key（仅当前会话）", password=True, can_reveal_password=True, width=310)
    chat_input = ft.TextField(label="告诉助手你想吃什么", expand=True, multiline=True, min_lines=1, max_lines=4)
    chat_log = ft.Column(spacing=8)
    chat_status = ft.Text("未填写 API Key 时自动使用纯本地检索。", size=12)
    agent_holder: dict[str, Any] = {"signature": None, "agent": None}

    def append_chat(role: str, text: str) -> None:
        chat_log.controls.append(
            ft.Container(
                content=ft.Column([ft.Text(role, weight=_bold()), ft.Text(text, selectable=True)]),
                padding=10,
                border_radius=10,
            )
        )

    def send_chat(_event=None) -> None:
        question = (chat_input.value or "").strip()
        if not question:
            return
        append_chat("你", question)
        chat_input.value = ""
        chat_status.value = "正在检索/生成…"
        page.update()

        def worker() -> None:
            try:
                signature = (provider.value, model.value, base_url.value, api_key.value)
                if agent_holder["signature"] != signature:
                    config = LLMConfig.from_preset(
                        provider.value or "openai",
                        model=model.value or None,
                        api_key=api_key.value or None,
                        base_url=base_url.value or None,
                    )
                    agent_holder["agent"] = FoodChatAgent(config=config, service=service)
                    agent_holder["signature"] = signature
                reply = agent_holder["agent"].ask(question)
                append_chat("HUST Helper", reply.text)
                chat_status.value = f"返回 {len(reply.sources)} 个本地来源"
            except Exception as exc:
                append_chat("错误", str(exc))
                chat_status.value = "调用失败；请检查模型、Key、Base URL 与网络。"
            page.update()

        threading.Thread(target=worker, daemon=True).start()

    chat_input.on_submit = send_chat
    chat_view = ft.Column(
        [
            ft.Text("对话式找吃的", size=20, weight=_bold()),
            ft.Row([provider, model, base_url, api_key], wrap=True),
            chat_log,
            ft.Row([chat_input, button(ft, "发送", icon=icon(ft, "SEND"), on_click=send_chat)]),
            chat_status,
        ],
        spacing=10,
    )

    # ------------------------------------------------------------------
    # Editor view: entries + images
    # ------------------------------------------------------------------
    editor_id = ft.TextField(label="记录 ID（更新/删除/图片操作时填写）")
    editor_name = ft.TextField(label="名称")
    editor_chapter = ft.TextField(label="章节", value="用户扩展")
    editor_section = ft.TextField(label="区域/小节", value="用户扩展")
    editor_category = ft.TextField(label="类型")
    editor_description = ft.TextField(label="描述", multiline=True, min_lines=4, max_lines=10)
    media_id = ft.TextField(label="图片 Media ID")
    media_path = ft.TextField(label="本地图片路径（添加/替换）")
    media_caption = ft.TextField(label="图片说明")
    media_list = ft.Text("当前图片：无", selectable=True)
    editor_status = ft.Text("所有修改均进入用户目录中的 overlay，不改动包内原始数据。")

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

    def add_record(_event=None) -> None:
        try:
            entry = service.add(
                name=editor_name.value or "未命名地点",
                chapter_title=editor_chapter.value or "用户扩展",
                section_title=editor_section.value or "用户扩展",
                category=editor_category.value or "",
                description=editor_description.value or "",
                tags=["用户扩展"],
            )
            editor_id.value = entry.id
            editor_status.value = f"已添加：{entry.id}"
        except Exception as exc:
            editor_status.value = str(exc)
        page.update()

    def update_record(_event=None) -> None:
        try:
            entry = service.update(
                editor_id.value,
                name=editor_name.value,
                chapter_title=editor_chapter.value,
                section_title=editor_section.value,
                category=editor_category.value,
                description=editor_description.value,
            )
            editor_status.value = f"已更新：{entry.id}"
        except Exception as exc:
            editor_status.value = str(exc)
        page.update()

    def delete_record(_event=None) -> None:
        try:
            service.delete(editor_id.value)
            editor_status.value = f"已删除/隐藏：{editor_id.value}"
        except Exception as exc:
            editor_status.value = str(exc)
        page.update()

    def restore_record(_event=None) -> None:
        try:
            service.restore(editor_id.value)
            editor_status.value = f"已恢复：{editor_id.value}"
        except Exception as exc:
            editor_status.value = str(exc)
        page.update()

    def attach_image(_event=None) -> None:
        try:
            new_id = service.add_image(editor_id.value, media_path.value, media_caption.value or "")
            media_id.value = new_id
            editor_status.value = f"已添加图片：{new_id}"
            fill_selected()
        except Exception as exc:
            editor_status.value = str(exc)
            page.update()

    def update_caption(_event=None) -> None:
        try:
            service.update_image_caption(media_id.value, media_caption.value or "")
            editor_status.value = f"已修改图片说明：{media_id.value}"
        except Exception as exc:
            editor_status.value = str(exc)
        page.update()

    def replace_image(_event=None) -> None:
        try:
            service.replace_image(media_id.value, media_path.value, media_caption.value or None)
            editor_status.value = f"已替换图片：{media_id.value}"
        except Exception as exc:
            editor_status.value = str(exc)
        page.update()

    def detach_image(_event=None) -> None:
        try:
            service.remove_image(editor_id.value, media_id.value)
            editor_status.value = f"已从记录移除图片：{media_id.value}"
            fill_selected()
        except Exception as exc:
            editor_status.value = str(exc)
            page.update()

    editor_view = ft.Column(
        [
            ft.Text("数据与图片编辑", size=20, weight=_bold()),
            button(ft, "载入搜索页当前记录", on_click=fill_selected),
            editor_id,
            ft.Row([editor_name, editor_chapter, editor_section, editor_category], wrap=True),
            editor_description,
            ft.Row(
                [
                    button(ft, "新增记录", icon=icon(ft, "ADD"), on_click=add_record),
                    button(ft, "保存修改", icon=icon(ft, "SAVE"), on_click=update_record),
                    button(ft, "删除/隐藏", icon=icon(ft, "DELETE"), on_click=delete_record),
                    button(ft, "恢复", icon=icon(ft, "RESTORE"), on_click=restore_record),
                ],
                wrap=True,
            ),
            ft.Divider(),
            media_list,
            ft.Row([media_id, media_path, media_caption], wrap=True),
            ft.Row(
                [
                    button(ft, "添加图片", on_click=attach_image),
                    button(ft, "修改图片说明", on_click=update_caption),
                    button(ft, "替换图片文件", on_click=replace_image),
                    button(ft, "从记录删除图片", on_click=detach_image),
                ],
                wrap=True,
            ),
            editor_status,
        ],
        spacing=10,
    )

    # ------------------------------------------------------------------
    # About view
    # ------------------------------------------------------------------
    counts = catalog["counts"]
    about_view = ft.Column(
        [
            ft.Text("HUST Helper", size=28, weight=_bold()),
            ft.Text("首个模块：tools/hust_eater"),
            ft.Text(
                f"源 PDF：{catalog['source_pdf_pages']} 页；章节 {counts['chapters']}；小节 {counts['sections']}；"
                f"结构化记录 {counts['entries']}；原始图片 {counts['images']}。"
            ),
            ft.Text("内容来源：《HUSTer 的干饭修养——HUST 求学七年的干饭经验》，许少 著。"),
            ft.Text("代码：MIT License，Copyright (c) 2026 Jialiu Zeng。源内容及第三方截图不随代码 MIT 重新授权。"),
            ft.Text(f"用户 overlay：{service.repository.overlay_path}"),
            ft.Text("保留原 PDF、逐页 JSON/Markdown、文本布局、颜色、边界框、图片及哈希，便于校对与后续扩展。"),
        ],
        spacing=12,
    )

    # Manual navigation avoids API churn between older and newer Flet Tabs controls.
    view_host = ft.Column([search_view], expand=True)

    def switch(view):
        def handler(_event=None):
            view_host.controls = [view]
            page.update()
        return handler

    navigation = ft.Row(
        [
            button(ft, "搜索", icon=icon(ft, "SEARCH"), on_click=switch(search_view)),
            button(ft, "AI 对话", icon=icon(ft, "CHAT"), on_click=switch(chat_view)),
            button(ft, "数据/图片编辑", icon=icon(ft, "EDIT"), on_click=switch(editor_view)),
            button(ft, "关于", icon=icon(ft, "INFO"), on_click=switch(about_view)),
        ],
        wrap=True,
    )
    page.add(navigation, ft.Divider(), view_host)
    do_search()


def run() -> None:
    run_app(ft, main)


if __name__ == "__main__":
    run()
