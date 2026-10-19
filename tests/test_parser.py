"""Unit tests for SerialDataParser.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pytest
from app.serial.parser import SerialDataParser

def test_parse_legacy_text_format():
    # User's exact Arduino format: "Light: 222 | Motion: YES"
    line = "Light: 222 | Motion: YES"
    parsed = SerialDataParser.parse_line(line)
    assert parsed is not None
    assert parsed["light_raw"] == 222
    assert parsed["motion"] == 1
    assert parsed["temperature"] is None

    line2 = "Light: 185 | Motion: NO"
    parsed2 = SerialDataParser.parse_line(line2)
    assert parsed2 is not None
    assert parsed2["light_raw"] == 185
    assert parsed2["motion"] == 0

def test_parse_csv_format():
    # Basic CSV
    line = "222,1"
    parsed = SerialDataParser.parse_line(line)
    assert parsed is not None
    assert parsed["light_raw"] == 222
    assert parsed["motion"] == 1

    # CSV with future DHT11 temp & humidity
    line_extended = "235,0,26.4,55.2"
    parsed_ext = SerialDataParser.parse_line(line_extended)
    assert parsed_ext is not None
    assert parsed_ext["light_raw"] == 235
    assert parsed_ext["motion"] == 0
    assert parsed_ext["temperature"] == 26.4
    assert parsed_ext["humidity"] == 55.2

def test_parse_json_format():
    line = '{"light": 412, "motion": 1, "temperature": 27.1, "humidity": 60.5}'
    parsed = SerialDataParser.parse_line(line)
    assert parsed is not None
    assert parsed["light_raw"] == 412
    assert parsed["motion"] == 1
    assert parsed["temperature"] == 27.1
    assert parsed["humidity"] == 60.5

def test_parse_json_preserves_zero_sensor_values():
    parsed = SerialDataParser.parse_line('{"light": 0, "motion": 0}')
    assert parsed is not None
    assert parsed["light_raw"] == 0
    assert parsed["motion"] == 0
    assert SerialDataParser.parse_line('{"light": 100}') is None

def test_parse_json_null_temperature_and_humidity():
    parsed = SerialDataParser.parse_line(
        '{"light": 100, "motion": 0, "temperature": null, "humidity": null}'
    )
    assert parsed is not None
    assert parsed["temperature"] is None
    assert parsed["humidity"] is None

def test_parse_malformed():
    assert SerialDataParser.parse_line("") is None
    assert SerialDataParser.parse_line("Hello Arduino") is None
    assert SerialDataParser.parse_line("Random noise 12345") is None
