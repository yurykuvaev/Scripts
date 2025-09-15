"""Apply per-SG `Environment=<env>` tag from a pairs file.

Each line in --input is `<sg-id> <env>` separated by whitespace. The script
will skip an SG if it already has an `Environment` tag with a different
value (so a pre-existing prod tag won't be overwritten by 'dev').
"""
from __future__ import annotations

import sys
from pathlib import Path

from _common import LOG, aws_client, common_arg_parser, configure_logging


def read_pairs(path: Path) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for line in path.read_text().splitlines():
        parts = line.strip().split()
        if len(parts) == 2:
            pairs[parts[0]] = parts[1]
    return pairs


def apply_env_tag(client, sg_id: str, env: str, dry_run: bool) -> str:
    """Returns one of: applied / skipped-already / skipped-conflict."""
    resp = client.describe_tags(Filters=[{"Name": "resource-id", "Values": [sg_id]}])
    current = {t["Key"]: t["Value"] for t in resp.get("Tags", [])}
    existing_env = current.get("Environment")

    if existing_env == env:
        return "skipped-already"
    if existing_env and existing_env != env:
        LOG.warning("%s has Environment=%s, refusing to overwrite with %s",
                    sg_id, existing_env, env)
        return "skipped-conflict"

    if dry_run:
        LOG.info("[dry-run] %s would set Environment=%s", sg_id, env)
        return "applied"

    client.create_tags(Resources=[sg_id], Tags=[{"Key": "Environment", "Value": env}])
    LOG.info("%s set Environment=%s", sg_id, env)
    return "applied"


def main(argv: list[str] | None = None) -> int:
    parser = common_arg_parser(__doc__.splitlines()[0])
    parser.add_argument(
        "-i", "--input",
        type=Path,
        default=Path("sg_env_pairs.txt"),
        help="File with `<sg-id> <env>` pairs, one per line.",
    )
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    pairs = read_pairs(args.input)
    if not pairs:
        LOG.warning("no pairs found in %s", args.input)
        return 0

    ec2 = aws_client("ec2", region=args.region)
    counts = {"applied": 0, "skipped-already": 0, "skipped-conflict": 0}
    for sg_id, env in pairs.items():
        counts[apply_env_tag(ec2, sg_id, env, args.dry_run)] += 1

    LOG.info("done: %s", counts)
    return 0 if counts["skipped-conflict"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
