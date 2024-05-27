"""Switch platform for tuya_smartir_ac."""
from __future__ import annotations

from homeassistant.components.remote import RemoteEntity, RemoteEntityDescription

from .const import DOMAIN
from .coordinator import BlueprintDataUpdateCoordinator
from .entity import IntegrationBlueprintEntity

from collections.abc import Iterable

ENTITY_DESCRIPTIONS = (
    RemoteEntityDescription(
        key="tuya_smartir_ac",
        name="Fake Remote",
        icon="mdi:format-quote-close",
    ),
)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the remove platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        FakeRemote(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class FakeRemote(IntegrationBlueprintEntity, RemoteEntity):
    """fake remote entity for debugging"""

    def __init__(
        self,
        coordinator: BlueprintDataUpdateCoordinator,
        entity_description: RemoteEntityDescription,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator)
        self.entity_description = entity_description

    def send_command(self, command: Iterable[str], **kwargs):
        """Send commands to a device."""
        print(f"send_command: {command}")
