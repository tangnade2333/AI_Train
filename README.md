# YOLO 目标检测实战 —— 以"螺丝刀识别"为例

> 本文是完整实战复盘：从零训练一个能识别螺丝刀的 YOLO 模型，并接到摄像头做实时检测。
> 所有命令都在本仓库（`/home/tang/work/AI_Train/YOLO_test`）实测通过。
> 进度打勾看 `PLAN.md`，本文侧重"流程 + 命令 + 参数是什么意思"。

---

## 一、总览：从数据到实时检测要走哪 8 步

```
① 环境准备 → ② 准备数据 → ③ 标注 → ④ 划分数据 → ⑤ 训练 → ⑥ 评估 → ⑦ 推理 → ⑧ 实时检测
```

| 步骤 | 干什么 | 耗时占比 |
|------|--------|---------|
| 环境 | 装好 ultralytics（含 PyTorch） | 5 分钟 |
| 数据 | 收集图片（自拍/下载） | 最花时间 |
| 标注 | 给每把螺丝刀画框 | 第二花时间 |
| 划分 | 拆成"练习册"和"考试卷" | 10 分钟 |
| 训练 | 让模型看图学习 | 等着就行（640 约 15 秒/轮） |
| 评估 | 看成绩单、找错误 | 脑力活 |
| 推理 | 拿新图/视频验证 | 10 分钟 |
| 实时 | 接摄像头，逐帧推理 | 1 小时（含调参） |

---

## 二、各步骤详解与命令参数

### ① 环境准备

```bash
uv venv .venv --python 3.13                        # 建独立 Python 环境，不污染系统
uv pip install -p .venv/bin/python ultralytics     # 装框架（自动带 CUDA 版 torch）
.venv/bin/python -c "import torch; print(torch.cuda.is_available())"   # 必须 True

cd /home/tang/work/AI_Train/YOLO_test
source .venv/bin/activate                          # 之后每个新终端都要激活
```

---

### ② 准备数据

两种来源，各有取舍：

| 来源 | 优点 | 缺点 |
|------|------|------|
| 自己手机拍 | 场景=真实使用场景，模型最对症 | 费时，需标注 |
| Roboflow 下载 | 量大、已有标注、省时 | 场景可能和你的使用环境不同 |

**关键原则：**

- 数据要"杂"：不同背景、光线、角度、距离、颜色。全是同一张桌子拍的，模型会偷懒记住桌子而不是学螺丝刀。
- **训练图里可以混入"不该检出的东西"（扳手、螺丝堆）但不给它们画框**——它们成为背景负样本，教会模型"金属杆状物 ≠ 螺丝刀"，专治乱报。
- 少量"完全没有螺丝刀"的空图也有价值（压低假阳性）。
- 下载的数据注意去重、版权（Roboflow 上 CC BY 4.0 可用，注明来源即可）。

---

### ③ 标注（画框）

