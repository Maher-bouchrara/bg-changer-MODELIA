"""Tests for bgchange/benchmark/dataset.py, on a fake test_data folder."""

from pathlib import Path

import pytest

from bgchange.benchmark.dataset import list_samples


def _make_set(root: Path, set_name: str, names: list[str], with_masks: bool = True) -> None:
    (root / set_name / "images").mkdir(parents=True)
    (root / set_name / "masks").mkdir(parents=True)
    for name in names:
        (root / set_name / "images" / f"{name}.jpg").write_bytes(b"")
        if with_masks:
            (root / set_name / "masks" / f"{name}.png").write_bytes(b"")


def test_dis_names_give_group_and_category(tmp_path):
    _make_set(tmp_path, "dis-vd", ["1#Furniture#3#Chair#123_o", "2#Architecture#1#Bridge#456_o"])
    bridge, chair = sorted(list_samples("dis-vd", root=tmp_path), key=lambda s: s.category)

    assert (bridge.group, bridge.category, bridge.product_like) == ("Architecture", "Bridge", False)
    assert (chair.group, chair.category, chair.product_like) == ("Furniture", "Chair", True)


def test_p3m_samples_are_people(tmp_path):
    _make_set(tmp_path, "p3m-500-np", ["p_0001"])
    (sample,) = list_samples("p3m-500-np", root=tmp_path)
    assert (sample.group, sample.category, sample.product_like) == ("People", "Portrait", False)


def test_photos_without_answer_key_are_skipped(tmp_path):
    _make_set(tmp_path, "dis-vd", ["1#Tool#1#Key#1"], with_masks=False)
    assert list_samples("dis-vd", root=tmp_path) == []


def test_limit_spreads_over_the_whole_set(tmp_path):
    """DIS-VD is sorted by group, so a limit must not just take the first ones."""
    names = [f"1#Group{g}#1#Cat#{i}" for g in "ABCD" for i in range(5)]  # 4 groups x 5
    _make_set(tmp_path, "dis-vd", names)
    picked = list_samples("dis-vd", limit=4, root=tmp_path)

    assert len(picked) == 4
    assert {s.group for s in picked} == {"GroupA", "GroupB", "GroupC", "GroupD"}


def test_missing_set_gives_download_command(tmp_path):
    with pytest.raises(FileNotFoundError, match="download_test_data.py"):
        list_samples("dis-vd", root=tmp_path)
