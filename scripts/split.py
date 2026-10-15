import random
import shutil
from pathlib import Path

random.seed(42)  # 固定随机种子：同样的数据每次划分结果相同，可复现

src_img = Path('dataset/raw/mini')
src_lbl = Path('dataset/raw/phtxt/extracted')
dst = Path('dataset/yolo')

imgs = sorted(src_img.glob('*.jpg'))
random.shuffle(imgs)

n_val = max(1, round(len(imgs) * 0.2))   # 20% 做验证集
val_set, train_set = imgs[:n_val], imgs[n_val:]

for split, items in [('train', train_set), ('val', val_set)]:
    (dst / 'images' / split).mkdir(parents=True, exist_ok=True)
    (dst / 'labels' / split).mkdir(parents=True, exist_ok=True)
    for img in items:
        shutil.copy(img, dst / 'images' / split / img.name)
        lbl = src_lbl / (img.stem + '.txt')
        if lbl.exists():   # 背景图没有 txt，不复制 → 训练器自动当"无目标"负样本
            shutil.copy(lbl, dst / 'labels' / split / lbl.name)

print(f'train={len(train_set)} 张, val={len(val_set)} 张')
