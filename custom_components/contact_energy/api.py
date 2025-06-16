import requests
from datetime import datetime

class ContactEnergyApi:
    def __init__(self, hass, email, password):
        self.hass = hass
        self.email = email
        self.password = password
        self.api_key = "wg8mXRp7kQ82aOT7mTkzl9fsULf1sEcu7WMGtn6C"
        self.base_url = "https://api.contact-digital-prod.net"
        self.session = requests.Session()
        self._api_token = None
        self._csrf_token = None
        self._account_id = None
        self._contract_id = None
        self._broadband_plan = None

    async def login(self):
        try:
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
            }
            payload = {
                "username": self.email,
                "password": self.password,
            }

            resp = await self.hass.async_add_executor_job(
                lambda: self.session.post(f"{self.base_url}/login/v2", json=payload, headers=headers)
            )
            resp.raise_for_status()
            self._api_token = resp.json()["token"]

            headers = {
                "x-api-key": self.api_key,
                "Authorization": self._api_token,
                "Content-Type": "application/json",
            }
            resp = await self.hass.async_add_executor_job(
                lambda: self.session.post(f"{self.base_url}/login/v2/refresh", json=payload, headers=headers)
            )
            resp.raise_for_status()
            data = resp.json()
            self._csrf_token = data["x-csrf-token"]
            self._session_token = data["session"]

            return await self._fetch_plan_details()

        except Exception as e:
            print(f"Login failed: {e}")
            return False

    async def _fetch_plan_details(self):
        headers = self._auth_headers()
        try:
            resp = await self.hass.async_add_executor_job(
                lambda: self.session.get(
                    f"{self.base_url}/usage/v2/plan-details",
                    headers=headers,
                    params={"ba": "501835449"},
                )
            )
            resp.raise_for_status()
            data = resp.json()

            self._account_id = data["accountId"]

            for s in data["premises"][0]["services"]:
                if s["serviceType"] == "ELEC":
                    self._contract_id = s["contract"]["contractId"]
                elif s["serviceType"] == "BROADBAND":
                    self._broadband_plan = s.get("planDetails", {}).get("externalPlanDescription")

            return self._contract_id is not None

        except Exception as e:
            print(f"Failed to fetch plan details: {e}")
            return False

    async def get_usage(self, year, month, day):
        try:
            from_date = f"{year}-{month.zfill(2)}-01"
            to_date = datetime.now().strftime("%Y-%m-%d")

            headers = self._auth_headers()
            resp = await self.hass.async_add_executor_job(
                lambda: self.session.post(
                    f"{self.base_url}/usage/v2/{self._contract_id}",
                    headers=headers,
                    params={
                        "ba": self._account_id,
                        "interval": "monthly",
                        "from": from_date,
                        "to": to_date,
                    },
                )
            )
            resp.raise_for_status()
            return resp.json()

        except Exception as e:
            print(f"Error fetching usage: {e}")
            return None

    def _auth_headers(self):
        return {
            "User-Agent": "Mozilla/5.0",
            "x-api-key": self.api_key,
            "x-csrf-token": self._csrf_token,
            "Authorization": self._session_token,
            "Origin": "https://myaccount.contact.co.nz",
            "Referer": "https://myaccount.contact.co.nz/",
        }
