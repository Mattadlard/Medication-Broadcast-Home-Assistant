"""Icon helpers and automatic mirroring for Medication Broadcast Assistant.

All source icons are stored under this integration:...

    custom_components/medication_broadcast/icons/

Structure:

    icons/
      tablet/
        tablet-16px.png
        tablet-24px.png
        tablet-32px.png
        tablet-64px.png
        tablet-128px.png
        tablet-256px.png
        tablet-512px.png
      refill/
        refill-16px.png
        refill-24px.png
        refill-32px.png
        refill-64px.png
        refill-128px.png
        refill-256px.png
        refill-512px.png

On setup we mirror these to:

    /config/www/medication_broadcast/tablet/
    /config/www/medication_broadcast/refill/

So Lovelace can use:

    /local/medication_broadcast/tablet/tablet-128px.png
    /local/medication_broadcast/refill/refill-128px.png
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Literal

from homeassistant.core import HomeAssistant

from .const import (
    ICON_SIZES,
    DEFAULT_ICON_SIZE,
)

_LOGGER = logging.getLogger(__name__)

IconKind = Literal["tablet", "refill"]


def _nearest_size(requested: int) -> int:
    """Pick the nearest available icon size."""
    if requested in ICON_SIZES:
        return requested
    return min(ICON_SIZES, key=lambda s: abs(s - requested))


def get_integration_icon_path(kind: IconKind, size: int | None = None) -> str:
    """Internal path inside custom_components for a given icon.

    This path is relative to the Home Assistant config directory. need to fix future ideas though

    Example:
        "custom_components/medication_broadcast/icons/tablet/tablet-128px.png"
    """
    if size is None:
        size = DEFAULT_ICON_SIZE
    chosen = _nearest_size(size)

    if kind == "tablet":
        root = "custom_components/medication_broadcast/icons/tablet"
    elif kind == "refill":
        root = "custom_components/medication_broadcast/icons/refill"
    else:
        raise ValueError(f"Unknown icon kind: {kind}")

    return f"{root}/{kind}-{chosen}px.png"


def get_lovelace_icon_url(kind: IconKind, size: int | None = None) -> str:
    """Return a /local/ URL for use in Lovelace.

    This assumes icons have been mirrored into: i hope so this time. note to self.

        /config/www/medication_broadcast/<kind>/<kind>-<size>px.png
    """
    if size is None:
        size = DEFAULT_ICON_SIZE
    chosen = _nearest_size(size)

    if kind == "tablet":
        return f"/local/medication_broadcast/tablet/tablet-{chosen}px.png"
    if kind == "refill":
        return f"/local/medication_broadcast/refill/refill-{chosen}px.png"

    raise ValueError(f"Unknown icon kind: {kind}")


async def async_ensure_icons_mirrored(hass: HomeAssistant) -> None:
    """Copy icon files from the integration into /config/www for Lovelace use.

    This is intended to be called on setup. It is idempotent:
    if files already exist at the destination, they will be overwritten, i hope, its late, 3am..
    so updates to icons propagate cleanly.
    """
    config_dir = Path(hass.config.path(""))
    source_root = Path(__file__).parent / "icons"
    dest_root = config_dir / "www" / "medication_broadcast"

    # Run the file operations in an executor to avoid blocking the event loop
    def _sync() -> None:
        if not source_root.exists():
            _LOGGER.warning(
                "Icon source directory %s does not exist; skipping icon sync.",
                source_root,
            )
            return

        # Mirror each subdirectory (tablet, refill)
        for sub in ("tablet", "refill"):
            src_dir = source_root / sub
            dest_dir = dest_root / sub

            if not src_dir.exists():
                _LOGGER.warning("Icon source subdirectory %s missing", src_dir)
                continue

            os.makedirs(dest_dir, exist_ok=True)

            for file in src_dir.iterdir():
                if not file.is_file():
                    continue
                dest_file = dest_dir / file.name
                try:
                    shutil.copyfile(file, dest_file)
                except OSError as exc:
                    _LOGGER.error("Failed to copy icon %s to %s: %s", file, dest_file, exc)
                else:
                    _LOGGER.debug("Mirrored icon %s -> %s", file, dest_file)

        _LOGGER.info(
            "Medication Broadcast icons mirrored into /config/www/medication_broadcast/"
        )

    await hass.async_add_executor_job(_sync)
