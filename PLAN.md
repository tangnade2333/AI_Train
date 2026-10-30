# 螺丝刀（screwdriver）目标检测 · YOLO 训练计划

- **目标类别**：`0: screwdriver`（单类别，不细分十字/一字）
- **干扰物策略**：扳手/钳子等拍进图但**不标注**（成为背景，模型学会区分）
- **数据来源**：Roboflow 外部集（CC BY 4.0）为主 + 自拍 52 张
- **训练目标**：本地图片/视频推理 + 摄像头实时检测
- **总策略**：先用 50 张迷你集**跑通全流程** → 扩到 800+ 张 → 重做「按场景组」划分 → 分辨率实验定型 → 接摄像头
- **硬件**：RTX 3050 6GB / Python 3.13 / uv + conda 已就绪
- **当前状态**：最优模型 `runs/train/ext_v4d_640_orin/weights/best.pt`（imgsz=640，val mAP50=0.926），实时检测脚本已跑通

---

## 阶段 A：先跑通全流程（迷你数据集 50 张）

### Step 1 环境准备
- [x] 1.1 用 uv 创建虚拟环境 `.venv`
- [x] 1.2 安装 `ultralytics`（自动带 PyTorch CUDA）— torch 2.14.1+cu130 / ultralytics 8.4.177
- [x] 1.3 验证 GPU 可用（`torch.cuda.is_available()` == True）— RTX 3050 / CUDA 13.0
- [x] 1.4 Smoke test：`yolo checks` + 官方示例图跑通 `yolo detect predict` 出框 — bus.jpg 检出 4 persons + 1 bus

> 📚 学习点：`.pt` 权重文件、预训练模型、CUDA 推理

### Step 2 理解任务与数据格式
- [x] 2.1 理解目标检测三要素：bbox + 类别 + 置信度
- [x] 2.2 理解 YOLO 标签格式 `class x_center y_center w h`（归一化 0~1）— 手算验收 3/4 通过（中心x 计算顺序错误已纠正）
- [x] 2.3 理解 `images/` 与 `labels/` 同名配对的目录约定
- [x] 2.4 理解 `data.yaml` 的作用

> ✅ 验收：给一个像素坐标框，能手算出归一化标签行 — 已通过（示例见 demo/step2/）

### Step 3 采集迷你数据集（50 张）
- [x] 3.1 手机拍螺丝刀照片（实拍 40 张，自定场景/角度，分辨率 3000×3000）
- [x] 3.2 拷贝到 `dataset/raw/mini/`，程序检查：无近似重复、平均色差 145（场景多样性良好）

### Step 4 标注
- [x] 4.1 用 makesense.ai 导入图片，导出 YOLO 格式 — 两次导出，有效包为 11-46-25（40 txt），11-51-03 为空包可删
- [x] 4.2 按规范标注：每个螺丝刀单独一框、完整贴合 — 共 140 框，平均 3.5 框/图
- [x] 4.3 校验：labels 与 images 一一对应、无空 txt、坐标在 0~1 — 程序校验 0 问题

> 📚 学习点：标注质量 = 模型上限

### Step 5 划分与配置
- [x] 5.1 写 `scripts/split.py` 按 8:2 固定种子划分 train/val — train=39 图/30 标注，val=13 图/10 标注
- [x] 5.2 创建 `dataset/yolo/data.yaml`（path/train/val/names/nc）
- [x] 5.3 修正：随机划分导致 val 无背景图，手动挪 3 张背景图进 val（val 现含 3 张负样本，可测误检）

### Step 6 首次训练
- [x] 6.1 启动训练：`yolo26n.pt`、epochs=30、imgsz=640、batch=8、patience=10 — 30 轮完成，用时约 30 秒 GPU 训练
- [x] 6.2 解读训练指标：前 11 轮 mAP50≈0.06（学习期），12 轮起飞，最终 mAP50=0.867 / mAP50-95=0.533 / P=0.869 / R=0.76
- [x] 6.3 检查产物：`results.png`、混淆矩阵、`best.pt` 均生成于 `runs/detect/runs/detect/mini_v1/`

> 📚 学习点：迁移学习（用 `.pt` 而非 `.yaml` 起步）、过拟合的信号

### Step 7 评估与推理
- [x] 7.1 `yolo detect val` 单独验证，看 Precision/Recall
- [x] 7.2 `yolo detect predict` 对训练集外的本地图片 + 一段视频推理 — 4 个测试文件跑通
- [x] 7.3 错误分析 — 三类典型错误：①新场景整把漏检 ②螺丝被误判为螺丝刀 ③多把螺丝刀时框破碎/数量错。结论：val 0.867 虚高（与训练集同分布），瓶颈=数据多样性而非 imgsz

