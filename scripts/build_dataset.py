#!/usr/bin/env python3
"""从 raw/ 重建训练集：raw/external + raw/mini -> dataset/yolo_v4

解决的问题：旧流程要两个脚本接力（merge_external.py 合并 → resplit.py 划分），
两个都已废弃。本脚本一步到位，并且自带校验。

流程
  1. 收集  raw/external/train/{images,labels}  +  raw/mini/*.jpg 配 raw/phtxt/extracted/*.txt
  2. 暂存  统一成 images/train + labels/train 的布局
  3. 划分  按「场景组」8:2（复用 resplit.py 的分组与防泄露逻辑）
  4. 校验  配对完整、跨组零重叠、内容无重复
  5. 比对  --verify-against 可选，逐字节确认与已有数据集一致

用法
  # 先试跑，不落盘
  python scripts/build_dataset.py --dst /tmp/yolo_v4_rebuild --dry-run

  # 重建到指定目录，并与现有数据集比对
  python scripts/build_dataset.py --dst /tmp/yolo_v4_rebuild --verify-against dataset/yolo_v4

  # 覆盖正式目录（会先备份到 <dst>.bak-<时间戳>）
  python scripts/build_dataset.py --dst dataset/yolo_v4 --force

注意
  raw/external/valid 的 52 张默认**不纳入**（与历史上 yolo_v4 的构成保持一致），
  需要时加 --include-external-valid。
  raw/external/test 的 19 张是最终验收集，**永不纳入**。
"""
import argparse
import hashlib
import shutil
import sys
import time
from pathlib import Path

# 复用 resplit.py 的分组/划分/校验逻辑，避免两套规则各写一遍而逐渐分歧
sys.path.insert(0, str(Path(__file__).resolve().parent))
import resplit  # noqa: E402

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def parse_args():
    p = argparse.ArgumentParser(description="从 raw/ 重建 YOLO 训练集")
    p.add_argument("--raw", default="dataset/raw", help="原始素材根目录")
    p.add_argument("--dst", required=True, help="输出数据集目录（写入 images/ labels/ data.yaml）")
    p.add_argument("--val-ratio", type=float, default=0.2, help="验证集比例")
    p.add_argument("--seed", type=int, default=42, help="划分随机种子，固定才可复现")
    p.add_argument("--include-external-valid", action="store_true",
                   help="把 raw/external/valid 的图片也纳入（默认不纳入，保持历史构成）")
    p.add_argument("--verify-against", default=None,
                   help="与已有数据集逐字节比对，例如 dataset/yolo_v4")
    p.add_argument("--force", action="store_true", help="dst 已存在时备份后覆盖")
    p.add_argument("--dry-run", action="store_true", help="只统计和预演，不写任何文件")
    return p.parse_args()


def collect_external(raw: Path, include_valid: bool):
    """收集外部集：train（必需）+ 可选 valid。test 永不纳入。"""
    items, missing = [], 0
    splits = ["train"] + (["valid"] if include_valid else [])
    for sp in splits:
        img_dir = raw / "external" / sp / "images"
        lbl_dir = raw / "external" / sp / "labels"
        if not img_dir.is_dir():
            raise SystemExit(f"找不到外部集目录: {img_dir}")
        for img in sorted(img_dir.iterdir()):
            if img.suffix.lower() not in IMG_EXTS:
                continue
            lbl = lbl_dir / f"{img.stem}.txt"
            if lbl.exists():
                items.append((img, lbl))
            else:
                items.append((img, None))
                missing += 1
    print(f"  外部集: {len(items)} 张（无标签 {missing} 张，作为背景负样本）")
    return items


def collect_own(raw: Path):
    """收集自拍集：图片在 raw/mini 平铺，标签在 raw/phtxt/extracted。"""
    img_dir = raw / "mini"
    lbl_dir = raw / "phtxt" / "extracted"
    if not img_dir.is_dir():
        raise SystemExit(f"找不到自拍目录: {img_dir}")
    if not lbl_dir.is_dir():
        raise SystemExit(f"找不到自拍标签目录: {lbl_dir}")
    items, missing = [], 0
    for img in sorted(img_dir.iterdir()):
        if img.suffix.lower() not in IMG_EXTS:
            continue
        lbl = lbl_dir / f"{img.stem}.txt"
        if lbl.exists() and lbl.stat().st_size > 0:
            items.append((img, lbl))
        else:
            items.append((img, None))
            missing += 1
    print(f"  自拍集: {len(items)} 张（无标签 {missing} 张，作为背景负样本）")
    return items


def stage(items, staging: Path):
    """把两组素材统一复制成 images/train + labels/train 布局，供 resplit 消费。"""
    img_out = staging / "images" / "train"
    lbl_out = staging / "labels" / "train"
    img_out.mkdir(parents=True, exist_ok=True)
    lbl_out.mkdir(parents=True, exist_ok=True)

    seen = {}
    for img, lbl in items:
        if img.name in seen:
            raise SystemExit(f"文件名冲突: {img} 与 {seen[img.name]} —— 合并前需改名")
        seen[img.name] = img
        shutil.copy2(img, img_out / img.name)
        if lbl:
            shutil.copy2(lbl, lbl_out / lbl.name)
    print(f"  暂存完成: {len(items)} 张 -> {staging}")


