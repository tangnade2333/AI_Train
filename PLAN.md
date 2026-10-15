# 螺丝刀（screwdriver）目标检测 · YOLO 训练计划

- **目标类别**：`0: screwdriver`（单类别，不细分十字/一字）
- **干扰物策略**：扳手/钳子等拍进图但**不标注**（成为背景，模型学会区分）
- **数据来源**：自拍为主 + 网络下载补充
- **训练目标**：能对本地图片/视频推理
- **总策略**：先用 50 张迷你集**跑通全流程** → 再扩到 200~300 张迭代放大
- **硬件**：RTX 3050 6GB / Python 3.13 / uv + conda 已就绪

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

## 三代模型终局对比

| | mini_v1 | mini_v2 | ext_v3 |
|---|---|---|---|
| 训练数据 | 42 张自拍 | 42 张自拍 | 822 张（783 外部+39 自拍） |
| imgsz | 640 | 1280 | 960 |
| val mAP50 | 0.867（虚高） | 0.064（失败，早停） | 0.772（诚实） |
| 红柄螺丝刀（自拍新图） | 漏检 0 | — | **检出 0.26** |
| 螺丝堆（网图） | 碎框+3 个螺丝误报 | — | **单框 0.74，零误报** |
| 4 把黄柄（产品图） | 3 乱框 | — | 3 框（0.63/0.63/0.47），仍不完美 |
| 视频 | — | — | 可检出 |

**核心教训**
1. 数据量与多样性 >> 一切调参（1→3 是 20 倍数据带来的质变）
2. val 与训练集同分布时指标虚高，**新场景实测才是真成绩**
3. 失败的 mini_v2 同样有价值：用数据否定了"高分辨率救小数据"的假设
4. 单变量对比原则让每一代结论都可归因
5. conf 阈值是 P/R 的滑杆，部署时按场景调

**当前已知弱点**（下一阶段素材）：密集平行摆放的多把螺丝刀仍框不准；红柄置信度仅 0.26；缺自有场景螺丝堆负样本。

## 全流程命令链（复盘用）

```bash
# 环境
uv venv .venv --python 3.13 && uv pip install -p .venv/bin/python ultralytics
# 数据划分 / 外部合并
python3 scripts/split.py && python3 scripts/merge_external.py
# 训练
.venv/bin/yolo detect train model=yolo26n.pt data=dataset/yolo_ext/data.yaml \
  epochs=50 imgsz=960 batch=8 patience=15 project=runs/detect name=ext_v3
# 评估 / 推理
.venv/bin/yolo detect val model=runs/detect/runs/detect/ext_v3/weights/best.pt data=dataset/yolo_ext/data.yaml
.venv/bin/yolo detect predict model=runs/detect/runs/detect/ext_v3/weights/best.pt source=dataset/test conf=0.25 save=True
```

---

## 阶段 C：可选延伸（按需添加）

- [ ] C.1 导出 ONNX 格式
- [ ] C.2 摄像头实时检测
- [ ] C.3 扩展类别：扳手/钳子/电钻正式标注为多类别
- [ ] C.4 细分螺丝刀子类：十字 / 一字 / 电动

---

## 变更记录

| 日期 | 变更 |
|------|------|
| 2026-10-09 | 制定初始计划：单类别 screwdriver，先跑通后放大 |
| 2026-10-15 | 阶段 A 跑通：mini_v1 mAP50=0.867；Step7 新场景暴露泛化问题（漏检/误报/框破碎） |
| 2026-10-15 | imgsz=1280 实验（mini_v2）失败：早停于第 11 轮，mAP50=0.064。结论=数据量优先于分辨率调参 |
| 2026-10-15 | 阶段 B 完成：Roboflow 854 张合并自拍 39 张 → ext_v3（imgsz=960）val mAP50=0.772，新场景测试全面优于 v1。当前 best.pt=ext_v3 |
