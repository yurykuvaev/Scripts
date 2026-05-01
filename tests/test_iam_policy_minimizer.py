"""Tests for the pure-Python helpers in iam_policy_minimizer.

Skips anything that needs CloudTrail or IAM live - focuses on parsing
helpers (statement normalisation, action aggregation, policy rendering).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from iam_policy_minimizer import (
    _actions,
    _statements,
    actions_from_events,
    build_policy,
)


class TestStatements:
    def test_dict_doc(self) -> None:
        doc = {"Statement": [{"Effect": "Allow", "Action": "s3:GetObject"}]}
        assert _statements(doc) == [{"Effect": "Allow", "Action": "s3:GetObject"}]

    def test_string_doc(self) -> None:
        doc = '{"Statement": [{"Effect": "Allow", "Action": "ec2:Describe*"}]}'
        assert _statements(doc) == [{"Effect": "Allow", "Action": "ec2:Describe*"}]

    def test_single_statement_object_normalised(self) -> None:
        doc = {"Statement": {"Effect": "Allow", "Action": "iam:GetUser"}}
        assert _statements(doc) == [{"Effect": "Allow", "Action": "iam:GetUser"}]

    def test_empty(self) -> None:
        assert _statements({}) == []


class TestActionsExtractor:
    def test_string_action(self) -> None:
        assert _actions({"Effect": "Allow", "Action": "s3:GetObject"}) == {"s3:GetObject"}

    def test_list_actions(self) -> None:
        stmt = {"Effect": "Allow", "Action": ["s3:GetObject", "s3:ListBucket"]}
        assert _actions(stmt) == {"s3:GetObject", "s3:ListBucket"}

    def test_deny_returns_empty(self) -> None:
        # Deny statements aren't part of "what's currently allowed".
        assert _actions({"Effect": "Deny", "Action": "s3:DeleteBucket"}) == set()

    def test_no_action_returns_empty(self) -> None:
        assert _actions({"Effect": "Allow"}) == set()


class TestActionsFromEvents:
    def test_basic_mapping(self) -> None:
        events = [
            {"EventName": "ListBucket", "EventSource": "s3.amazonaws.com"},
            {"EventName": "GetObject", "EventSource": "s3.amazonaws.com"},
            {"EventName": "DescribeInstances", "EventSource": "ec2.amazonaws.com"},
        ]
        result = actions_from_events(events)
        assert result == {
            "s3": {"ListBucket", "GetObject"},
            "ec2": {"DescribeInstances"},
        }

    def test_dedups_within_service(self) -> None:
        events = [
            {"EventName": "ListBucket", "EventSource": "s3.amazonaws.com"},
            {"EventName": "ListBucket", "EventSource": "s3.amazonaws.com"},
        ]
        assert actions_from_events(events) == {"s3": {"ListBucket"}}

    def test_unknown_source_skipped(self) -> None:
        events = [
            {"EventName": "Foo", "EventSource": "weird-no-domain"},
            {"EventName": "GetObject", "EventSource": "s3.amazonaws.com"},
        ]
        assert actions_from_events(events) == {"s3": {"GetObject"}}

    def test_empty(self) -> None:
        assert actions_from_events([]) == {}


class TestBuildPolicy:
    def test_groups_actions_by_service(self) -> None:
        policy = build_policy({"s3": {"GetObject", "ListBucket"}, "ec2": {"DescribeInstances"}})
        assert policy["Version"] == "2012-10-17"
        # Statements are sorted by service name.
        assert [s["Sid"] for s in policy["Statement"]] == ["AllowEc2", "AllowS3"]

    def test_actions_are_sorted_within_statement(self) -> None:
        policy = build_policy({"s3": {"PutObject", "GetObject", "DeleteObject"}})
        actions = policy["Statement"][0]["Action"]
        assert actions == ["s3:DeleteObject", "s3:GetObject", "s3:PutObject"]

    def test_empty(self) -> None:
        policy = build_policy({})
        assert policy == {"Version": "2012-10-17", "Statement": []}
