from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hust_helper.llm import FoodChatAgent, LLMConfig
from hust_helper.tools.hust_eater.api import eater


def _print_entry(entry, score: float | None = None) -> None:
    prefix = f"[{score:.1f}] " if score is not None else ""
    print(f"{prefix}{entry.name}  ({entry.chapter_title} / {entry.section_title})")
    if entry.category:
        print(f"  类型: {entry.category}")
    if entry.recommended_items:
        print(f"  推荐: {'、'.join(entry.recommended_items)}")
    print(f"  作者状态: {entry.author_visit_status}; 来源页: {entry.source_pages}")
    print(f"  ID: {entry.id}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hust-helper", description="HUST campus-life helper")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("stats", help="Show bundled data counts")

    search = sub.add_parser("search", help="Search food entries")
    search.add_argument("query", nargs="?", default="")
    search.add_argument("--chapter")
    search.add_argument("--section")
    search.add_argument("--category")
    search.add_argument("--venue-type")
    search.add_argument("--meal-period")
    search.add_argument("--visited")
    search.add_argument("--spicy", action="store_true")
    search.add_argument("--avoid-spicy", action="store_true")
    search.add_argument("--recommended-only", action="store_true")
    search.add_argument("--with-images", action="store_true")
    search.add_argument("--with-price-notes", action="store_true")
    search.add_argument("--external-only", action="store_true")
    search.add_argument("--exclude", action="append", default=[])
    search.add_argument("--sort", choices=["relevance", "recommendations", "visited", "source_page", "name"], default="relevance")
    search.add_argument("--query-mode", choices=["smart", "all", "exact"], default="smart")
    search.add_argument("--limit", type=int, default=20)
    search.add_argument("--json", action="store_true")

    show = sub.add_parser("show", help="Show one entry")
    show.add_argument("entry_id")
    show.add_argument("--json", action="store_true")

    export = sub.add_parser("export", help="Export merged catalog")
    export.add_argument("--format", choices=["json", "jsonl"], default="json")
    export.add_argument("--output", type=Path, required=True)

    add = sub.add_parser("add", help="Add a local entry")
    add.add_argument("name")
    add.add_argument("--description", default="")
    add.add_argument("--chapter", default="用户扩展")
    add.add_argument("--section", default="用户扩展")
    add.add_argument("--category", default="")

    update = sub.add_parser("update", help="Patch a local or bundled entry in the overlay")
    update.add_argument("entry_id")
    update.add_argument("--name")
    update.add_argument("--description")
    update.add_argument("--category")

    delete = sub.add_parser("delete", help="Hide an entry using the overlay")
    delete.add_argument("entry_id")

    restore = sub.add_parser("restore", help="Restore a hidden entry")
    restore.add_argument("entry_id")

    chat = sub.add_parser("chat", help="Ask the bundled-PDF food agent")
    chat.add_argument("question")
    chat.add_argument("--provider", default="openai")
    chat.add_argument("--model")
    chat.add_argument("--base-url")
    chat.add_argument("--api-key")

    live = sub.add_parser("live-chat", help="Ask the independent real-time MCP food agent")
    live.add_argument("question")
    live.add_argument("--provider", default="siliconflow")
    live.add_argument("--model", required=True)
    live.add_argument("--base-url")
    live.add_argument("--api-key", required=True)
    live.add_argument("--amap-key")
    live.add_argument("--mcp-json", help="JSON array or path to a JSON file containing extra MCP servers")
    live.add_argument("--city", default="武汉")
    live.add_argument("--center", default="华中科技大学")
    live.add_argument("--radius", type=int, default=3000)

    sub.add_parser("gui", help="Launch the Flet GUI")
    return parser


def _read_json_argument(value: str | None) -> str:
    if not value:
        return "[]"
    path = Path(value)
    return path.read_text(encoding="utf-8") if path.is_file() else value


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "stats":
        print(json.dumps(eater.stats(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "search":
        results = eater.search_with_scores(
            args.query,
            chapter=args.chapter,
            section=args.section,
            category=args.category,
            venue_type=args.venue_type,
            meal_period=args.meal_period,
            visited=args.visited,
            spicy=True if args.spicy else None,
            avoid_spicy=args.avoid_spicy,
            recommended_only=args.recommended_only,
            has_images=True if args.with_images else None,
            has_price_notes=True if args.with_price_notes else None,
            external_recommended=True if args.external_only else None,
            exclude_terms=args.exclude,
            sort_by=args.sort,
            query_mode=args.query_mode,
            limit=args.limit,
        )
        if args.json:
            print(json.dumps([result.to_dict() for result in results], ensure_ascii=False, indent=2))
        else:
            for result in results:
                _print_entry(result.entry, result.score)
        return 0
    if args.command == "show":
        entry = eater.get(args.entry_id)
        if args.json:
            print(json.dumps(entry.to_dict(), ensure_ascii=False, indent=2))
        else:
            _print_entry(entry)
            print("\n" + entry.description)
        return 0
    if args.command == "export":
        print(eater.export(args.output, args.format))
        return 0
    if args.command == "add":
        entry = eater.add(
            name=args.name,
            description=args.description,
            chapter_title=args.chapter,
            section_title=args.section,
            category=args.category,
            tags=["用户扩展"],
        )
        print(entry.id)
        return 0
    if args.command == "update":
        changes = {
            key: value
            for key, value in {
                "name": args.name,
                "description": args.description,
                "category": args.category,
            }.items()
            if value is not None
        }
        _print_entry(eater.update(args.entry_id, **changes))
        return 0
    if args.command == "delete":
        eater.delete(args.entry_id)
        return 0
    if args.command == "restore":
        _print_entry(eater.restore(args.entry_id))
        return 0
    if args.command == "chat":
        config = LLMConfig.from_preset(
            args.provider,
            model=args.model,
            api_key=args.api_key,
            base_url=args.base_url,
        )
        print(FoodChatAgent(config).ask(args.question).text)
        return 0
    if args.command == "live-chat":
        from hust_helper.realtime import (
            MCPHub,
            MCPServerConfig,
            RealtimeFoodAgent,
            parse_server_configs,
        )

        servers = []
        if args.amap_key:
            servers.append(MCPServerConfig.amap(args.amap_key))
        servers.extend(parse_server_configs(_read_json_argument(args.mcp_json)))
        servers = [server for server in servers if server.enabled]
        if not servers:
            print("At least one enabled MCP server is required.", file=sys.stderr)
            return 2
        config = LLMConfig.from_preset(
            args.provider,
            model=args.model,
            api_key=args.api_key,
            base_url=args.base_url,
        )
        context = f"默认城市：{args.city}；默认中心点：{args.center}；默认半径：{args.radius} 米。\n"
        reply = RealtimeFoodAgent(config, MCPHub(servers)).ask(context + args.question)
        print(reply.text)
        return 0
    if args.command == "gui":
        try:
            from hust_helper.ui.flet_app import run
        except ImportError as exc:
            print('GUI dependency missing. Install with: pip install "hust_helper[gui]"', file=sys.stderr)
            return 2
        run()
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
