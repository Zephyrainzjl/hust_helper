from __future__ import annotations

import base64


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


def _image_fit_contain(ft):
    box_fit = getattr(ft, "BoxFit", None)
    return getattr(box_fit, "CONTAIN", None) if box_fit is not None else None


def _image_error_content(ft):
    text_cls = getattr(ft, "Text", None)
    container_cls = getattr(ft, "Container", None)
    if text_cls is None:
        return None

    message = text_cls("图片加载失败", size=12)
    if container_cls is None:
        return message

    return container_cls(
        content=message,
        alignment=getattr(getattr(ft, "Alignment", None), "CENTER", None),
    )


def image_from_bytes(ft, data: bytes, **kwargs):
    """Create an Image from encoded image bytes.

    Although current Flet accepts both raw bytes and a base64 string through
    ``Image.src``, a base64 string is the most deterministic representation
    across desktop transports and packaged executables because it avoids
    transporting Python ``bytes`` through the control protocol.
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("image data must be bytes-like")

    encoded = base64.b64encode(bytes(data)).decode("ascii")
    options = dict(kwargs)
    options.setdefault("fit", _image_fit_contain(ft))
    options.setdefault("error_content", _image_error_content(ft))
    options.setdefault("gapless_playback", True)

    # Avoid passing optional fields as None to older Flet releases.
    options = {key: value for key, value in options.items() if value is not None}
    return ft.Image(src=encoded, **options)


def image_from_base64(ft, encoded: str, **kwargs):
    """Backward-compatible wrapper for callers that still hold base64 text."""
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid base64 image data") from exc
    return image_from_bytes(ft, data, **kwargs)


def run_app(ft, target):
    runner = getattr(ft, "run", None) or getattr(ft, "app")
    try:
        return runner(target)
    except TypeError:
        return runner(target=target)


def padding_symmetric(ft, *, horizontal: float = 0, vertical: float = 0):
    """Create symmetric padding across old and new Flet releases.

    Flet 0.85 removed the deprecated module-level ``ft.padding`` helpers.
    New releases expose ``ft.Padding.symmetric`` instead, while older
    releases may only expose ``ft.padding.symmetric``.
    """
    padding_class = getattr(ft, "Padding", None)
    symmetric = getattr(padding_class, "symmetric", None)
    if callable(symmetric):
        return symmetric(horizontal=horizontal, vertical=vertical)

    padding_module = getattr(ft, "padding", None)
    symmetric = getattr(padding_module, "symmetric", None)
    if callable(symmetric):
        return symmetric(horizontal=horizontal, vertical=vertical)

    if padding_class is not None:
        try:
            return padding_class(
                left=horizontal,
                top=vertical,
                right=horizontal,
                bottom=vertical,
            )
        except TypeError:
            pass

    # PaddingValue also accepts a four-item sequence in supported Flet
    # versions. Keep this final fallback free of version-specific imports.
    return (horizontal, vertical, horizontal, vertical)
