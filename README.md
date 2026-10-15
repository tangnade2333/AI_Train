# YOLO 目标检测训练指南 —— 以"螺丝刀识别"为例

> 本文是完整实战复盘：从零训练一个能识别螺丝刀的 YOLO 模型。
> 所有命令都在本仓库（`/home/tang/work/AI_Train/YOLO_test`）实测通过。
> 进度打勾看 `PLAN.md`，本文侧重"流程 + 命令 + 参数是什么意思"。

---

## 一、总览：训练一个检测模型要走哪 7 步

```
① 环境准备 → ② 准备数据 → ③ 标注 → ④ 划分数据 → ⑤ 训练 → ⑥ 评估 → ⑦ 推理使用
```

一句话概括每步：
| 步骤 | 干什么 | 耗时占比 |
|------|--------|---------|
| 环境 | 装好 ultralytics（含 PyTorch） | 5 分钟 |
| 数据 | 收集图片（自拍/下载） | 最花时间 |
| 标注 | 给每把螺丝刀画框 | 第二花时间 |
| 划分 | 拆成"练习册"和"考试卷" | 10 分钟 |
| 训练 | 让模型看图学习 | 等着就行 |
| 评估 | 看成绩单、找错误 | 脑力活 |
| 推理 | 拿新图/视频验证 | 10 分钟 |

---

## 二、各步骤详解与命令参数

### ① 环境准备

```bash
uv venv .venv --python 3.13               # 建独立Python环境，不污染系统
uv pip install -p .venv/bin/python ultralytics   # 装框架（自动带CUDA版torch）
.venv/bin/python -c "import torch; print(torch.cuda.is_available())"  # 必须True
```

- **虚拟环境（.venv）**：每个项目一套独立的 Python + 包，删目录即卸载。
- 之后所有命令都用 `.venv/bin/yolo` 或 `.venv/bin/python`，确保用的是这套环境。

### ② 准备数据

两种来源，各有取舍：

| 来源 | 优点 | 缺点 |
|------|------|------|
| 自己手机拍 | 场景=真实使用场景，模型最对症 | 费时，需标注 |
| Roboflow 等下载 | 量大、已有标注、省时 | 场景可能和你的使用环境不同 |

**关键原则：**
- 数据要"杂"：不同背景、光线、角度、距离、颜色。全是同一张桌子拍的，模型会偷懒记住桌子而不是学螺丝刀。
- **训练图里可以混入"不该检出的东西"（扳手、螺丝堆）但不给它们画框**——它们成为背景负样本，教会模型"金属杆状物 ≠ 螺丝刀"，专治乱报。
- 少量"完全没有螺丝刀"的空图也有价值（压低假阳性）。
- 下载的数据注意去重、版权（Roboflow 上 CC BY 4.0 可用，注明来源即可）。

### ③ 标注（画框）

