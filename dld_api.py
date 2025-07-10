import base64
import os
import uuid
from typing import Tuple, Dict, Any, Optional

import requests


DLD_API_URL = "https://viewit.ae/api/dld-qr"


def fetch_listing_details(
    trade_license_number: str,
    listing_number: str,
    auth_token: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> Tuple[Dict[str, Any], str]:
    """Query the DLD API and save the returned base-64 QR image to disk.

    Parameters
    ----------
    trade_license_number : str
        The brokerage's trade licence number.
    listing_number : str
        The Trakheesi permit / listing number.
    auth_token : str
        Bearer token for the DLD API.

    Returns
    -------
    Tuple[Dict[str, Any], str]
        1. The full JSON payload returned by the API (already parsed).
        2. Absolute path to the written PNG containing the QR code.

    Raises
    ------
    RuntimeError
        If the API returns an error or the request fails.
    """
    headers: Dict[str, str] = {
        "Content-Type": "application/json",
    }
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    elif username and password:
        import base64 as _b64
        b64_token = _b64.b64encode(f"{username}:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {b64_token}"
    else:
        raise RuntimeError("Either auth_token or username/password must be provided for DLD API authentication")

    payload = {
        "trade_license_number": trade_license_number,
        "listing_number": listing_number,
    }

    try:
        resp = requests.post(DLD_API_URL, json=payload, headers=headers, timeout=30)
    except requests.RequestException as exc:
        raise RuntimeError(f"Unable to reach DLD API: {exc}") from exc

    if resp.status_code != 200:
        raise RuntimeError(f"DLD API returned HTTP {resp.status_code}: {resp.text[:200]}")

    data: Dict[str, Any] = resp.json()

    if not data.get("status"):
        raise RuntimeError(data.get("message", "Unknown error"))

    try:
        qr_b64: str = data["data"]["result"][0]["validationQr"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("QR code not found in DLD response")

    qr_bytes = base64.b64decode(qr_b64)
    os.makedirs("static", exist_ok=True)
    filename = f"qr_{listing_number}_{uuid.uuid4().hex[:8]}.png"
    output_path = os.path.abspath(os.path.join("static", filename))

    with open(output_path, "wb") as f:
        f.write(qr_bytes)

    return data, output_path 