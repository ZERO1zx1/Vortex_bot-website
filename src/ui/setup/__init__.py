"""Shared building blocks for administrative setup panels."""

from .panel import (
    ConfirmActionView,
    SetupPanel,
    SetupState,
    disable_setup_panel,
    mention_or_missing,
    state_text,
    sync_toggle_button,
)

__all__ = [
    "ConfirmActionView",
    "SetupPanel",
    "SetupState",
    "disable_setup_panel",
    "mention_or_missing",
    "state_text",
    "sync_toggle_button",
]
