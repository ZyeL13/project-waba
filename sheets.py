# sheets.py
import aiohttp
import asyncio
import logging
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import config
from retry import retry

logger = logging.getLogger("sheets")

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class SheetsClient:
    def __init__(self, credentials_file, spreadsheet_id):
        self.creds = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=SCOPES
        )
        self.spreadsheet_id = spreadsheet_id
        self._token = None
        self._token_expiry = 0
        self._lock = asyncio.Lock()

    async def _get_token(self):
        """Dapatkan access token, refresh jika perlu"""
        now = asyncio.get_event_loop().time()
        if self._token and now < self._token_expiry - 60:
            return self._token
        async with self._lock:
            # double-check
            if self._token and now < self._token_expiry - 60:
                return self._token
            # Refresh token blocking → jalankan di thread executor
            loop = asyncio.get_event_loop()
            token = await loop.run_in_executor(None, self._refresh_token_sync)
            self._token = token
            self._token_expiry = now + 3500  # token berlaku 1 jam
            return token

    def _refresh_token_sync(self):
        from google.auth.transport.requests import Request
        request = Request()
        self.creds.refresh(request)
        return self.creds.token

    @retry(max_retries=3, base_delay=1, max_delay=5, exceptions=(aiohttp.ClientError, asyncio.TimeoutError, ValueError))
    async def batch_append(self, rows):
        """
        rows: list of list nilai, misal [["op123","add","pensil","1714123456"], ...]
        """
        token = await self._get_token()
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/{config.RANGE_NAME}:append"
        params = {
            "valueInputOption": "USER_ENTERED",
            "insertDataOption": "INSERT_ROWS"
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        body = {
            "values": rows
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, params=params, json=body) as resp:
                if resp.status in [200, 201]:
                    data = await resp.json()
                    logger.info(f"Batch write sukses: {len(rows)} rows, updatedRange={data.get('updates',{}).get('updatedRange')}")
                else:
                    text = await resp.text()
                    logger.error(f"Google Sheets API error {resp.status}: {text}")
                    raise ValueError(f"Sheets API error {resp.status}: {text}")