工具：[makesense.ai](https://makesense.ai)（浏览器打开即用，图片不上传）。

1. 拖入图片 → 格式选 **Object Detection** → 导出格式选 **YOLO**
2. 类别只建一个：`screwdriver`
3. 每把螺丝刀画一个矩形框（Rect），紧贴物体、别留大空隙、别切掉物体
4. 没有螺丝刀的图：一个框都不画，直接下一张
5. 导出 → 得到一堆 `.txt` 标注文件

**标注质量 = 模型上限**，这步别赶。40 张大约 30~60 分钟。

### ④ 数据格式与划分

**YOLO 数据集目录约定**（图和标注同名配对）：

```
dataset/yolo/
├── images/train/xxx.jpg  ←→  labels/train/xxx.txt   （同名！）
├── images/val/yyy.jpg    ←→  labels/val/yyy.txt
└── data.yaml
```

**标注文件内容**（每行一个物体，坐标已归一化到 0~1）：

```
类别号  中心x占比  中心y占比  宽占比  高占比
0       0.375      0.375      0.25    0.25
```

换算：`中心x = (左角x + 右角x)/2 ÷ 图宽`，其余同理。图里没目标 → 不生成 txt。

**data.yaml**（告诉训练器数据在哪）：

```yaml
path: dataset/yolo
train: images/train
val: images/val
nc: 1              # 类别数
names:
  0: screwdriver   # 类号0 的名字
```

**划分脚本**（`scripts/split.py`，8:2 拆分，固定随机种子保证可复现）：

```python
random.seed(42)    # 不固定的话每次划分结果都不同，实验没法对比
# train 80% 给模型学习，val 20% 训练全程不看、专门考试
```

小坑：随机划分可能把背景图全分进 train，val 里没有 → 手动挪 3 张过去，
这样 val 才能同时考"找得到"和"不乱框"。

### ⑤ 训练

```bash
.venv/bin/yolo detect train \
  model=yolo26n.pt \          # 预训练权重起点（迁移学习，强烈建议）
  data=dataset/yolo_ext/data.yaml \
  epochs=50 \                 # 把全部图完整过几遍
  imgsz=640 \                 # 图统一缩放到这个尺寸喂给模型
  batch=8 \                   # 每次喂几张图（越大越吃显存，GPU利用率越高）
  patience=15 \               # val连续15轮无提升就提前停（防过拟合白练）
  project=runs/detect \       # 输出目录
  name=ext_v3                 # 本次实验名（每次实验一个文件夹，方便对比）
```

**参数怎么选（经验参考，显存6GB的3050）：**

| 参数 | 建议 | 说明 |
|------|------|------|
| model | `yolo26n.pt`（n/s/m/l/x 由小到大） | 从 `.pt` 开始=站在巨人肩膀上；从 `.yaml` 开始=白手起家，小数据别想 |
| epochs | 数据少 30~50，数据多 50~100 | 配合 patience 早停，不怕设多 |
| imgsz | 先 640；数据量 200+ 张后再试 960 | 小数据集上盲目调大反而会训崩（见教训3） |
| batch | 6GB 显存下 8~16 | 报 OOM 就减半 |

**训练时看懂终端输出：**

```
Epoch GPU_mem box_loss cls_loss ...   ← 学习侧：loss是"错了多少"，越低越好
14/30  1.44G   1.572    5.245
Class Images Instances P R mAP50 mAP50-95  ← 考试侧：每轮学完立刻在val上考一次
all     13      35     0.785 0.371 0.495  0.219
```

| 指标 | 大白话 |
|------|--------|
| box_loss / cls_loss | 框位置的错误分 / 分类的错误分，都越低越好 |
| P（精确率） | 框出来的框里，多少是真的（防误报看它） |
| R（召回率） | 画面里的目标，找到了多少（防漏检看它） |
| mAP50 | **主要成绩单**，框"大概盖住"就算对，0~1 越高越好 |
| mAP50-95 | 严选版成绩单，要求框贴很准，数值天然比 mAP50 低 |

训练曲线正常形态：前几轮 mAP 不动（还没开窍）→ 某轮突然起飞 → 缓慢精修。
`cls_loss` 开局很高是正常的（检测头换了类别数要重新学）。

### ⑥ 评估

```bash
.venv/bin/yolo detect val \
  model=runs/detect/runs/detect/ext_v3/weights/best.pt \   # 用最好的那版权重
  data=dataset/yolo_ext/data.yaml
```

产物在训练文件夹里：
- `best.pt`（mAP最高的权重，**部署就用它**） / `last.pt`
- `results.png`（loss和mAP曲线）、`confusion_matrix.png`（混淆矩阵）
- `val_batch0_labels.jpg` vs `val_batch0_pred.jpg`（标准答案 vs 模型答卷，肉眼对比）

**最重要的一课：val 分数可能骗你。** 如果 val 和训练图是同一批手机拍的，
模型是"背熟了你的桌子"，换个场景就现原形。所以要用**训练集外的新场景照片**实测，
那才是真实成绩。

### ⑦ 推理（日常使用）

```bash
.venv/bin/yolo detect predict \
  model=runs/detect/runs/detect/ext_v3/weights/best.pt \
  source=dataset/test \        # 可以是图片、文件夹、视频文件、摄像头0
  conf=0.25 \                  # 只显示置信度≥0.25的框
  save=True                    # 结果图存到 runs/detect/predict*/
```

`conf` 就是 P/R 跷跷板的滑杆：调低→检出更多但误报也多；调高→保守但可能漏检。

---

## 三、关键概念速查

| 概念 | 一句话解释 |
|------|-----------|
| 迁移学习 | 拿预训练好的 `.pt` 权重继续训练，比从零训练快得多、要的数据少得多 |
| 过拟合 | 把训练数据背得滚瓜烂熟，换个场景就废。信号：train loss降、val loss升 |
| 泛化 | 模型在没见过的数据上也能打。我们一切努力都是为了它 |
| 负样本/背景图 | 没有目标的图（或目标不画框），教模型"这里没有"，减少乱报 |
| IoU | 预测框和答案框的重叠程度，≥0.5算对（mAP50）、更严算对（mAP50-95） |
| 单变量原则 | 一次实验只改一个参数，否则无法归因，白做 |
| 数据增强 | 训练时自动对图做翻转/裁剪/调色，等于免费增加数据多样性（ultralytics默认开） |

---

## 四、本次实战踩坑记录（含教训）

| # | 现象 | 原因 | 教训 |
|---|------|------|------|
| 1 | v1 val mAP50=0.867，新场景却漏检/乱报 | val与训练集同分布（都是自己同一天拍的） | **val高≠真的好**，新场景实测为准；val要留部署场景的图 |
| 2 | v1 把螺丝误判成螺丝刀（conf 0.68） | 训练集没有螺丝堆这类负样本 | 干扰物要进训练图（不画框），专治误报 |
| 3 | v2 imgsz=1280 训练崩了（mAP 0.064，cls_loss居高不下） | 42张小数据 + 高分辨率 + batch减半，默认超参失稳 | **数据量不够时别碰高分辨率**；数据200+张后再试960 |
| 4 | val里一张背景图都没有 | 8:2随机划分没分层 | 划分后检查构成，必要时手动调配 |
| 5 | 外部数据类别对不上 | 预想的多类合并，实际下到的集子恰好单类 | 合并前先看 data.yaml 的 nc 和 names |

**三代模型成绩单**（详见 `PLAN.md`）：

| | mini_v1 | mini_v2 | ext_v3（现役） |
|---|---|---|---|
| 数据 | 42张自拍 | 42张自拍 | 822张(783外部+39自拍) |
| imgsz | 640 | 1280 | 960 |
| val mAP50 | 0.867(虚高) | 0.064(失败) | 0.772(诚实) |
| 新场景实测 | 漏检/误报严重 | — | 红柄检出、螺丝零误报 |

结论一句话：**数据的数量和多样性 >> 一切调参。**

---

## 五、常见报错排查

| 报错/现象 | 怎么办 |
|-----------|--------|
| `torch.cuda.is_available()` 返回 False | 查 `nvidia-smi` 驱动是否正常；确认装的是CUDA版torch而非CPU版 |
| `CUDA out of memory` | batch 减半，或 imgsz 调小 |
| 训练提前结束、打印 EarlyStopping | 正常！连续 patience 轮 val 没进步自动停，best.pt 已保存 |
| mAP 一直是 0.0x 不涨 | 先查数据：标注txt和图片文件名对得上吗？坐标在0~1吗？类号对吗？ |
| 检出效果忽好忽坏 | 检查是否一次改了多个参数；val是否和训练集同分布导致虚高 |
| 新图检不出 | 试试调低 conf=0.1 看是"被阈值卡住"还是"真没认出来" |

---

## 六、本仓库目录速查

```
YOLO_test/
├── PLAN.md                     # 进度打勾清单 + 三代对比复盘
├── README.md                   # 本文
├── .venv/                      # Python虚拟环境
├── scripts/
│   ├── split.py                # 自有数据8:2划分
│   └── merge_external.py       # 外部集+自有集合并
├── dataset/
│   ├── raw/mini/               # 自拍原图（52张：40有标注+12背景）
│   ├── raw/external/           # Roboflow下载（854张，CC BY 4.0，来源 universo/screwdriver-paveq）
│   ├── yolo/                   # 自有数据集（v1用）
│   ├── yolo_ext/               # 合并数据集（822 train / 13 val）
│   └── test/                   # 新场景测试图+视频（不参与训练）
├── runs/detect/
│   ├── mini_v1/                # v1训练产物
│   ├── mini_v2/                # v2（失败实验，留档）
│   └── ext_v3/                 # v3训练产物 ★ 现役最优：weights/best.pt
└── demo/step2/                 # YOLO标签格式示例
```

模型使用一行命令：

```bash
.venv/bin/yolo detect predict model=runs/detect/runs/detect/ext_v3/weights/best.pt source=你的图片或视频 conf=0.25 save=True
```

---

## 七、下一步可选方向（PLAN.md 阶段 C）

1. **导出 ONNX**：`yolo export model=best.pt format=onnx`，脱离Python给别人/嵌入式用
2. **摄像头实时检测**：`source=0`，3050 跑 yolo26n 实时无压力
3. **多类别扩展**：把扳手/钳子正式标注为 1、2 类，重训
4. **子类细分**：十字 / 一字 / 电动螺丝刀
5. **继续喂数据**：补自有场景的螺丝堆负样本、密集摆放场景（当前模型剩余弱点）