def write_data_yaml(dst: Path):
    (dst / "data.yaml").write_text(
        f"path: {dst.as_posix()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "nc: 1\n"
        "names:\n"
        "  0: screwdriver\n",
        encoding="utf-8",
    )


def img_hashes(root: Path):
    """按文件名建索引，返回 {name: md5}，用于两套数据集逐字节比对。"""
    out = {}
    for p in root.rglob("*"):
        if p.suffix.lower() in IMG_EXTS:
            out[p.name] = hashlib.md5(p.read_bytes()).hexdigest()
    return out


def verify(dst: Path, train, val):
    """四道自检：配对完整、无孤儿标签、跨组零重叠、内容无重复。"""
    ok = True

    for split in ("train", "val"):
        imgs = {p.stem for p in (dst / "images" / split).iterdir() if p.suffix.lower() in IMG_EXTS}
        lbls = {p.stem for p in (dst / "labels" / split).glob("*.txt")}
        orphan = lbls - imgs          # 有标签没图 = 数据错位
        bg = len(imgs - lbls)         # 有图没标签 = 背景负样本，正常
        print(f"  {split}: 图 {len(imgs)} 标签 {len(lbls)} 背景图 {bg} 孤儿标签 {len(orphan)}")
        if orphan:
            print(f"    ❌ 孤儿标签: {list(orphan)[:3]}")
            ok = False

    tr = {resplit.group_key(i.name)[1] for i, _ in train}
    va = {resplit.group_key(i.name)[1] for i, _ in val}
    overlap = tr & va
    if overlap:
        print(f"  ❌ 跨 train/val 的组: {len(overlap)} 个，例如 {list(overlap)[:3]}")
        ok = False
    else:
        print(f"  组: train {len(tr)} / val {len(va)} / 重叠 0")

    hashes = list(img_hashes(dst).values())
    dup = len(hashes) - len(set(hashes))
    if dup:
        print(f"  ⚠️  内容重复的图片: {dup} 组（同图多份，会让 val 分数虚高）")
    else:
        print("  内容重复: 0")
    return ok


def main():
    a = parse_args()
    raw, dst = Path(a.raw), Path(a.dst)

    print("=== 1/5 收集素材 ===")
    items = collect_external(raw, a.include_external_valid) + collect_own(raw)
    print(f"  合计: {len(items)} 张")
    if not items:
        raise SystemExit("没有收集到任何图片")

    print("\n=== 2/5 预演划分（不落盘）===")
    staging = Path("/tmp") / f"yolo_stage_{int(time.time())}"
    stage(items, staging)
    collected = resplit.collect(staging)
    train, val = resplit.split_groups(collected, a.val_ratio, a.seed)
    print(f"  train {len(train)} 张 / val {len(val)} 张 ({len(val) / len(collected):.0%})")

    if a.dry_run:
        shutil.rmtree(staging, ignore_errors=True)
        print("\n--dry-run：未写入任何文件")
        return

    print("\n=== 3/5 写入目标目录 ===")
    if dst.exists():
        if not a.force:
            shutil.rmtree(staging, ignore_errors=True)
            raise SystemExit(f"{dst} 已存在。确认要覆盖就加 --force（会先备份）")
        bak = dst.with_name(f"{dst.name}.bak-{time.strftime('%Y%m%d_%H%M%S')}")
        dst.rename(bak)
        print(f"  旧目录已备份: {bak}")
    resplit.copy_split(train, dst, "train")
    resplit.copy_split(val, dst, "val")
    write_data_yaml(dst)
    print(f"  已写入 {dst}")

    print("\n=== 4/5 校验 ===")
    if not verify(dst, train, val):
        shutil.rmtree(staging, ignore_errors=True)
        raise SystemExit("校验失败，请检查上面的输出")

    if a.verify_against:
        print(f"\n=== 5/5 与 {a.verify_against} 逐字节比对 ===")
        ref = img_hashes(Path(a.verify_against))
        cur = img_hashes(dst)
        only_ref = set(ref) - set(cur)
        only_cur = set(cur) - set(ref)
        diff = {k for k in set(ref) & set(cur) if ref[k] != cur[k]}
        if not only_ref and not only_cur and not diff:
            print(f"  ✅ 完全一致（{len(cur)} 张图片逐字节相同）")
        else:
            print(f"  ❌ 不一致：仅参考有 {len(only_ref)}，仅新集有 {len(only_cur)}，内容不同 {len(diff)}")
            for k in list(diff)[:3]:
                print(f"     {k}")

    shutil.rmtree(staging, ignore_errors=True)
    print("\n完成。data.yaml:")
    print((dst / "data.yaml").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
