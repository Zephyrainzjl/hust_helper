from __future__ import annotations


def icon(ft, name: str):
    """Resolve both old `ft.icons` and newer `ft.Icons` names."""
    for container_name in ("Icons", "icons"):
        container = getattr(ft, container_name, None)
        if container and hasattr(container, name):
            return getattr(container, name)
    return None


def color(ft, name: str, fallback: str | None = None):
    for container_name in ("Colors", "colors"):
        container = getattr(ft, container_name, None)
        if container and hasattr(container, name):
            return getattr(container, name)
    return fallback


def button(ft, text: str, **kwargs):
    modern = getattr(ft, "Button", None)
    if modern is not None:
        return modern(content=text, **kwargs)
    return ft.ElevatedButton(text=text, **kwargs)


def image_from_base64(ft, encoded: str, **kwargs):
    try:
        return ft.Image(src_base64=encoded, **kwargs)
    except TypeError:
        return ft.Image(src=f"data:image/png;base64,{encoded}", **kwargs)


def run_app(ft, target):
    runner = getattr(ft, "run", None) or getattr(ft, "app")
    try:
        return runner(target)
    except TypeError:
        return runner(target=target)