### Step 7.5 追加实验：imgsz=1280（mini_v2）
- [x] 假设"提高分辨率可提升效果" → 单变量实验：仅改 imgsz=1280/batch=4
- [x] 结果：**失败**。cls_loss 从 epoch 1 起即 31.8（v1 为 7.9）且不降，mAP50 停在 0.064，第 11 轮触发早停
- [x] 结论：n=42 的小数据集上高分辨率反而破坏训练稳定性；**此假设被实验否定**。数据量升至 200+ 后再重试（届时优先试 960）

### Step 8 复盘
- [x] 8.1 总结 mini 流程跑通的完整命令链（见下方「全流程命令链」）
- [x] 8.2 bad case 清单：红柄/异色漏检、螺丝误报、多把框破碎 → 驱动阶段 B 数据方向

---

## 阶段 B：放大到正式数据集（已完成）

### Step 9 扩采数据
- [x] 9.1 改走 Roboflow 路线（用户不自拍）：`universo/screwdriver-paveq` 854 张，CC BY 4.0，单类 nc=1 免合并
- [x] 9.2 bad case 覆盖：外部集含多色手柄/多把成排/产品图场景，对症 Step 8.2 清单
- [ ] 9.3 自有场景干扰物补拍（螺丝堆背景图等）— 仍缺，是当前模型剩余弱点的来源

### Step 10 数据合并（替代原"预标注"路线）
- [x] 10.1 ~~用 best.pt 预标注~~ → 改用外部数据集，省去标注人力（预标注技巧留待后续自采时使用）
- [x] 10.2 外部集程序校验：783+52+19 图、坐标全部合法、类号全 0
- [x] 10.3 `scripts/merge_external.py`：train=外部783+自拍39=822，val=仅自拍13（考题贴近部署场景）

### Step 11 迭代训练与对比
- [x] 11.1 训练 ext_v3（822 张，imgsz=960，batch=8，epochs=50）：val mAP50=0.772
- [x] 11.2 实验记录：mini_v2（1280/42张）失败；ext_v3（960/822张）成功 — 分辨率放大的前提是数据量
- [x] 11.3 当前最优：`runs/detect/runs/detect/ext_v3/weights/best.pt`

---

## 阶段 C：重做数据划分 + 分辨率定型 + 实时检测（2026-10-29 ~ 10-30）

### Step 12 发现旧划分的两处缺陷
- [x] 12.1 旧 val 仅 13 张且**全为自拍**，外部集 0 张 → 0.772 不可信（同分布 + 样本太少）
- [x] 12.2 外部 783 张图实为 **261 个原始帧 × 3 个增强副本**（`.rf.<hash>`）；自拍 52 张集中在 12 个分钟段
- [x] 12.3 按文件随机划分会让同一帧的副本跨 train/val → 数据泄露，分数虚高

### Step 13 按「场景组」重新划分（`scripts/resplit.py`）
- [x] 13.1 分组规则：外部图按 `.rf.` 之前的前缀 = 原始帧；自拍按 `IMG_YYYYMMDD_HHMM` = 分钟段
- [x] 13.2 分层抽样（外部 / 自拍各自 8:2）+ 固定种子 42 + 脚本内防泄露断言
- [x] 13.3 产出 `dataset/yolo_v4`：train 664 图 / 653 标签（1233 框），val 171 图 / 170 标签（386 框）
- [x] 13.4 校验：跨组重叠 0、图片内容哈希重复 0、val 含外部 159 + 自拍 12
- [x] 13.5 关键认知：835 张图实际只有 **273 个真实场景**（261 帧 + 12 段连拍）

### Step 14 分辨率实验（关键结论）
- [x] 14.1 统计发现：Roboflow 图**中位尺寸仅 512×512**，最大 4000×3000；自拍为 800×571 ~ 3000×3000
- [x] 14.2 ext_v4（imgsz=1920，50 轮）：mAP50=0.425 / mAP50-95=0.160，曲线仍在涨 → 判定为「欠训练」而非「分辨率不行」
- [x] 14.3 ext_v4b（imgsz=1920，300 轮，lr0=0.001 续训）：mAP50=0.803 / 0.440，耗时 7.5 小时
- [x] 14.4 ext_v4c（imgsz=640，续训）：54 轮即达 0.873 / 0.530，**超过 1920 跑满 300 轮**
- [x] 14.5 ext_v4d_640_coco（640，batch 24，lr0=5e-4，252 轮）：0.882 / 0.580
- [x] 14.6 ext_v4d_640_orin（640，batch 30，lr0=5e-4，从 COCO 起步，266 轮）：**0.926 / 0.696 当前最优**
- [x] 14.7 结论：**imgsz 应贴着数据原始分辨率**。这批数据 512 → 640 最优；1920 等于把图插值放大 3.75 倍，算力与效果双输

