"""Contact Energy sensors with broadband included."""

from datetime import datetime, timedelta

import logging
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, UnitOfEnergy
from homeassistant.components.sensor import SensorEntity

from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
)

from .api import ContactEnergyApi

from .const import (
    DOMAIN,
    SENSOR_USAGE_NAME,
    CONF_USAGE_DAYS,
)

NAME = DOMAIN
ISSUEURL = "https://github.com/codyc1515/hacs_contact_energy/issues"

STARTUP = f"""
-------------------------------------------------------------------
{NAME}
This is a custom component
If you have any issues with this you need to open an issue here:
{ISSUEURL}
-------------------------------------------------------------------
"""

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_EMAIL): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_USAGE_DAYS, default=10): cv.positive_int,
    }
)

SCAN_INTERVAL = timedelta(hours=3)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the platform async."""
    email = config.get(CONF_EMAIL)
    password = config.get(CONF_PASSWORD)
    usage_days = config.get(CONF_USAGE_DAYS)

    api = ContactEnergyApi(hass, email, password)

    _LOGGER.debug("Setting up sensor(s)...")

    sensors = [
        ContactEnergyUsageSensor(SENSOR_USAGE_NAME, api, usage_days),
        ContactEnergyBroadbandSensor("Broadband Plan", api),
    ]
    async_add_entities(sensors, True)


class ContactEnergyUsageSensor(SensorEntity):
    """Define Contact Energy Usage sensor."""

    def __init__(self, name, api, usage_days):
        self._name = name
        self._icon = "mdi:meter-electric"
        self._state = 0
        self._unit_of_measurement = "kWh"
        self._unique_id = f"{DOMAIN}_usage"
        self._device_class = "energy"
        self._state_class = "total"
        self._state_attributes = {}
        self._usage_days = usage_days
        self._api = api

    @property
    def name(self): return self._name

    @property
    def icon(self): return self._icon

    @property
    def state(self): return self._state

    @property
    def extra_state_attributes(self): return self._state_attributes

    @property
    def unit_of_measurement(self): return self._unit_of_measurement

    @property
    def state_class(self): return self._state_class

    @property
    def device_class(self): return self._device_class

    @property
    def unique_id(self): return self._unique_id

    async def async_update(self):
        _LOGGER.debug("Beginning usage update")

        if not self._api._api_token:
            _LOGGER.info("Logging in...")
            if not await self._api.login():
                _LOGGER.error("Login failed. Check credentials.")
                return

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        kWhStats, dollarStats, freeKWhStats = [], [], []
        kWhSum = dollarSum = freeKWhSum = 0
        currency = 'NZD'

        for i in range(self._usage_days):
            day = today - timedelta(days=self._usage_days - i)
            usage = await self._api.get_usage(day.year, day.month, day.day)

            if usage:
                for point in usage:
                    ts = datetime.strptime(point["date"], "%Y-%m-%dT%H:%M:%S.%f%z")
                    value = float(point["value"])

                    if point.get("currency"):
                        currency = point["currency"]

                    if point.get("offpeakValue") == "0.00":
                        kWhSum += value
                        dollarSum += float(point.get("dollarValue") or 0)
                    else:
                        freeKWhSum += value

                    kWhStats.append(StatisticData(start=ts, sum=kWhSum))
                    dollarStats.append(StatisticData(start=ts, sum=dollarSum))
                    freeKWhStats.append(StatisticData(start=ts, sum=freeKWhSum))

        async_add_external_statistics(
            self.hass,
            StatisticMetaData(
                has_mean=False, has_sum=True, name="ContactEnergy", source=DOMAIN,
                statistic_id=f"{DOMAIN}:energy_consumption", unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            ),
            kWhStats,
        )

        async_add_external_statistics(
            self.hass,
            StatisticMetaData(
                has_mean=False, has_sum=True, name="ContactEnergyDollars", source=DOMAIN,
                statistic_id=f"{DOMAIN}:energy_consumption_in_dollars", unit_of_measurement=currency,
            ),
            dollarStats,
        )

        async_add_external_statistics(
            self.hass,
            StatisticMetaData(
                has_mean=False, has_sum=True, name="FreeContactEnergy", source=DOMAIN,
                statistic_id=f"{DOMAIN}:free_energy_consumption", unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            ),
            freeKWhStats,
        )


class ContactEnergyBroadbandSensor(SensorEntity):
    """Sensor for broadband plan info."""

    def __init__(self, name, api):
        self._name = name
        self._api = api
        self._state = None
        self._attributes = {}
        self._icon = "mdi:lan"
        self._unique_id = f"{DOMAIN}_broadband"

    @property
    def name(self): return self._name

    @property
    def state(self): return self._state

    @property
    def icon(self): return self._icon

    @property
    def extra_state_attributes(self): return self._attributes

    @property
    def unique_id(self): return self._unique_id

    async def async_update(self):
        _LOGGER.debug("Updating broadband plan details...")
        if not self._api._api_token:
            _LOGGER.info("Logging in...")
            if not await self._api.login():
                _LOGGER.error("Login failed. Cannot fetch broadband plan.")
                return

        plan = await self._api.get_plan_details()
        if plan:
            try:
                broadband = next(
                    s for p in plan["premises"] for s in p["services"] if s["serviceType"] == "BROADBAND"
                )
                self._state = broadband["planDetails"].get("externalPlanDescription")
                self._attributes = broadband["planDetails"]
            except Exception as e:
                _LOGGER.error(f"Failed to parse broadband plan details: {e}")
