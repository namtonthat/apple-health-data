"""Thin gspread wrapper — the only module that talks to the Sheets API."""

from __future__ import annotations

import json

import gspread

from exports.gsheet.model import CellWrite


def a1(row: int, col: int) -> str:
    """0-based (row, col) to A1 notation."""
    letters = ""
    col += 1
    while col:
        col, rem = divmod(col - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return f"{letters}{row + 1}"


class SheetClient:
    def __init__(self, spreadsheet_id: str, service_account_json: str):
        creds = json.loads(service_account_json)
        self._spreadsheet = gspread.service_account_from_dict(creds).open_by_key(spreadsheet_id)

    def list_tabs(self) -> list[str]:
        return [ws.title for ws in self._spreadsheet.worksheets()]

    def get_grid(self, tab: str) -> list[list[str]]:
        return self._spreadsheet.worksheet(tab).get_all_values()

    def batch_write(self, tab: str, writes: list[CellWrite]) -> None:
        if not writes:
            return
        payload = [{"range": a1(w.row, w.col), "values": [[w.value]]} for w in writes]
        self._spreadsheet.worksheet(tab).batch_update(payload, value_input_option="USER_ENTERED")
