"""HUST campus-life helper framework."""

from ._version import __version__
from .tools.hust_eater.api import eater

__all__ = ["__version__", "eater"]
