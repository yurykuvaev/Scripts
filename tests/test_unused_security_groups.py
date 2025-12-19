"""Unit tests for the pure-Python helpers in unused_security_groups.

We don't mock botocore here — that would test the mock library more than
our code. Instead we test the parts that have real logic: cross-reference
extraction and topo sort for delete order.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from unused_security_groups import cross_references, topo_sort_for_delete


def make_sg(sg_id: str, refs: list[str]) -> dict:
    """Build a minimal SG dict that references other SGs in its ingress rules."""
    return {
        "GroupId": sg_id,
        "IpPermissions": [
            {"UserIdGroupPairs": [{"GroupId": ref} for ref in refs]},
        ],
        "IpPermissionsEgress": [],
    }


class TestCrossReferences:
    def test_no_references(self) -> None:
        sgs = [make_sg("sg-1", []), make_sg("sg-2", [])]
        assert dict(cross_references(sgs)) == {}

    def test_single_reference(self) -> None:
        sgs = [make_sg("sg-1", ["sg-2"]), make_sg("sg-2", [])]
        result = dict(cross_references(sgs))
        assert result == {"sg-1": {"sg-2"}}

    def test_self_reference_ignored(self) -> None:
        # "sg-1 allows ingress from sg-1" is common (peer-to-peer in cluster);
        # it should not be counted as cross-reference.
        sgs = [make_sg("sg-1", ["sg-1"])]
        assert dict(cross_references(sgs)) == {}

    def test_chain(self) -> None:
        sgs = [
            make_sg("sg-1", ["sg-2"]),
            make_sg("sg-2", ["sg-3"]),
            make_sg("sg-3", []),
        ]
        result = dict(cross_references(sgs))
        assert result == {"sg-1": {"sg-2"}, "sg-2": {"sg-3"}}


class TestTopoSortForDelete:
    def test_independent_sgs(self) -> None:
        # Order doesn't really matter for independent SGs but result must contain all.
        order = topo_sort_for_delete(["sg-a", "sg-b", "sg-c"], {})
        assert sorted(order) == ["sg-a", "sg-b", "sg-c"]

    def test_chain_referrer_first(self) -> None:
        # sg-1 references sg-2. To delete both safely, sg-1 must go first
        # so the dependency it has on sg-2 disappears.
        refs = {"sg-1": {"sg-2"}}
        order = topo_sort_for_delete(["sg-1", "sg-2"], refs)
        assert order.index("sg-1") < order.index("sg-2")

    def test_three_chain(self) -> None:
        # sg-1 -> sg-2 -> sg-3 (referencer to referenced)
        # delete order: sg-1, sg-2, sg-3
        refs = {"sg-1": {"sg-2"}, "sg-2": {"sg-3"}}
        order = topo_sort_for_delete(["sg-1", "sg-2", "sg-3"], refs)
        assert order == ["sg-1", "sg-2", "sg-3"]

    def test_dep_outside_unused_set_is_ignored(self) -> None:
        # sg-1 references sg-2 but sg-2 is not in the unused list — that's fine,
        # the topo sort only walks within the unused set.
        refs = {"sg-1": {"sg-2"}}
        order = topo_sort_for_delete(["sg-1"], refs)
        assert order == ["sg-1"]
