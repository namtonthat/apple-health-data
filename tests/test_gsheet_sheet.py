from unittest.mock import MagicMock, patch

from exports.gsheet.model import CellWrite
from exports.gsheet.sheet import SheetClient, a1


def test_a1_conversion():
    assert a1(0, 0) == "A1"
    assert a1(11, 1) == "B12"
    assert a1(11, 27) == "AB12"
    assert a1(0, 51) == "AZ1"


def test_batch_write_builds_single_batch_update():
    with patch("exports.gsheet.sheet.gspread") as mock_gspread:
        ws = MagicMock()
        (
            mock_gspread.service_account_from_dict.return_value.open_by_key.return_value.worksheet.return_value
        ) = ws

        client = SheetClient("sheet-id", '{"type": "service_account"}')
        client.batch_write(
            "Daily",
            [CellWrite(row=2, col=6, value="70.3"), CellWrite(row=2, col=4, value="7.2")],
        )

        ws.batch_update.assert_called_once_with(
            [
                {"range": "G3", "values": [["70.3"]]},
                {"range": "E3", "values": [["7.2"]]},
            ],
            value_input_option="USER_ENTERED",
        )


def test_batch_write_no_writes_is_noop():
    with patch("exports.gsheet.sheet.gspread") as mock_gspread:
        ws = MagicMock()
        (
            mock_gspread.service_account_from_dict.return_value.open_by_key.return_value.worksheet.return_value
        ) = ws
        client = SheetClient("sheet-id", '{"type": "service_account"}')
        client.batch_write("Daily", [])
        ws.batch_update.assert_not_called()
