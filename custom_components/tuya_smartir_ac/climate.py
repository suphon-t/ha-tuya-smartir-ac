import logging
from homeassistant.core import HomeAssistant
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity, ExtraStoredData
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, ClimateEntityDescription
from homeassistant.components.climate.const import (
    HVACMode,
    ATTR_HVAC_MODE, ATTR_FAN_MODE, ATTR_SWING_MODE,
    FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH,
    SWING_OFF, SWING_VERTICAL, SWING_HORIZONTAL, SWING_BOTH,
)
import tinytuya.Contrib
from .gree_remote import encode_gree_remote, Mode, Fan, VerticalVane, HorizontalVane
import tinytuya

_LOGGER = logging.getLogger(__name__)

ATTR_POWER = 'power'

def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    add_entities([GreeACRemote(config)])

VALID_MODES = {
    "0": HVACMode.AUTO,
    "1": HVACMode.COOL,
    # "2": HVACMode.DRY,
    "3": HVACMode.FAN_ONLY,
    # "4": HVACMode.HEAT,
    "5": HVACMode.OFF,
}

GREE_HVAC_MODES = {
    HVACMode.AUTO: Mode.AUTO,
    HVACMode.COOL: Mode.COOL,
    HVACMode.DRY: Mode.DRY,
    HVACMode.FAN_ONLY: Mode.FAN,
    HVACMode.HEAT: Mode.HEAT,
}

GREE_FAN = {
    FAN_AUTO: Fan.AUTO,
    FAN_LOW: Fan.LOW,
    FAN_MEDIUM: Fan.MEDIUM,
    FAN_HIGH: Fan.HIGH,
}

GREE_VERTICAL_VANE = {
    SWING_OFF: VerticalVane.AUTO,
    SWING_HORIZONTAL: VerticalVane.AUTO,
    SWING_VERTICAL: VerticalVane.SWING_ALL,
    SWING_BOTH: VerticalVane.SWING_ALL,
}

GREE_HORIZONTAL_VANE = {
    SWING_OFF: HorizontalVane.AUTO,
    SWING_HORIZONTAL: HorizontalVane.SWING_ALL,
    SWING_VERTICAL: HorizontalVane.AUTO,
    SWING_BOTH: HorizontalVane.SWING_ALL,
}

class ACState:
    data: dict[str, str | float | None]

    def __init__(self, data: dict[str, str | float | None] = {}):
        self.data = data

    def get(self, key: str):
        return self.data.get(key, None)

    def as_dict(self):
        return {**self.data}

    def copy(self):
        return ACState({**self.data})

    def copy_with(self, data: dict[str, str | float | None]):
        return ACState({**self.data, **data})

class GreeACRemote(ClimateEntity, RestoreEntity):
    _enable_turn_on_off_backwards_compatibility = False

    _remote_entity_id: str
    _state: ACState
    target_state: ACState

    def __init__(self, config: ConfigType):
        self._remote_entity_id = config['remote_entity_id']
        self._attr_unique_id = config['id']
        self._attr_device_info = DeviceInfo(
            # identifiers={(DOMAIN, self.unique_id)},
            name=config['name'],
            # model=VERSION,
            # manufacturer=NAME,
        )
        self._state = ACState({
            ATTR_POWER: False,
            ATTR_HVAC_MODE: HVACMode.AUTO,
            ATTR_TEMPERATURE: 25
        })
        self.target_state = self._state.copy()

    @property
    def supported_features(self):
        return ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF | \
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE | \
            ClimateEntityFeature.SWING_MODE

    @property
    def hvac_modes(self):
        return list(VALID_MODES.values())

    @property
    def fan_modes(self):
        return list([FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH])

    @property
    def swing_modes(self):
        return list([SWING_OFF, SWING_HORIZONTAL, SWING_VERTICAL, SWING_BOTH])

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    @property
    def precision(self):
        return 1

    @property
    def target_temperature_step(self):
        return 1

    @property
    def min_temp(self):
        return 16

    @property
    def max_temp(self):
        return 30

    @property
    def hvac_mode(self):
        power = self._state.get(ATTR_POWER)
        if not power:
            return HVACMode.OFF
        return HVACMode(self._state.get(ATTR_HVAC_MODE))

    @property
    def fan_mode(self):
        return self._state.get(ATTR_FAN_MODE)

    @property
    def target_temperature(self):
        return self._state.get(ATTR_TEMPERATURE)

    @property
    def swing_mode(self):
        return self._state.get(ATTR_SWING_MODE)

    async def async_turn_on(self) -> None:
        if self._state.get(ATTR_HVAC_MODE) == HVACMode.OFF:
            await self.async_set_hvac_mode(HVACMode.COOL)
            return
        await self.async_set_target_state(ATTR_POWER, True)

    async def async_turn_off(self) -> None:
        await self.async_set_target_state(ATTR_POWER, False)

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get("temperature")
        if temperature is None:
            return
        await self.async_set_target_state({ATTR_TEMPERATURE: temperature})

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.OFF:
            await self.async_set_target_state({ATTR_POWER: False})
            return
        await self.async_set_target_state({ATTR_POWER: True, ATTR_HVAC_MODE: hvac_mode})

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        await self.async_set_target_state({ATTR_FAN_MODE: fan_mode})

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        await self.async_set_target_state({ATTR_SWING_MODE: swing_mode})

    async def async_set_target_state(self, data: dict[str, str | float | None]):
        self.target_state = self.target_state.copy_with(data)
        target = self.target_state

        result = encode_gree_remote(
            mode=GREE_HVAC_MODES.get(target.get(ATTR_HVAC_MODE), Mode.AUTO),
            power=target.get(ATTR_POWER),
            fan=GREE_FAN.get(target.get(ATTR_FAN_MODE), Fan.AUTO),
            temp=int(target.get(ATTR_TEMPERATURE)),
            vertical_vane=GREE_VERTICAL_VANE.get(target.get(ATTR_SWING_MODE), VerticalVane.AUTO),
            horizontal_vane=GREE_HORIZONTAL_VANE.get(target.get(ATTR_SWING_MODE), HorizontalVane.AUTO),
        )
        pulses = result.get('pulses')

        b64 = 'b64:'+tinytuya.Contrib.IRRemoteControlDevice.pulses_to_base64(pulses)

        await self.hass.services.async_call('remote', 'send_command', {
            'entity_id': self._remote_entity_id,
            'command': b64,
        })
        self._state = self.target_state

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        old_state = await self.async_get_last_extra_data()
        if not old_state:
            return
        _LOGGER.info(f"Restoring state: {old_state.as_dict()}")
        self._state = ACState(old_state.as_dict())
        self.target_state = self._state.copy()

    @property
    def extra_restore_state_data(self) -> ExtraStoredData | None:
        _LOGGER.info(f"Saving state: {self._state.as_dict()}")
        return self._state