### Step 15 实时摄像头检测（`scripts/realtime.py`）
- [x] 15.1 设备确认：SHUNCCM USB 2.0 Camera，MJPG 1280×720@30 可用
- [x] 15.2 脚本：MJPG 强制协商 + `BUFFERSIZE=1` + `imgsz=640` + 30 帧滑动窗口 FPS + `--no-show` 无显示器模式
- [x] 15.3 实测：推理 8~10ms（理论 100fps），但采集仅 **15~20fps** → 瓶颈在摄像头（暗光自动曝光把曝光时间拉到 66ms）
- [x] 15.4 验收通过：能稳定出框、按 q 退出、显存与耗时正常
- [ ] 15.5 待办：改善照明或锁定曝光，把帧率拉回 30

### Step 16 目录治理
- [x] 16.1 清理重复：删除 `dataset/yolo_ext`（105M，与 yolo_v4 逐字节相同的旧划分副本，835 张全同）
- [x] 16.2 四类分区：`dataset/`（数据）、`weights/`（预训练）、`models/`（训练完成）、`outputs/`（推演结果）
- [x] 16.3 训练过程归 `runs/<版本>/`，日志归 `logs/`，`models/*.pt` 入库、`weights/*.pt` 不入库
- [x] 16.4 修复 ultralytics 输出嵌套（相对 `project=` 被再拼一层 `runs/detect/`）

### Step 17 重建脚本（`scripts/build_dataset.py`）
- [x] 17.1 背景：旧的 `merge_external.py` / `split.py` 已废弃，`raw → 训练集` 的重建路径中断
- [x] 17.2 一步到位：收集 `raw/external/train` + `raw/mini`（标签配 `raw/phtxt/extracted`）→ 装配 → 按场景组划分
- [x] 17.3 复用 `resplit.py` 的分组逻辑，避免两套规则各写一遍而逐渐分歧
- [x] 17.4 内置校验：配对完整、孤儿标签、跨组重叠、内容哈希重复；另有 `--dry-run` / `--verify-against` / `--force`（覆盖前自动备份）
- [x] 17.5 验证：重建到临时目录后与现有 `dataset/yolo_v4` **835 张逐字节一致**（train 664 / val 171 / 重叠 0）


---


## 模型版本总表

| 版本 | 数据 | imgsz | 轮数 | val mAP50 | val mAP50-95 | 评价 |
|---|---|---|---|---|---|---|
| mini_v1 | 42 张自拍 | 640 | 30 | 0.867 | 0.533 | val 与训练同源，虚高 |
| mini_v2 | 42 张自拍 | 1280 | 11 | 0.064 | — | 失败实验（早停） |
| ext_v3 | 822 张（旧划分） | 960 | 50 | 0.772 | — | val 13 张全自拍，不可信 |
| ext_v4 | 664/171（新划分） | 1920 | 50 | 0.425 | 0.160 | 欠训练，曲线仍在涨 |
| ext_v4b | 664/171 | 1920 | 300 | 0.803 | 0.440 | 跑满，7.5 小时 |
| ext_v4c | 664/171 | 640 | 54 | 0.873 | 0.530 | 中途停止（目录已清理） |
| ext_v4d_640_coco | 664/171 | 640 | 252 | 0.882 | 0.580 | 从 1920 权重续训 |
| **ext_v4d_640_orin** | 664/171 | **640** | 266 | **0.926** | **0.696** | **当前最优**，从 COCO 起步 |

**核心教训**

1. 数据量与多样性 >> 一切调参（42 → 835 张是质变）
2. val 与训练集同分布时指标虚高，**新场景实测才是真成绩**
3. 失败的实验同样有价值：mini_v2 否定「小数据+高分辨率」，ext_v4 系列说明「欠训练≠分辨率无效」
4. **imgsz 要贴着数据原始分辨率**：这批数据 512×512，640 打满 0.926，1920 只有 0.803 且慢 7 倍
5. 划分必须**按场景组**，否则同帧增强副本跨 train/val，分数虚高
6. 单变量对比原则让每一代结论都可归因

**当前已知弱点**

- 真实自拍场景（桌面、自然光、远景小目标）仍明显弱于 val → **域偏移**，273 个场景里只有 12 段是自有拍摄
- 密集平行摆放的多把螺丝刀仍框不准
- 缺自有场景的螺丝堆负样本
- 实时采集只有 15~20fps（自动曝光），离 30fps 还有差距


## 全流程命令链（复盘用）

