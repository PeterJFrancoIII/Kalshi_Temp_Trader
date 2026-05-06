import os
import json
import pytest
from unittest.mock import patch, mock_open
from shared.manual_corrections import (
    load_manual_corrections, 
    get_correction_for_date, 
    is_excluded_from_learning, 
    get_market_open_time_et
)

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

MOCK_CONFIG = {
    "corrections_version": 1,
    "dates": {
        "2026-05-05": {
            "station": "KMIA",
            "corrected_official_max_temp_f": 88,
            "exclude_from_learning": True,
            "settlement_status": "needs_manual_review"
        },
        "2026-05-07": {
            "market_open_time_et": "11:00"
        }
    }
}

def test_load_manual_corrections():
    with patch("builtins.open", mock_open(read_data=json.dumps(MOCK_CONFIG))):
        with patch("pathlib.Path.exists", return_value=True):
            corrections = load_manual_corrections()
            assert "2026-05-05" in corrections
            assert "2026-05-07" in corrections

def test_is_excluded_from_learning():
    with patch("builtins.open", mock_open(read_data=json.dumps(MOCK_CONFIG))):
        with patch("pathlib.Path.exists", return_value=True):
            assert is_excluded_from_learning("2026-05-05") is True
            assert is_excluded_from_learning("2026-05-07") is False

def test_get_market_open_time_et():
    with patch("builtins.open", mock_open(read_data=json.dumps(MOCK_CONFIG))):
        with patch("pathlib.Path.exists", return_value=True):
            assert get_market_open_time_et("2026-05-07") == "11:00"
            assert get_market_open_time_et("2026-05-05") is None

def test_missing_file_fails_safely():
    with patch("pathlib.Path.exists", return_value=False):
        assert load_manual_corrections() == {}
        assert is_excluded_from_learning("2026-05-05") is False
        assert get_market_open_time_et("2026-05-07") is None

def test_invalid_json_fails_safely():
    with patch("builtins.open", mock_open(read_data="invalid json")):
        with patch("pathlib.Path.exists", return_value=True):
            assert load_manual_corrections() == {}

@patch("shared.manual_corrections.load_manual_corrections")
def test_get_correction_for_date(mock_load):
    mock_load.return_value = MOCK_CONFIG["dates"]
    correction = get_correction_for_date("2026-05-05")
    assert correction["corrected_official_max_temp_f"] == 88