工具：[makesense.ai](https://makesense.ai)（浏览器打开即用，图片不上传）。

1. 拖入图片 → 格式选 **Object Detection** → 导出格式选 **YOLO**
2. 类别只建一个：`screwdriver`
3. 每把螺丝刀画一个矩形框（Rect），紧贴物体、别留大空隙、别切掉物体
4. 没有螺丝刀的图：一个框都不画，直接下一张
5. 导出 → 得到一堆 `.txt` 标注文件

**标注质量 = 模型上限**，这步别赶。40 张大约 30~60 分钟。

---

### ④ 数据格式与划分

**YOLO 数据集目录约定**（图和标注同名配对）：

```
dataset/yolo_v4/
├── images/train/xxx.jpg  ←→  labels/train/xxx.txt   （同名！）
├── images/val/yyy.jpg    ←→  labels/val/yyy.txt
└── data.yaml
```

**标注文件内容**（每行一个物体，坐标已归一化到 0~1）：

```
类别号  中心x占比  中心y占比  宽占比  高占比
0       0.375      0.375      0.25    0.25
```

**data.yaml**（告诉训练器数据在哪）：

```yaml
path: dataset/yolo_v4
train: images/train
val: images/val
nc: 1              # 类别数
names:
  0: screwdriver   # 类号 0 的名字
```

#### 划分原理：**按"场景组"划分，不是按文件**

这是本项目踩过的最大的坑之一，务必理解。

**问题**：Roboflow 导出的图片名长这样：

```
000010_jpg.rf.2ce62002166a2921913966b1ed75f0a6.jpg
000010_jpg.rf.af529a13820b4f2e40ffafef720d5086.jpg
000010_jpg.rf.f23ea5576434263d28dd4e40b9dac1df.jpg
        └─ 同一个原始帧 000010，3 个增强副本
```

835 张图实际只有 **273 个真实场景**（261 个外部原始帧 + 12 段自拍连拍）。如果按**文件**随机 8:2 划分，同一帧的 3 个副本会被拆到 train 和 val 两侧——模型在 val 上考的是"自己练过的同一张照片的另一个副本"，分数虚高。

**做法**（`scripts/resplit.py`）：

| 数据来源 | 分组规则 | 组数 |
|---|---|---|
| Roboflow 外部图 | `.rf.` 之前的前缀 = 原始帧号 | 261 |
| 自拍图 | `IMG_YYYYMMDD_HHMM` = 同一分钟连拍 | 12 |

四条规则缺一不可：

1. **按组划分**：同一组的副本整体进 train 或整体进 val
2. **分层抽样**：外部集、自拍集各按 8:2 切，保证 val 里两种来源都有
3. **固定种子**：`--seed 42`，可复现
4. **脚本内置断言**：划分后检查跨组重叠，发现就报错

```bash
# 从零重建（raw -> 完整数据集，一步到位）
python scripts/build_dataset.py --dst dataset/yolo_v4 --val-ratio 0.2 --seed 42

# 只对已有数据集重新划分
python scripts/resplit.py --src <已合并目录> --dst dataset/yolo_v4 --val-ratio 0.2 --seed 42
```

> `build_dataset.py` 负责"装配"：把 `raw/external/train` 和 `raw/mini`+`raw/phtxt/extracted` 统一成
> `images/train` + `labels/train` 布局，再调用 `resplit.py` 的分组划分逻辑。
> 它自带校验（配对完整、跨组零重叠、内容无重复），并支持 `--verify-against` 与已有数据集逐字节比对、
> `--dry-run` 预演不落盘。`raw/external/test` 的 19 张是最终验收集，脚本永不纳入。

当前结果：**train 664 图 / 217 组，val 171 图 / 56 组，跨组重叠 0，内容哈希重复 0**。

> 对比：旧划分 val 只有 13 张且全是自拍，外部集 0 张 → 那个 0.772 的分数是"只在自己桌子上考了 13 道题"。

---

### ⑤ 训练

```bash
yolo detect train \
  model=weights/yolo26n.pt \
  data=dataset/yolo_v4/data.yaml \
  imgsz=640 \
  epochs=300 \
  batch=24 \
  patience=50 \
  optimizer=AdamW \
  lr0=0.0005 \
  warmup_epochs=3 \
  save_period=-1 \
  project=/home/tang/work/AI_Train/YOLO_test/runs/train \
  name=ext_v4e_640 \
  device=0
```

**参数怎么选（经验参考，6GB 的 3050）：**

| 参数 | 建议 | 说明 |
|------|------|------|
| `model` | `weights/yolo26n.pt`（n/s/m/l/x 由小到大） | 从 `.pt` 开始=站在巨人肩膀上 |
| `imgsz` | **640**（见下面"分辨率怎么定"） | 数据原生 512，640 足够 |
| `batch` | 640 下 24~30；1920 下只能 8 | 报 OOM 就减半 |
| `epochs` | 200~500，配合 `patience` 早停 | 小数据集收敛慢，50 轮远远不够 |
| `optimizer` | **必须显式写** `AdamW` 或 `SGD` | 写 `auto` 会忽略你的 `lr0`（见踩坑 #7） |
| `lr0` | 续训 5e-4，从零 1e-3 | 太大把旧特征冲掉 |
| `patience` | 50 | 太小会被正常波动误触发 |
| `save_period` | **-1** | 否则每 N 轮存一个 20MB 完整快照，300 轮能占几百 MB |
| `project` | **绝对路径** | 相对路径会被再拼一层 `runs/detect/`（见踩坑 #8） |

#### 分辨率怎么定：跟着数据走，不是跟着"越大越好"

实测数据（同一份数据集，同一套划分）：

| 训练 imgsz | 轮数 | val mAP50 | 说明 |
|---|---|---|---|
| **1920** | 50 | 0.425 | 没收敛就停，误判为"分辨率不行" |
| **1920** | 300 | 0.803 | 跑满了，但单轮耗时是 640 的 7 倍 |
| **640** | 254 | **0.926** | 当前最优 |

原因：这批数据里 **Roboflow 的图绝大多数是 512×512**。`imgsz=1920` 等于把 512 的图插值放大 **3.75 倍**再喂给模型——算力全花在放大后的模糊像素上，模型学到的也是"模糊纹理"，换到真实拍摄的清晰照片反而失配。

> **结论：imgsz 应该 ≈ 数据集的原始分辨率。** 数据普遍 512 就用 640；等你补了大量 1280×720 自拍图，再考虑 960。

#### 训练时看懂终端输出

```
Epoch GPU_mem box_loss cls_loss l1_loss Instances Size
  3/300  3.78G   1.719    2.961   0.0308     12     640: 3% ━━ 11/42 5.5it/s
Class Images Instances  Box(P   R   mAP50  mAP50-95)   ← 每轮学完立刻在 val 上考一次
all     171     386    0.875  0.814  0.868   0.507
```

| 指标 | 大白话 |
|------|--------|
| box_loss / cls_loss | 框位置的错误分 / 分类的错误分，都越低越好 |
| P（精确率） | 框出来的框里，多少是真的（防误报看它） |
| R（召回率） | 画面里的目标，找到了多少（防漏检看它） |
| mAP50 | **主要成绩单**，框"大概盖住"就算对，0~1 |
| mAP50-95 | 严选版成绩单，要求框贴得准，天然比 mAP50 低 |

**重要**：`loss` 的绝对值不能跨分辨率比较。1920 训练的 `cls_loss` 开局是 53，640 只有 3.8——因为分类损失是在**全部候选网格点**上求和的，1920 的网格数是 640 的 9 倍。跨分辨率只能比 `mAP`。

---

### ⑥ 评估

```bash
yolo detect val \
  model=runs/train/ext_v4d_640_orin/weights/best.pt \
  data=dataset/yolo_v4/data.yaml
```

产物在训练文件夹里：

- `best.pt`（mAP 最高的权重，**部署就用它**） / `last.pt`
- `results.csv`（每轮指标，一行一轮）、`results.png`（曲线）
- `confusion_matrix.png`（误判分布）
- `val_batch0_labels.jpg` vs `val_batch0_pred.jpg`（标准答案 vs 模型答卷）

**最重要的一课：val 分数可能骗你。** 如果 val 和训练图同源（都来自同一个 Roboflow 数据集），模型是"背熟了这批图的风格"，换个场景就现原形。

所以本仓库专门留了 `dataset/val_final`（19 张从未参与训练的图）和 `dataset/test`（3 张你自己的实拍 + 1 段视频）。**最终验收必须用你自己的实拍图**，那是唯一有意义的成绩。

---

### ⑦ 推理（日常使用）

```bash
yolo detect predict \
  model=runs/train/ext_v4d_640_orin/weights/best.pt \
  source=dataset/test \
  imgsz=640 \
  conf=0.25 \
  save=True \
  project=/home/tang/work/AI_Train/YOLO_test/outputs \
  name=test_640
```

两个必须写清楚的：

- **`imgsz`**：不写会**继承权重里的训练尺寸**（实测确认：模型 `overrides` 里存着 `imgsz=1920`）。所以别以为不写就是 640。
- **`project`**：写绝对路径，否则 ultralytics 会在你给的相对路径前再拼 `runs/detect/`，产出 `runs/detect/runs/train/...` 这种嵌套目录。

`conf` 是 P/R 跷跷板的滑杆，但注意它只是**后处理筛子**：模型给出 0.03 的框，你把 conf 降到 0.15 也永远看不见。想确认"是没认出来还是被阈值卡住"，直接跑 `conf=0.01` 看有没有框。

---

### ⑧ 实时摄像头检测

```bash
python scripts/realtime.py                    # 默认 1280x720@30，imgsz=640
python scripts/realtime.py --conf 0.15        # 放低阈值看召回
python scripts/realtime.py --no-show          # 无显示器（Jetson / SSH）
```

按 `q` 退出。

#### 原理：一帧要走五道工序

```
读一帧 → 缩放到 640 → 前向推理 → NMS 解码 → 画框 → 显示 → 读下一帧
 采集       预处理       推理       后处理     绘制
```

FPS = 1 / 一圈总耗时，由**最慢那一环**决定。RTX 3050 上各环节实测：

| 环节 | 耗时 |
|---|---|
| 采集（MJPG 解码） | 3~5 ms |
| 预处理（letterbox） | 1~2 ms |
| **推理（yolo26n @640）** | **8~10 ms** |
| 后处理（NMS） | 1~2 ms |
| 绘制 + imshow | 2~4 ms |

模型只需要 10ms → 理论上限 100fps，**瓶颈几乎总在摄像头**。

#### 三个必须知道的硬件事实

**1. USB 2.0 带宽强制你用 MJPG**

| 格式 | 每帧 | 720p30 需要 | 结论 |
|---|---|---|---|
| YUYV（未压缩） | 1.8 MB | 553 Mbps | ❌ 超 USB2.0 的 480 Mbps |
| MJPG（压缩） | 100~200 KB | 24~48 Mbps | ✅ |

所以要显式设 `cv2.CAP_PROP_FOURCC = MJPG`。不设可能协商成 YUYV，表现为"720p 却只有 8fps"。

**2. 缓冲队列会让画面滞后**

摄像头是固定 30fps 的生产者，你的循环是消费者。不清队列，你处理的就是几秒前的帧。

```python
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # 只保留最新一帧
```

**3. 自动曝光会把帧率腰斩**

暗光下摄像头把曝光时间拉长到 66ms 来凑亮度，帧率就从 30 掉到 15。**这不影响清晰度，只影响帧率**。判据：把灯打开再测，帧率上来就是它。

#### 验收标准

| 检查 | 期望 | 不符合说明 |
|---|---|---|
| 启动打印格式 | `MJPG` | YUYV → 带宽瓶颈 |
| 启动打印分辨率 | `1280x720 @ 30fps` | 掉到 640x480 → 不支持该组合 |
| 推理耗时 | 8~12 ms | > 30ms → 没走 GPU |
| 窗口 FPS | 接近摄像头实际帧率 | 明显更低 → 绘制/显示慢 |

---

## 三、关键概念速查

| 概念 | 一句话解释 |
|------|-----------|
| 迁移学习 | 拿预训练好的 `.pt` 权重继续训练，比从零快得多、要的数据少得多 |
| 过拟合 | 把训练数据背得滚瓜烂熟，换个场景就废。信号：train loss 降、val loss 升 |
| 泛化 | 模型在没见过的数据上也能打。一切努力都是为了它 |
| 域偏移 | 训练图和实际使用场景的分布不同（背景/光照/物体外观），是 mAP 高但实测差的主因 |
| 负样本/背景图 | 没有目标的图（或目标不画框），教模型"这里没有"，减少乱报 |
| IoU | 预测框和答案框的重叠程度，≥0.5 算对（mAP50）、更严算对（mAP50-95） |
| 单变量原则 | 一次实验只改一个参数，否则无法归因 |
| 数据增强 | 训练时自动对图做翻转/裁剪/调色（ultralytics 默认开）；Roboflow 还额外导出过离线增强副本 |
| BN running stats | 批归一化的滑动统计量，对输入尺度敏感；换分辨率续训时前几百步会重估 |

---

## 四、踩坑记录（含教训）

| # | 现象 | 原因 | 教训 |
|---|------|------|------|
| 1 | v1 val mAP50=0.867，新场景却漏检/乱报 | val 与训练集同分布（都是同一天拍的） | **val 高≠真的好**，要用部署场景的图验收 |
| 2 | v1 把螺丝误判成螺丝刀 | 训练集没有螺丝堆这类负样本 | 干扰物要进训练图（不画框） |
| 3 | mini_v2 imgsz=1280 训练崩（mAP 0.064） | 42 张小数据 + 高分辨率 + batch 减半 | 小数据别盲目调大分辨率 |
| 4 | val 里一张背景图都没有 | 8:2 随机划分没分层 | 划分后检查构成 |
| 5 | 同一原始帧的 3 个增强副本被拆到 train/val | 按文件划分 | **按场景组划分**，脚本内断言校验 |
| 6 | 1920 训 300 轮耗时 7.5 小时，效果不如 640 训 254 轮 | 数据原生 512，1920 是放大 3.75 倍的插值图 | **imgsz ≈ 数据原始分辨率** |
| 7 | 写了 `lr0=0.001` 但日志显示 `AdamW(lr=0.002)` | `optimizer=auto` 会忽略 `lr0` 自己定 | 必须显式 `optimizer=AdamW lr0=...` |
| 8 | 训练结果跑到 `runs/detect/runs/train/...` | 相对 `project=` 被 ultralytics 再拼一层 | `project` 写**绝对路径** |
| 9 | `yolo predict` 不写 `imgsz` 却按 1920 跑 | 权重里存着训练时的 args，推理会继承 | 推理显式写 `imgsz` |
| 10 | 降 `conf` 到 0.15 仍然"识别不到" | `conf` 是后处理筛子，救不回根本没激活的框 | 用 `conf=0.01` 区分"不敢说"和"看不见" |
| 11 | `pkill -f "yolo detect train"` 把自己终端杀了 | `-f` 匹配完整命令行，pkill 自身也含这串字 | `pgrep -af "[y]olo detect"` 取 PID 再 `kill` |
| 12 | 训练目录每轮涨 20MB | `save_period=25` 存完整快照（含 AdamW 动量） | `save_period=-1`，只要 best/last |
| 13 | `wc -l` 数标签框数偏少 | 最后一行没有换行符时 `wc -l` 不计数 | 用 Python 逐行统计 |
| 14 | 训练日志里全是乱码/重复行 | 进度条用 `\r` 原地刷新，重定向到文件后每次都追加 | 看日志先 `tr '\r' '\n'` |
| 15 | 摄像头 720p 只有 15fps | 暗光自动曝光把曝光时间拉到 66ms | 改善照明，或锁定曝光 |

---

## 五、模型成绩单

| 版本 | 数据 | imgsz | 轮数 | val mAP50 | val mAP50-95 | 备注 |
|---|---|---|---|---|---|---|
| mini_v1 | 42 张自拍 | 640 | 30 | 0.867 | 0.533 | val 与训练同源，虚高 |
| mini_v2 | 42 张自拍 | 1280 | 11 | 0.064 | — | 失败实验，早停 |
| ext_v3 | 822 张 | 960 | 50 | 0.772 | — | val 13 张全是自拍，不可信 |
| ext_v4 | 664/171（新划分） | 1920 | 50 | 0.425 | 0.160 | 未收敛 |
| ext_v4b | 664/171 | 1920 | 300 | 0.803 | 0.440 | 跑满，但耗时 7.5h |
| ext_v4c | 664/171 | 640 | 54 | 0.873 | 0.530 | 中途停止，目录已清理 |
| ext_v4d_640_coco | 664/171 | 640 | 252 | 0.882 | 0.580 | 从 1920 权重续训 |
| **ext_v4d_640_orin** | 664/171 | **640** | 266 | **0.926** | **0.696** | **当前最优**，从 COCO 起步 |

结论一句话：**数据的数量和多样性 >> 一切调参**；而在数据有限时，**训练分辨率要贴着数据走**。

**当前已知弱点**：真实自拍场景（桌面、自然光、远景小目标）的表现仍明显弱于 val；273 个真实场景里只有 12 段是你的拍摄场景，这是域偏移的根源。

---

## 六、常见报错排查

| 报错/现象 | 怎么办 |
|-----------|--------|
| `torch.cuda.is_available()` 返回 False | 查 `nvidia-smi`；确认装的是 CUDA 版 torch |
| `CUDA out of memory` | batch 减半，或 imgsz 调小 |
| `FileNotFoundError: .../weights/best.pt` | 训练还没跑完，或 `runs/` 被清理过；长期存放的模型在 `models/` |
| 训练提前结束、打印 EarlyStopping | 正常，连续 patience 轮 val 没进步自动停 |
| mAP 一直是 0.0x 不涨 | 先查数据：图片与标签同名配对？坐标 0~1？类号对？ |
| 新图检不出 | 先确认 `imgsz` 与训练一致，再用 `conf=0.01` 看有没有框 |
| 摄像头打开失败 | `ls -l /dev/video*`；`fuser -v /dev/video0` 看是否被占用 |
| 实时画面滞后 | `CAP_PROP_BUFFERSIZE=1`；关掉其他占带宽的 USB 设备 |

---

## 七、本仓库目录速查

```
YOLO_test/
├── PLAN.md                       # 进度打勾清单 + 版本对比复盘
├── README.md                     # 本文
├── .venv/                        # Python 虚拟环境（不入库）
├── scripts/
│   ├── build_dataset.py          # 从 raw/ 一步重建数据集（装配 + 划分 + 校验）
│   ├── resplit.py                # 只做划分：按场景组 8:2（含防泄露断言）
│   └── realtime.py               # 摄像头实时检测
├── dataset/
│   ├── raw/external/             # Roboflow 原始下载（783+52+19，CC BY 4.0）
│   ├── raw/mini/                 # 自拍原图 52 张（全分辨率底片）
│   ├── raw/phtxt/                # 标注 zip + 解出的 txt
│   ├── yolo_v4/                  # 当前训练集 664 train / 171 val（含 data.yaml）
│   ├── val_final/                # 19 张终验图（从未参与训练）
│   └── test/                     # 3 张实拍 + 1 段视频
├── weights/
│   └── yolo26n.pt                # 预训练权重（不入库，可重新下载）
├── models/                       # 训练完成的模型（入库）
├── runs/                         # 训练过程产物（曲线/CSV/混淆矩阵，不入库）
├── outputs/                      # 推演结果（不入库）
└── logs/                         # 训练日志（不入库）
```

模型使用一行命令：

```bash
yolo detect predict model=runs/train/ext_v4d_640_orin/weights/best.pt \
  source=你的图片或视频 imgsz=640 conf=0.25 save=True
```

---

## 八、下一步可选方向

1. **补自有场景数据**（最重要）：桌面/自然光/远景/多角度，目标 300~500 张，这是打破域偏移的唯一办法
2. **方向识别（0~360°）**：普通检测框只能给"在哪"。要"刀尖朝哪"需 Pose 双关键点（柄尾 + 刀尖），OBB 只能给轴线角度（0~180°）
3. **导出 ONNX / TensorRT**：`yolo export model=best.pt format=engine half=True imgsz=640`，注意 engine 绑定 GPU 架构，PC 导的不能给 Jetson 用
4. **多类别扩展**：扳手/钳子/电钻正式标注为 1、2 类
5. **子类细分**：十字 / 一字 / 电动螺丝刀
