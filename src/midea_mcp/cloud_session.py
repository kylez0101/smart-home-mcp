import json
import logging
import types
from datetime import datetime, timezone
from hashlib import md5, sha256
from secrets import token_hex, token_urlsafe
from time import time

import hmac as hmac_mod
import requests
from midea_beautiful import MideaCloud
from midea_beautiful.exceptions import CloudAuthenticationError
from midea_beautiful.midea import SUPPORTED_APPS

_LOGGER = logging.getLogger(__name__)

# ---------- MeijuCloud-specific constants (from midea-local v6.6.0) ----------
MEIJU_LOGIN_KEY = "ad0ee21d48a64bf49f4fb583ab76e799"
MEIJU_IOT_KEY = bytes.fromhex(
    format(9795516279659324117647275084689641883661667, "x")
).decode()
MEIJU_HMAC_KEY = bytes.fromhex(
    format(117390035944627627450677220413733956185864939010425, "x")
).decode()
MEIJU_FIXED_KEY = format(10864842703515613082, "x").encode("ascii")


def _meiju_encrypt_password(login_id: str, password: str) -> str:
    h = sha256(password.encode("ascii")).hexdigest()
    return sha256((login_id + h + MEIJU_LOGIN_KEY).encode("ascii")).hexdigest()


def _meiju_encrypt_iam_password(_login_id: str, password: str) -> str:
    first = md5(password.encode("ascii")).hexdigest()
    return md5(first.encode("ascii")).hexdigest()


def _aes_decrypt_ecb(data_hex: str, key: bytes) -> str:
    """AES ECB decrypt, matching midea-local's aes_decrypt_with_fixed_key."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    raw = bytes.fromhex(data_hex)
    decryptor = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    padded = decryptor.update(raw) + decryptor.finalize()
    # PKCS7 unpad
    pad_len = padded[-1]
    return padded[:-pad_len].decode()


def _meiju_sign(data_str: str, random: str) -> str:
    """HMAC-SHA256 sign matching midea-local CloudSecurity.sign for MeijuCloud."""
    msg = MEIJU_IOT_KEY + data_str + random
    return hmac_mod.new(
        MEIJU_HMAC_KEY.encode("ascii"), msg.encode("ascii"), sha256
    ).hexdigest()


def _meiju_login_proxied(cloud: MideaCloud) -> None:
    """Custom _login_proxied for MeijuCloud, bypassing midea_beautiful's broken impl."""
    login_id = cloud._login_id
    stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H%M%S")
    cloud._header_access_token = ""
    cloud._uid = ""

    iampwd = _meiju_encrypt_iam_password(login_id, cloud._password)
    password = _meiju_encrypt_password(login_id, cloud._password)

    app = SUPPORTED_APPS["MeijuCloud"]
    device_id = sha256(f"Hello, {cloud._account}!".encode("ascii")).hexdigest()[:16]

    data = {
        "iotData": {
            "clientType": 1,
            "deviceId": device_id,
            "iampwd": iampwd,
            "iotAppId": str(app["appid"]),
            "loginAccount": cloud._account,
            "password": password,
            "reqId": token_hex(16),
            "stamp": stamp,
        },
        "data": {
            "appKey": app["appkey"],
            "deviceId": device_id,
            "platform": 2,
        },
        "timestamp": stamp,
        "stamp": stamp,
        "reqId": token_hex(16),
    }

    url = cloud._api_url + "/mj/user/login"
    dump_data = json.dumps(data)
    random_str = str(int(time()))
    sign = _meiju_sign(dump_data, random_str)

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "secretVersion": "1",
        "sign": sign,
        "random": random_str,
    }

    _LOGGER.debug("MeijuCloud login request to %s", url)
    resp = requests.post(url=url, data=dump_data, headers=headers, timeout=10)
    resp.raise_for_status()
    payload = resp.json()

    if str(payload.get("code", "-1")) != "0":
        raise CloudAuthenticationError(
            int(payload.get("code", -1)),
            payload.get("msg", "Unknown error"),
            cloud._account,
        )

    session = payload["data"]
    cloud._session = session
    cloud._uid = str(session.get("uid", ""))
    _LOGGER.debug("MeijuCloud UID=%s", cloud._uid)

    if mdata := session.get("mdata"):
        cloud._header_access_token = mdata["accessToken"]

    # Decrypt AES key with fixed key (ECB mode) — this is the critical difference
    # from midea_beautiful which uses SHA256(appKey)-derived keys with CBC.
    decrypted_key = _aes_decrypt_ecb(session["key"], MEIJU_FIXED_KEY)
    # Directly set internal _data_key (used by aes_encrypt_string/aes_decrypt_string)
    # and _data_iv=None to use ECB mode for subsequent operations.
    cloud._security._data_key = decrypted_key
    cloud._security._data_iv = None


