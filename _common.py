"""Shared utilities used by all scripts in this repo.

Keeps the per-script files focused on the business logic - argparse,
logging setup, and the boto3 client factory live here so we don't repeat
them.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any

import boto3

LOG = logging.getLogger("scripts")


def configure_logging(verbose: bool = False) -> None:
    """Set up a single root logger writing to stderr.

    Format is short by default and gains the module name when -v is passed.
    """
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s %(levelname)-5s %(message)s"
    if verbose:
        fmt = "%(asctime)s %(levelname)-5s %(name)s %(message)s"

    logging.basicConfig(level=level, format=fmt, datefmt="%H:%M:%S", stream=sys.stderr)


def aws_client(service: str, region: str | None = None) -> Any:
    """Build a boto3 client.

    `region` overrides the env / config; falling back to AWS_REGION,
    then to whatever `~/.aws/config` says.
    """
    region = region or os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    return boto3.client(service, region_name=region)


def common_arg_parser(description: str) -> argparse.ArgumentParser:
    """A parser pre-loaded with the flags every script supports."""
    p = argparse.ArgumentParser(description=description)
    p.add_argument(
        "--region",
        default=None,
        help="AWS region. Defaults to $AWS_REGION / $AWS_DEFAULT_REGION / aws config.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print intended changes without calling write APIs.",
    )
    p.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show DEBUG logs.",
    )
    return p


def parse_kv_pairs(values: list[str]) -> dict[str, str]:
    """Parse a list of `--tag KEY=VALUE` arguments into a dict.

    Raises argparse.ArgumentTypeError on malformed input so the caller
    fails fast with a clean message.
    """
    out: dict[str, str] = {}
    for v in values or []:
        if "=" not in v:
            raise argparse.ArgumentTypeError(f"expected KEY=VALUE, got: {v!r}")
        k, _, val = v.partition("=")
        if not k:
            raise argparse.ArgumentTypeError(f"empty key in: {v!r}")
        out[k] = val
    return out
