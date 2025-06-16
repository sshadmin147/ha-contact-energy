"""Contact Energy API."""

import logging
import requests
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class ContactEnergyApi:
    """Class for Contact Energy API."""

    def __init__(self, hass: HomeAssistant, email, password):
        """Initialise Contact Energy API."""
        self._hass = hass
        self._api_token = ""
        self._api_session = ""
        self._contractId = ""
        self._accountId = ""
        self._url_base = "https://api.contact-digital-prod.net"
        self._api_key = "wg8mXRp7kQ82aOT7mTkzl9fsULf1sEcu7WMGtn6C"  # ← UPDATED
        self._email = email
        self._password = password

    async def login(self):
        """Login to the Contact Energy API."""
        headers = {"x-api-key": self._api_key}
        data = {"username": self._email, "password": self._password}

        def do_login():
            return requests.post(self._url_base + "/login/v2", json=data, headers=headers)

        loginResult = await self._hass.async_add_executor_job(do_login)

        if loginResult.status_code == requests.codes.ok:
            jsonResult = loginResult.json()
            self._api_token = jsonResult["token"]
            _LOGGER.debug("Logged in")
            await self.refresh_session()
            return True
        else:
            _LOGGER.error("Failed to login - check the username and password are valid: %s", loginResult.text)
            return False

    async def refresh_session(self):
        """Refresh the session."""
        headers = {"x-api-key": self._api_key}
        data = {"username": self._email, "password": self._password}

        def do_refresh():
            return requests.post(self._url_base + "/login/v2/refresh", json=data, headers=headers)

        loginResult = await self._hass.async_add_executor_job(do_refresh)

        if loginResult.status_code == requests.codes.ok:
            jsonResult = loginResult.json()
            self._api_session = jsonResult["session"]
            _LOGGER.debug("Refreshed session")
            await self.get_accounts()
            return True
        else:
            _LOGGER.error("Failed to refresh session - check credentials: %s", loginResult.text)
            return False

    async def get_accounts(self):
        """Get the first account that we see."""
        headers = {
            "x-api-key": self._api_key,
            "cookie": f"userAuth={self._api_session}",
        }

        def do_get_accounts():
            return requests.get(self._url_base + "/customer/v2?fetchAccounts=true", headers=headers)

        result = await self._hass.async_add_executor_job(do_get_accounts)

        if result.status_code == requests.codes.ok:
            _LOGGER.debug("Retrieved accounts")
            data = result.json()
            self._accountId = data["accounts"][0]["id"]
            self._contractId = data["accounts"][0]["contracts"][0]["contractId"]
            return True
        else:
            _LOGGER.error("Failed to fetch customer accounts: %s", result.text)
            return False

    async def get_usage(self, year, month, day):
        """Update our usage data."""
        headers = {
            "x-api-key": self._api_key,
            "authorization": self._api_token,
            "cookie": f"userAuth={self._api_session}",
        }

        def do_get_usage():
            return requests.post(
                f"{self._url_base}/usage/v2/{self._contractId}"
                f"?ba={self._accountId}&interval=hourly"
                f"&from={year}-{month.zfill(2)}-{day.zfill(2)}"
                f"&to={year}-{month.zfill(2)}-{day.zfill(2)}",
                headers=headers,
                json=None,  # Send null as body
            )

        response = await self._hass.async_add_executor_job(do_get_usage)

        if response.status_code == requests.codes.ok:
            data = response.json()
            if not data:
                _LOGGER.info("Fetched usage data for %s/%s/%s, but got nothing", year, month, day)
            return data
        else:
            _LOGGER.error("Failed to fetch usage data for %s/%s/%s", year, month, day)
            _LOGGER.debug(response)
            return False
