"""Parse and format one configurable global hotkey trigger."""

from __future__ import annotations

from dataclasses import dataclass


_VALID_MODIFIERS = ("alt", "ctrl", "shift", "meta", "win")


@dataclass(slots=True, frozen=True)
class HotkeyTrigger:
    """Normalized trigger parts used by the listener backends."""

    modifiers: tuple[str, ...]
    key: str

    @property
    def label(self) -> str:
        """Return a human-readable trigger label."""

        parts = [modifier.title().replace("Ctrl", "Ctrl") for modifier in self.modifiers]
        key_part = self.key.upper() if len(self.key) == 1 else self.key.upper()
        return "+".join([*parts, key_part])


def parse_hotkey_trigger(trigger: str, default: str = "Alt+L") -> HotkeyTrigger:
    """Parse one trigger string like ``Alt+L`` into normalized parts."""

    normalized = trigger.strip() or default
    tokens = [token.strip().lower() for token in normalized.split("+") if token.strip()]
    if len(tokens) < 2:
        tokens = [token.strip().lower() for token in default.split("+") if token.strip()]

    key = tokens[-1]
    modifiers = tuple(_normalize_modifiers(tokens[:-1]))
    if not modifiers:
        fallback = [token.strip().lower() for token in default.split("+") if token.strip()]
        modifiers = tuple(_normalize_modifiers(fallback[:-1]))
        key = fallback[-1]
    return HotkeyTrigger(modifiers=modifiers, key=key)


def format_hotkey_trigger(trigger: str) -> str:
    """Return a normalized display label for one trigger string."""

    return parse_hotkey_trigger(trigger).label


def _normalize_modifiers(modifiers: list[str]) -> list[str]:
    normalized: list[str] = []
    for modifier in modifiers:
        mapped = {
            "control": "ctrl",
            "win": "meta",
        }.get(modifier, modifier)
        if mapped in _VALID_MODIFIERS and mapped not in normalized:
            normalized.append(mapped)
    return normalized
