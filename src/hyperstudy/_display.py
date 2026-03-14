"""Rich display helpers for Jupyter and marimo notebooks."""

from __future__ import annotations

from typing import Any


class ExperimentInfo:
    """Wrapper around an experiment dict with ``_repr_html_`` for notebooks."""

    def __init__(self, data: dict[str, Any]):
        self._data = data

    def __getitem__(self, key):
        return self._data[key]

    def __contains__(self, key):
        return key in self._data

    def get(self, key, default=None):
        return self._data.get(key, default)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)

    def __repr__(self):
        name = self._data.get("name", "Unknown")
        eid = self._data.get("id", "?")
        return f"Experiment({eid!r}, name={name!r})"

    def _repr_html_(self) -> str:
        d = self._data
        rows = ""
        display_fields = [
            ("ID", "id"),
            ("Name", "name"),
            ("Description", "description"),
            ("Owner", "ownerEmail"),
            ("Rooms", "roomCount"),
            ("Participants", "participantCount"),
            ("Created", "createdAt"),
            ("Updated", "updatedAt"),
        ]
        for label, key in display_fields:
            val = d.get(key)
            if val is not None:
                rows += (
                    f"<tr><th style='text-align:left;padding:4px 12px 4px 0'>"
                    f"{label}</th><td style='padding:4px 0'>{val}</td></tr>"
                )
        return (
            "<div style='font-family:system-ui,sans-serif;max-width:600px'>"
            f"<h4 style='margin:0 0 8px'>Experiment: {d.get('name', '?')}</h4>"
            f"<table style='border-collapse:collapse'>{rows}</table></div>"
        )
