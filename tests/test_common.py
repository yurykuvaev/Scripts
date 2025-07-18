"""Tests for the shared utilities in _common.py.

Lightweight — no AWS calls, no botocore mocking. Just argument parsing
and parse_kv_pairs validation logic, the parts that have non-trivial
behavior.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common import common_arg_parser, parse_kv_pairs  # noqa: E402


class TestParseKvPairs:
    def test_empty_input(self) -> None:
        assert parse_kv_pairs([]) == {}
        assert parse_kv_pairs(None) == {}  # type: ignore[arg-type]

    def test_single_pair(self) -> None:
        assert parse_kv_pairs(["Product=foo"]) == {"Product": "foo"}

    def test_multiple_pairs(self) -> None:
        result = parse_kv_pairs(["A=1", "B=2", "C=hello world"])
        assert result == {"A": "1", "B": "2", "C": "hello world"}

    def test_value_with_equals(self) -> None:
        # Only the FIRST = is a separator.
        assert parse_kv_pairs(["URL=https://x.com?a=b"]) == {"URL": "https://x.com?a=b"}

    def test_empty_value_allowed(self) -> None:
        assert parse_kv_pairs(["Tag="]) == {"Tag": ""}

    def test_missing_equals_raises(self) -> None:
        with pytest.raises(argparse.ArgumentTypeError, match="KEY=VALUE"):
            parse_kv_pairs(["broken"])

    def test_empty_key_raises(self) -> None:
        with pytest.raises(argparse.ArgumentTypeError, match="empty key"):
            parse_kv_pairs(["=value"])


class TestCommonArgParser:
    def test_defaults(self) -> None:
        p = common_arg_parser("test")
        args = p.parse_args([])
        assert args.region is None
        assert args.dry_run is False
        assert args.verbose is False

    def test_flags(self) -> None:
        p = common_arg_parser("test")
        args = p.parse_args(["--region", "us-west-2", "--dry-run", "-v"])
        assert args.region == "us-west-2"
        assert args.dry_run is True
        assert args.verbose is True