def _meiju_list_appliances(cloud: MideaCloud, force: bool = False) -> list:
    """MeijuCloud uses different endpoints: list homes first, then devices per home."""
    if not force and cloud._appliance_list:
        return cloud._appliance_list

    homes = cloud.api_request("/v1/homegroup/list/get", {})
    cloud._appliance_list = []
    for home in homes.get("homeList", []):
        home_id = home["homegroupId"]
        detail = cloud.api_request(
            "/v1/appliance/home/list/get", {"homegroupId": home_id}
        )
        for h in detail.get("homeList", []):
            for room in h.get("roomList", []):
                for item in room.get("applianceList", []):
                    sn_encrypted = item.get("sn", "")
                    try:
                        sn = cloud._security.aes_decrypt_string(sn_encrypted) if sn_encrypted else "Unknown"
                    except Exception:
                        sn = "Unknown"
                    app_info = {
                        "id": item.get("applianceCode"),
                        "name": item.get("name"),
                        "sn": sn,
                        "type": item.get("type"),
                        "modelNumber": item.get("modelNumber"),
                    }
                    cloud._appliance_list.append(app_info)
    return cloud._appliance_list


def _create_meiju_cloud(account: str, password: str) -> MideaCloud:
    """Create and authenticate a MideaCloud for MeijuCloud (美的美居)."""
    app = SUPPORTED_APPS["MeijuCloud"]
    cloud = MideaCloud(
        appkey=app["appkey"],
        account=account,
        password=password,
        appid=app["appid"],
        hmac_key=MEIJU_HMAC_KEY,
        iot_key=MEIJU_IOT_KEY,
        api_url=app["apiurl"],
        proxied=app.get("proxied"),
        sign_key=app["signkey"],
    )
    # Skip deprecated _get_region endpoint
    cloud._country_code = "CN"
    # Patch encryption methods
    cloud._security.encrypt_password = _meiju_encrypt_password
    cloud._security.encrypt_iam_password = _meiju_encrypt_iam_password
    # Replace login with correct MeijuCloud implementation
    cloud._login_proxied = types.MethodType(
        lambda self: _meiju_login_proxied(self), cloud
    )
    # Replace list_appliances with MeijuCloud-specific endpoint
    cloud.list_appliances = types.MethodType(
        lambda self, force=False: _meiju_list_appliances(self, force), cloud
    )
    cloud.authenticate()
    return cloud


def _create_cloud(account: str, password: str, appname: str) -> MideaCloud:
    """Create and authenticate a MideaCloud instance."""
    if appname == "MeijuCloud":
        return _create_meiju_cloud(account, password)

    app = SUPPORTED_APPS[appname]
    cloud = MideaCloud(
        appkey=app["appkey"],
        account=account,
        password=password,
        appid=app["appid"],
        hmac_key=app.get("hmackey"),
        iot_key=app.get("iotkey"),
        api_url=app["apiurl"],
        proxied=app.get("proxied"),
        sign_key=app["signkey"],
    )
    if app.get("proxied"):
        cloud._country_code = "CN"
    cloud.authenticate()
    return cloud


class CloudSession:
    def __init__(self, account: str, password: str, appname: str):
        self._account = account
        self._password = password
        self._appname = appname
        self._cloud: MideaCloud | None = None

    def get_cloud(self) -> MideaCloud:
        """Returns authenticated MideaCloud instance, re-authenticating if needed."""
        if self._cloud is not None:
            return self._cloud
        return self._authenticate()

    def invalidate(self) -> None:
        """Forces re-authentication on next call."""
        self._cloud = None

    def _authenticate(self) -> MideaCloud:
        try:
            _LOGGER.info("Authenticating with Midea cloud...")
            self._cloud = _create_cloud(
                self._account, self._password, self._appname,
            )
            return self._cloud
        except CloudAuthenticationError:
            _LOGGER.warning("Cloud authentication failed, retrying...")
            self._cloud = None
            self._cloud = _create_cloud(
                self._account, self._password, self._appname,
            )
            return self._cloud
