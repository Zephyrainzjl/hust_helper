from __future__ import annotations

from .config import MCPServerConfig


def amap_mcp(api_key: str) -> MCPServerConfig:
    """Build the official Amap Streamable HTTP MCP configuration."""

    return MCPServerConfig.amap(api_key)


def authorized_meituan_mcp(
    url: str,
    token: str,
    *,
    name: str = "meituan-authorized",
) -> MCPServerConfig:
    """Build a Meituan connector from credentials granted to the user.

    This helper does not scrape Meituan and does not create access rights.  The
    URL must point to an MCP service supplied by the user's approved integration
    or by their own compliant backend.
    """

    return _authorized_platform_mcp(name, url, token)


def authorized_dianping_mcp(
    url: str,
    token: str,
    *,
    name: str = "dianping-authorized",
) -> MCPServerConfig:
    """Build a Dianping connector from credentials granted to the user."""

    return _authorized_platform_mcp(name, url, token)


def _authorized_platform_mcp(name: str, url: str, token: str) -> MCPServerConfig:
    if not url.strip():
        raise ValueError(f"{name} MCP URL 不能为空")
    headers = {"Authorization": f"Bearer {token.strip()}"} if token.strip() else {}
    config = MCPServerConfig(name=name, url=url.strip(), headers=headers)
    config.validate()
    return config
