#!/usr/bin/env python3
"""按“来源组”重新划分数据集 8:2，避免同一原始帧的增强副本跨 train/val 泄露。

分组规则：
  - 外部 Roboflow 图：000000_jpg.rf.<hash>.jpg  ->  组 = ext_000000（同一原始帧）
  - 自拍图：IMG_20261015_110630.jpg             ->  组 = own_20261015_1106（同一分钟连拍）
  - 其它：按文件名单独成组

用法：
  python scripts/resplit.py --src dataset/yolo_ext --dst dataset/yolo_v4 --val-ratio 0.2 --seed 42
"""
import argparse
import random
import re
import shutil
from collections import defaultdict
from pathlib import Path

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def group_key(name: str) -> tuple[str, str]:
    """返回 (来源类型, 组名)。"""
    if ".rf." in name:                          # Roboflow 增强副本：.rf. 之前即原始帧名
        base = name.split(".rf.")[0]
        base = re.sub(r"[-_]?(jpg|jpeg|png)$", "", base, flags=re.I).rstrip("-_")
        return "ext", "ext_" + base
    m = re.match(r"(IMG_\d{8}_\d{4})", name)     # 自拍：按分钟聚合连拍
    if m:
        return "own", "own_" + m.group(1).replace("IMG_", "")
    return "other", "file_" + Path(name).stem


def collect(src: Path) -> list[tuple[Path, Path | None]]:
    items = []
    for split in ("train", "val"):
        img_dir = src / "images" / split
        if not img_dir.is_dir():
            continue
        for img in sorted(img_dir.iterdir()):
            if img.suffix.lower() not in IMG_EXTS:
                continue
            lbl = src / "labels" / split / f"{img.stem}.txt"
            items.append((img, lbl if lbl.exists() else None))
    return items


def split_groups(items, val_ratio: float, seed: int):
    """按来源类型分别做 8:2，保证 val 里两类都有。"""
    by_type = defaultdict(list)
    for img, lbl in items:
        kind, gid = group_key(img.name)
        by_type[kind].append((gid, img, lbl))

    rng = random.Random(seed)
    train, val = [], []
    for kind, rows in sorted(by_type.items()):
        groups = defaultdict(list)
        for gid, img, lbl in rows:
            groups[gid].append((img, lbl))
        gids = sorted(groups)
        rng.shuffle(gids)

        target = round(len(rows) * val_ratio)
        picked, count = [], 0
        for gid in gids:
            if count >= target:
                break
            picked.append(gid)
            count += len(groups[gid])

        for gid in gids:
            (val if gid in picked else train).extend(groups[gid])
        print(f"  {kind}: 图 {len(rows)} 组 {len(gids)} -> val {count} 图 / {len(picked)} 组")
    return train, val


def copy_split(rows, dst: Path, split: str):
    img_dir = dst / "images" / split
    lbl_dir = dst / "labels" / split
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)
    for img, lbl in rows:
        shutil.copy2(img, img_dir / img.name)
        if lbl:
            shutil.copy2(lbl, lbl_dir / lbl.name)


def verify(train, val):
    tr = {group_key(i.name)[1] for i, _ in train}
    va = {group_key(i.name)[1] for i, _ in val}
    overlap = tr & va
    assert not overlap, f"仍有 {len(overlap)} 个组跨越 train/val: {list(overlap)[:5]}"
    print(f"  校验通过：train 组 {len(tr)}，val 组 {len(va)}，重叠 0")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--src", default="dataset/yolo_ext")
    p.add_argument("--dst", default="dataset/yolo_v4")
    p.add_argument("--val-ratio", type=float, default=0.2)
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()

    src, dst = Path(a.src), Path(a.dst)
    items = collect(src)
    print(f"源数据: {src}，共 {len(items)} 张")
    if dst.exists():
        shutil.rmtree(dst)

    train, val = split_groups(items, a.val_ratio, a.seed)
    copy_split(train, dst, "train")
    copy_split(val, dst, "val")

    (dst / "data.yaml").write_text(
        f"path: {dst.as_posix()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "nc: 1\n"
        "names:\n"
        "  0: screwdriver\n",
        encoding="utf-8",
    )

    print(f"\n结果: train {len(train)} 张, val {len(val)} 张 "
          f"(val {len(val) / len(items):.0%})")
    n_bg_val = sum(1 for _, l in val if l is None)
    print(f"val 中背景图（无标签）: {n_bg_val} 张")
    verify(train, val)


if __name__ == "__main__":
    main()