```bash
# 0. 环境
cd /home/tang/work/AI_Train/YOLO_test && source .venv/bin/activate

# 1. 数据划分（按场景组 8:2，含防泄露断言）
python scripts/resplit.py --src <源目录> --dst dataset/yolo_v4 --val-ratio 0.2 --seed 42

# 2. 训练（imgsz 贴着数据原始分辨率；optimizer 必须显式写，否则 lr0 被忽略）
setsid nohup yolo detect train \
  model=weights/yolo26n.pt data=dataset/yolo_v4/data.yaml \
  imgsz=640 epochs=300 batch=24 patience=50 \
  optimizer=AdamW lr0=0.0005 warmup_epochs=3 save_period=-1 \
  project=/home/tang/work/AI_Train/YOLO_test/runs/train name=ext_v4e_640 device=0 \
  > logs/ext_v4e_640.log 2>&1 < /dev/null &

# 3. 监控（进度条用 \r 刷新，必须转换）
tr '\r' '\n' < logs/ext_v4e_640.log | grep -a "100%" | tail -3
awk -F, 'NR>1{printf "ep %-4s mAP50=%-7.3f\n",$1,$8}' runs/train/ext_v4e_640/results.csv | tail -5

# 4. 评估 / 推理（imgsz 与训练一致；project 用绝对路径）
yolo detect val model=runs/train/ext_v4d_640_orin/weights/best.pt data=dataset/yolo_v4/data.yaml imgsz=640
yolo detect predict model=runs/train/ext_v4d_640_orin/weights/best.pt \
  source=dataset/test imgsz=640 conf=0.25 save=True \
  project=/home/tang/work/AI_Train/YOLO_test/outputs name=test_640

# 5. 实时摄像头
python scripts/realtime.py                  # 按 q 退出
python scripts/realtime.py --no-show        # 无显示器
```

---

## 阶段 D：可选延伸（按需添加）

- [ ] D.1 导出 ONNX 格式
- [x] D.2 摄像头实时检测（`scripts/realtime.py` 已跑通，帧率待优化）
- [ ] D.3 方向识别 0~360°（Pose 双关键点：柄尾 + 刀尖；OBB 只能给轴线角度）
- [ ] D.4 扩展类别：扳手/钳子/电钻正式标注为多类别
- [ ] D.5 细分螺丝刀子类：十字 / 一字 / 电动
- [ ] D.6 导出 TensorRT engine 上 Jetson（engine 绑定 GPU 架构，PC 导的不能给 Orin 用）
- [ ] D.7 补自有场景数据 300~500 张（打破域偏移的唯一办法）

---

## 变更记录

| 日期 | 变更 |
|------|------|
| 2026-10-09 | 制定初始计划：单类别 screwdriver，先跑通后放大 |
| 2026-10-15 | 阶段 A 跑通：mini_v1 mAP50=0.867；Step7 新场景暴露泛化问题（漏检/误报/框破碎） |
| 2026-10-15 | imgsz=1280 实验（mini_v2）失败：早停于第 11 轮，mAP50=0.064。结论=数据量优先于分辨率调参 |
| 2026-10-15 | 阶段 B 完成：Roboflow 854 张合并自拍 39 张 → ext_v3（imgsz=960）val mAP50=0.772，新场景测试全面优于 v1。当前 best.pt=ext_v3 |
| 2026-10-29 | 发现旧划分两处缺陷（val 仅 13 张全自拍、同帧增强副本跨 split）；写 `resplit.py` 按场景组重划 → `dataset/yolo_v4`（664/171） |
| 2026-10-29 | ext_v4（1920/50 轮）mAP50=0.425，判定为欠训练；启动 1920 通宵续训 |
| 2026-10-30 | ext_v4b（1920/300 轮）mAP50=0.803，耗时 7.5h |
| 2026-10-30 | 认知修正：数据中位尺寸 512×512，1920 属于插值放大。ext_v4c（640）54 轮即达 0.873 |
| 2026-10-30 | ext_v4d 系列定型：640 + batch 24~30 + lr0=5e-4，最高 mAP50=0.926（从 COCO 起步） |
| 2026-10-30 | 实时检测跑通：`scripts/realtime.py`，推理 8~10ms，采集受暗光自动曝光限制在 15~20fps |
| 2026-10-30 | 目录治理：删除与 yolo_v4 逐字节重复的 `yolo_ext`（105M），四类分区（dataset/weights/models/outputs） |
| 2026-10-30 | 重写 README（新增划分原理、分辨率结论、实时检测、15 条踩坑）并更新本计划 |
| 2026-10-30 | 删除废弃脚本 `scripts/split.py`（按文件划分的错误做法）与 `scripts/merge_external.py`（引用已删除目录）；保留 `resplit.py` + `realtime.py` |
| 2026-10-30 | 新增 `scripts/build_dataset.py`：`raw → 训练集` 一步重建，自带校验；实测与现有 yolo_v4 逐字节一致 |

