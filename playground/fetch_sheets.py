"""Read the map source sheet using credentials supplied by the environment."""

import os

import requests


def fetch_sheet():
    api_key = os.environ.get("GOOGLE_API_KEY")
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    if not api_key or not sheet_id:
        raise RuntimeError("Set GOOGLE_API_KEY and GOOGLE_SHEET_ID before fetching a sheet")
    response = requests.get(
        f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Sheet1!A1:C3",
        params={"key": api_key},
        timeout=15,
    )
    response.raise_for_status()
    return response.json().get("values", [])
