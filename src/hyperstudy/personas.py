"""Persona (agent library) methods, mixed into the HyperStudy client.

Personas are reusable AI-agent definitions. These methods target the
/api/v3/personas routes and require API-key scopes ``read:personas`` /
``write:personas``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import Persona


def _persona_payload(persona: "Persona | None", kwargs: dict[str, Any]) -> dict[str, Any]:
    """Build a wire-ready persona payload from a typed Persona and/or kwargs."""
    from .models import Persona as PersonaModel
    from .models import camelize_wire

    payload: dict[str, Any] = {}
    if persona is not None:
        if not isinstance(persona, PersonaModel):
            raise TypeError("persona must be a hyperstudy.Persona instance")
        payload.update(persona.model_dump(by_alias=True, exclude_none=True))
    if kwargs:
        payload.update(camelize_wire(kwargs))
    # The server hard-discards offlineCognition (offline loops now live inside
    # cognition.config.contexts.<name>.offline), so never send it — including
    # when a Persona was rebuilt from an older API response via extra fields.
    payload.pop("offlineCognition", None)
    payload.pop("offline_cognition", None)
    return payload


class PersonaMixin:
    """Persona CRUD methods for the HyperStudy client."""

    def list_personas(self, *, output: str = "pandas"):
        """List personas you own or can view (organization-scoped).

        Args:
            output: ``"pandas"`` (default), ``"polars"``, or ``"dict"``.
        """
        body = self._transport.get("personas")
        return self._convert_output(body.get("data", []), output)

    def get_persona(self, persona_id: str) -> dict[str, Any]:
        """Get one persona by ID."""
        body = self._transport.get(f"personas/{persona_id}")
        return body.get("data", {})

    def create_persona(
        self,
        *,
        persona: "Persona | None" = None,
        name: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a persona.

        Two equivalent ways to call this:

        - **Typed builder** (recommended): pass a :class:`Persona` instance.
        - **Kwargs**: pass snake_case fields directly
          (``create_persona(name="Confederate", provider="anthropic", ...)``).

        Returns:
            The created persona (including its ``id``).
        """
        if name is not None:
            kwargs["name"] = name
        payload = _persona_payload(persona, kwargs)
        if not payload.get("name"):
            raise ValueError("Persona name is required")
        body = self._transport.post("personas", json=payload)
        return body.get("data", {})

    def update_persona(
        self,
        persona_id: str,
        *,
        persona: "Persona | None" = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update a persona (merge-patch).

        Only the fields you pass are changed; everything else on the stored
        persona is preserved.
        """
        payload = _persona_payload(persona, kwargs)
        if not payload:
            raise ValueError("No fields to update")
        body = self._transport.put(f"personas/{persona_id}", json=payload)
        return body.get("data", {})

    def delete_persona(self, persona_id: str) -> None:
        """Delete a persona."""
        self._transport.delete(f"personas/{persona_id}")

    def duplicate_persona(self, persona_id: str) -> dict[str, Any]:
        """Copy a viewable persona into a new private persona you own.

        Returns:
            The new persona (named ``"<original name> (copy)"``).
        """
        body = self._transport.post(f"personas/{persona_id}/duplicate")
        return body.get("data", {})

    def get_cognition_catalog(self) -> dict[str, Any]:
        """Fetch the cognition authoring catalog.

        Lists the valid building blocks for persona ``cognition`` configs.
        Requires the ``read:personas`` scope.

        Returns:
            Dict with ``abilities``, ``recipes``, and ``offlineRecipes``.
        """
        body = self._transport.get("agent-cognition/catalog")
        data = body.get("data", [])
        return data[0] if isinstance(data, list) and data else data
