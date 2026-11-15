import pytest

from src.dataset.splitter import split_dataset


@pytest.fixture
def flat_dataset(tmp_path):
    root = tmp_path / "flat"
    (root / "images").mkdir(parents=True)
    (root / "labels").mkdir(parents=True)
    for i in range(20):
        (root / "images" / f"img{i:02d}.jpg").write_bytes(b"jpg")
        (root / "labels" / f"img{i:02d}.txt").write_text("0 0.5 0.5 0.1 0.1")
    return root


def _names(out, split):
    return {p.stem for p in (out / split / "images").iterdir()}


def test_split_counts_and_no_leakage(flat_dataset, tmp_path):
    out = tmp_path / "out"
    stats = split_dataset(flat_dataset, out, 0.7, 0.2, 0.1, seed=42)

    assert stats == {"train": 14, "val": 4, "test": 2}
    train, val, test = _names(out, "train"), _names(out, "val"), _names(out, "test")
    assert not (train & val) and not (train & test) and not (val & test)
    assert len(train | val | test) == 20


def test_labels_follow_their_images(flat_dataset, tmp_path):
    out = tmp_path / "out"
    split_dataset(flat_dataset, out)
    for split in ("train", "val", "test"):
        labels = {p.stem for p in (out / split / "labels").iterdir()}
        assert labels == _names(out, split)


def test_same_seed_gives_same_split(flat_dataset, tmp_path):
    split_dataset(flat_dataset, tmp_path / "a", seed=7)
    split_dataset(flat_dataset, tmp_path / "b", seed=7)
    assert _names(tmp_path / "a", "test") == _names(tmp_path / "b", "test")


def test_ratios_must_sum_to_one(flat_dataset, tmp_path):
    with pytest.raises(AssertionError):
        split_dataset(flat_dataset, tmp_path / "out", 0.5, 0.2, 0.1)
