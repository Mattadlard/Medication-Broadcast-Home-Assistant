"""Icon helpers for Medication Broadcast Assistant.

All icons are stored locally under the integration directory:

    custom_components/medication_broadcast/icons/

There are two icon families:
    - tablet
    - refill

Each has multiple sizes: it should. need to double chek 3am....
    16, 24, 32, 64, 128, 256, 512 px

This module gives you:
    - automatic size selection (nearest available)
    - simple helpers to build either:
        * internal paths (for reference)
        * /local/ URLs, if you mirror icons into /config/www
"""

from __future__ import annotations

from typing import Literal

from .const import (
    ICON_PATH_TABLET_ROOT,
    ICON_PATH_REFILL_ROOT,
    ICON_SIZES,
    DEFAULT_ICON_SIZE,
)

IconKind = Literal["tablet", "refill"]


def _nearest_size(requested: int) -> int:
    """Pick the nearest available icon size.

    Example:
        requested = 40  -> 32 (closer than 64)
        requested = 130 -> 128
        requested = 3   -> 16
    """
    if requested in ICON_SIZES:
        return requested
    # Basic nearest neighbour selection
    return min(ICON_SIZES, key=lambda s: abs(s - requested))


def _family_root(kind: IconKind) -> str:
    if kind == "tablet":
        return ICON_PATH_TABLET_ROOT
    if kind == "refill":
        return ICON_PATH_REFILL_ROOT
    # If someone passes nonsense, fail loudly rather than quietly
    raise ValueError(f"Unknown icon kind: {kind}")


def get_icon_path(kind: IconKind, size: int | None = None) -> str:
    """Return the internal icon path for a given family and size.

    This is the path relative to the Home Assistant config directory,
    pointing into the integration itself, for reference or copying.

    Example result:
        "custom_components/medication_broadcast/icons/tablet/tablet-128px.png"
    """
    if size is None:
        size = DEFAULT_ICON_SIZE
    chosen = _nearest_size(size)
    root = _family_root(kind)
    return f"{root}/{kind}-{chosen}px.png"


def get_lovelace_icon_url(kind: IconKind, size: int | None = None) -> str:
    """Return a /local/ URL for use in Lovelace, assuming icons
    have been mirrored into /config/www/medication_broadcast. i think. its late im tired,,

    You are responsible for copying the files, for example:

        /config/www/medication_broadcast/tablet/tablet-128px.png
        /config/www/medication_broadcast/refill/refill-128px.png

    Then this will return:
        "/local/medication_broadcast/tablet/tablet-128px.png"
    """
    if size is None:
        size = DEFAULT_ICON_SIZE
    chosen = _nearest_size(size)

    # This mirrors the integration layout under /www/
    if kind == "tablet":
        return f"/local/medication_broadcast/tablet/tablet-{chosen}px.png"
    if kind == "refill":
        return f"/local/medication_broadcast/refill/refill-{chosen}px.png"

    raise ValueError(f"Unknown icon kind: {kind}")
