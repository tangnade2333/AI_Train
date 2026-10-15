import shutil
from pathlib import Path

ext = Path('dataset/raw/external')
own = Path('dataset/yolo')          # 你自己已划分好的数据
dst = Path('dataset/yolo_ext')      # 合并后的新数据集（不动旧的，方便对比）

for split in ['train', 'val']:
    (dst / 'images' / split).mkdir(parents=True, exist_ok=True)
    (dst / 'labels' / split).mkdir(parents=True, exist_ok=True)

# 外部 train → 新 train
for img in (ext / 'train' / 'images').iterdir():
    shutil.copy(img, dst / 'images' / 'train' / img.name)
    lbl = ext / 'train' / 'labels' / (img.stem + '.txt')
    if lbl.exists():
        shutil.copy(lbl, dst / 'labels' / 'train' / lbl.name)

# 自己的 train → 新 train
for img in (own / 'images' / 'train').iterdir():
    shutil.copy(img, dst / 'images' / 'train' / img.name)
    lbl = own / 'labels' / 'train' / (img.stem + '.txt')
    if lbl.exists():
        shutil.copy(lbl, dst / 'labels' / 'train' / lbl.name)

# 自己的 val → 新 val（外部 valid 不用，考题要贴近部署场景）
for img in (own / 'images' / 'val').iterdir():
    shutil.copy(img, dst / 'images' / 'val' / img.name)
    lbl = own / 'labels' / 'val' / (img.stem + '.txt')
    if lbl.exists():
        shutil.copy(lbl, dst / 'labels' / 'val' / lbl.name)

print('merge done')
