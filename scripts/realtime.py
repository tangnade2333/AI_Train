#!/usr/bin/env python3
"""实时螺丝刀检测：USB 摄像头 -> YOLO -> 屏幕显示。

用法：
    python scripts/realtime.py                 # 默认 640 模型，1280x720@30
    python scripts/realtime.py --conf 0.15     # 放低阈值看召回
    python scripts/realtime.py --no-show       # 无显示器（Jetson / SSH），只打印统计
    python scripts/realtime.py --src 2         # 换摄像头节点

按 q 退出。
"""
import argparse
import time
from collections import deque

import cv2
from ultralytics import YOLO

DEFAULT_MODEL = "runs/train/ext_v4d_640_orin/weights/best.pt"


def parse_args():
    p = argparse.ArgumentParser(description="实时螺丝刀检测")
    p.add_argument("--model", default=DEFAULT_MODEL, help="权重路径")
    p.add_argument("--src", default=0, type=int, help="摄像头编号，对应 /dev/videoN")
    p.add_argument("--imgsz", default=640, type=int, help="推理尺寸，必须与训练一致")
    p.add_argument("--conf", default=0.25, type=float, help="置信度阈值")
    p.add_argument("--width", default=1280, type=int, help="采集宽度")
    p.add_argument("--height", default=720, type=int, help="采集高度")
    p.add_argument("--fps", default=30, type=int, help="请求的采集帧率")
    p.add_argument("--no-show", action="store_true", help="不弹窗，只打印统计")
    return p.parse_args()


def open_camera(a):
    """打开摄像头并强制 MJPG：USB 2.0 带宽下，YUYV 720p30 需要 553Mbps > 480Mbps。"""
    cap = cv2.VideoCapture(a.src)
    if not cap.isOpened():
        raise SystemExit(f"无法打开摄像头 {a.src}：检查是否被占用，或试试 --src 2")

    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, a.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, a.height)
    cap.set(cv2.CAP_PROP_FPS, a.fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 只保留最新一帧，否则画面会越来越滞后

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC)).to_bytes(4, "little").decode(errors="replace")
    print(f"摄像头 {a.src}: {w}x{h} @ {fps:.0f}fps  格式 {fourcc}")

    if fourcc != "MJPG":
        print("⚠️  没有协商到 MJPG，帧率可能只有 5~10fps")
    if (w, h) != (a.width, a.height):
        print(f"⚠️  分辨率未生效，实际 {w}x{h}")
    return cap


def main():
    a = parse_args()
    model = YOLO(a.model)
    print(f"模型: {a.model}  imgsz={a.imgsz}  conf={a.conf}")
    cap = open_camera(a)

    times = deque(maxlen=30)  # 最近 30 帧的完成时刻 -> 滑动平均 FPS
    n = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("cap.read() 失败，退出")
                break

            t0 = time.perf_counter()
            r = model.predict(frame, imgsz=a.imgsz, conf=a.conf, verbose=False)[0]
            infer_ms = (time.perf_counter() - t0) * 1000

            vis = r.plot()
            times.append(time.perf_counter())
            n += 1

            fps = 0.0
            if len(times) >= 2:
                fps = (len(times) - 1) / (times[-1] - times[0])

            cv2.putText(
                vis,
                f"FPS {fps:4.1f} | det {len(r.boxes)} | {infer_ms:4.1f}ms",
                (10, 32),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 0),
                2,
            )

            if a.no_show:
                if n % 30 == 0:
                    print(f"帧 {n:5d}  FPS {fps:5.1f}  推理 {infer_ms:5.1f}ms  检出 {len(r.boxes)}")
            else:
                cv2.imshow("screwdriver", vis)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print(f"共处理 {n} 帧")


if __name__ == "__main__":
    main()
