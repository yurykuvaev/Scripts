"""Report or delete ECR images that haven't been pulled recently.

ECR's built-in lifecycle policies expire by push age, not pull age, which
misses the common case: an image keeps getting deployed for months but its
storage bill grows because dozens of older "passing" builds accumulate.

This script uses each image's `lastRecordedPullTime` (falls back to
`imagePushedAt` if the image has never been pulled) and supports two
safety nets:

  --keep-tag-pattern PATTERN   never delete an image whose tag matches
                               (e.g. 'prod-*', 'v*.*.*'). Repeatable.
  --keep-last-n N              within each repository, always keep the N
                               newest by push time.
"""
from __future__ import annotations

import fnmatch
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from _common import LOG, aws_client, common_arg_parser, configure_logging


def list_repositories(client) -> list[str]:
    repos: list[str] = []
    paginator = client.get_paginator("describe_repositories")
    for page in paginator.paginate():
        repos.extend(r["repositoryName"] for r in page["repositories"])
    return repos


def list_images(client, repo: str) -> list[dict[str, Any]]:
    images: list[dict[str, Any]] = []
    paginator = client.get_paginator("describe_images")
    for page in paginator.paginate(repositoryName=repo):
        images.extend(page["imageDetails"])
    return images


def last_activity(image: dict) -> datetime:
    """Most recent of pull-time and push-time (UTC)."""
    pulled = image.get("lastRecordedPullTime")
    pushed = image.get("imagePushedAt")
    if pulled and pushed:
        return max(pulled, pushed)
    return pulled or pushed


def matches_keep_pattern(image: dict, patterns: list[str]) -> bool:
    """True if any tag of the image matches any glob in patterns."""
    if not patterns:
        return False
    for tag in image.get("imageTags", []) or []:
        for pat in patterns:
            if fnmatch.fnmatch(tag, pat):
                return True
    return False


def select_for_deletion(
    images: list[dict],
    cutoff: datetime,
    keep_patterns: list[str],
    keep_last_n: int,
) -> list[dict]:
    """Return the subset of images that should be deleted."""
    # Always-keep first: most recent N by push time.
    by_push = sorted(images, key=lambda i: i["imagePushedAt"], reverse=True)
    pinned_recent = {id(img) for img in by_push[:keep_last_n]}

    to_delete: list[dict] = []
    for img in images:
        if id(img) in pinned_recent:
            continue
        if matches_keep_pattern(img, keep_patterns):
            continue
        if last_activity(img) >= cutoff:
            continue
        to_delete.append(img)
    return to_delete


def delete_images(client, repo: str, images: list[dict], dry_run: bool) -> int:
    """ECR's batch_delete_image API takes 100 imageIds per call."""
    if not images:
        return 0
    ids = [{"imageDigest": i["imageDigest"]} for i in images]
    deleted = 0
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        if dry_run:
            LOG.info("[dry-run] %s would delete %d image(s) in batch", repo, len(chunk))
            deleted += len(chunk)
            continue
        resp = client.batch_delete_image(repositoryName=repo, imageIds=chunk)
        deleted += len(resp.get("imageIds", []))
        for failure in resp.get("failures", []):
            LOG.error("%s delete failure: %s", repo, failure)
    return deleted


def main(argv: list[str] | None = None) -> int:
    parser = common_arg_parser(__doc__.splitlines()[0])
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=90,
        help="Images inactive longer than this are eligible for deletion (default: 90).",
    )
    parser.add_argument(
        "--keep-tag-pattern",
        action="append",
        default=[],
        help="Glob (fnmatch) - tags matching are always kept. Repeatable.",
    )
    parser.add_argument(
        "--keep-last-n",
        type=int,
        default=10,
        help="Per repo, keep the N most-recently-pushed images regardless of age.",
    )
    parser.add_argument(
        "--repository",
        action="append",
        default=[],
        help="Limit to these repositories. Default: every repo in the region.",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually call batch_delete_image. Otherwise report-only.",
    )
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    ecr = aws_client("ecr", region=args.region)
    repos = args.repository or list_repositories(ecr)
    LOG.info("inspecting %d repo(s)", len(repos))

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.max_age_days)
    LOG.info("delete cutoff: images inactive since before %s", cutoff.isoformat())

    total_seen = 0
    total_to_delete = 0
    total_deleted = 0
    for repo in repos:
        images = list_images(ecr, repo)
        total_seen += len(images)
        to_delete = select_for_deletion(images, cutoff, args.keep_tag_pattern, args.keep_last_n)
        if to_delete:
            LOG.info("%s: %d candidate(s) for deletion (of %d)",
                     repo, len(to_delete), len(images))
            for img in to_delete:
                tags = img.get("imageTags") or ["<untagged>"]
                LOG.debug("  %s tags=%s last_active=%s",
                          img["imageDigest"][:19], tags, last_activity(img).isoformat())
        total_to_delete += len(to_delete)
        if args.delete:
            total_deleted += delete_images(ecr, repo, to_delete, args.dry_run)

    LOG.info("done: %sscanned=%d candidates=%d deleted=%d",
             "[dry-run] " if args.dry_run else "",
             total_seen, total_to_delete, total_deleted)
    return 0


if __name__ == "__main__":
    sys.exit(main())
