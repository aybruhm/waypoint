from uuid import UUID

from src.domain.entities.events.models import EventModel


class EventSchemaV1:
    """
    Deserializer for events with no compression columns.
    """

    def deserialize(self, raw: dict) -> EventModel:
        return EventModel(
            id=UUID(str(raw["id"])),
            execution_id=UUID(str(raw["execution_id"])),
            step_number=raw["step_number"],
            step_name=raw["step_name"],
            input=raw.get("input") or {},
            output=raw.get("output") or {},
            status=raw["status"],
            side_effects=raw.get("side_effects"),
            cached=raw.get("cached", False),
            error=raw.get("error"),
            duration_ms=raw.get("duration_ms"),
            created_at=raw.get("created_at", ""),
        )


class EventSchemaV2(EventSchemaV1):
    """
    Deserializer for events that has compression metadata fields. Inherits V1 to avoid duplicating base field mapping.
    """

    def deserialize(self, raw: dict) -> EventModel:
        # The base EventModel doesn't yet carry compression fields as attributes;
        # that metadata lives in state_metadata table. This class exists as a
        # forward hook — add any V2-specific field transforms here when needed.
        return super().deserialize(raw)


class EventSchemaRegistry:
    """
    Maps schema_version → deserializer.
    """

    _registry: dict[int, EventSchemaV1] = {
        1: EventSchemaV1(),
        2: EventSchemaV2(),
    }

    @classmethod
    def get(cls, version: int) -> EventSchemaV1:
        deserializer = cls._registry.get(version)
        if deserializer is None:
            raise ValueError(
                f"Unknown event schema version: {version}. "
                f"Known versions: {list(cls._registry)}"
            )
        return deserializer

    @classmethod
    def deserialize(cls, raw: dict) -> EventModel:
        version = raw.get("schema_version") or 1
        return cls.get(version).deserialize(raw)
