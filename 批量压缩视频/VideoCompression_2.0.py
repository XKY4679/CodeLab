"""
批量视频压缩工具 2.0 —— GUI 图形窗口版
支持质量预设 / 指定目标文件大小（MB）
自动检测 NVIDIA GPU 加速，无则回退 CPU
tkinter 界面，与答题系统 3.0 / 歌词工具 2.0 风格统一
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import subprocess
import threading
import json
import time

# ── 配置 ────────────────────────────────────────────
WINDOW_WIDTH = 780
WINDOW_HEIGHT = 620
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".wmv", ".flv", ".webm"}

# 质量预设 —— CRF 值（越小质量越高、文件越大）
QUALITY_PRESETS = {
    "高质量（体积较大）": 20,
    "均衡（推荐）": 26,
    "小体积（画质有损）": 32,
}

# ── ffmpeg / ffprobe 工具函数 ────────────────────────


def find_ffmpeg():
    """检查 ffmpeg 是否可用"""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return True
    except FileNotFoundError:
        return False


def has_nvenc():
    """检测是否支持 NVIDIA 硬件编码"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return "h264_nvenc" in result.stdout
    except Exception:
        return False


def get_video_duration(path):
    """用 ffprobe 获取视频时长（秒）"""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", path,
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except Exception:
        return None


def format_size(size_bytes):
    """字节 → 人类可读"""
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def scan_videos(folder):
    """扫描文件夹中的视频文件（不递归子目录）"""
    videos = []
    for fname in sorted(os.listdir(folder)):
        full = os.path.join(folder, fname)
        if not os.path.isfile(full):
            continue
        ext = os.path.splitext(fname)[1].lower()
        if ext in VIDEO_EXTS:
            videos.append(full)
    return videos


def build_ffmpeg_cmd_crf(input_path, output_path, crf, use_gpu):
    """构建基于 CRF 质量的 ffmpeg 命令"""
    if use_gpu:
        # NVENC 用 -cq 代替 -crf
        cmd = [
            "ffmpeg", "-y", "-hwaccel", "cuda",
            "-i", input_path,
            "-c:v", "h264_nvenc", "-preset", "p4",
            "-cq", str(crf), "-profile:v", "main",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            output_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-c:v", "libx264", "-preset", "medium",
            "-crf", str(crf), "-profile:v", "main",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            output_path,
        ]
    return cmd


def build_ffmpeg_cmd_target(input_path, output_path, target_mb, duration, use_gpu):
    """构建基于目标文件大小的 ffmpeg 命令（两遍编码中的单遍近似）"""
    target_bits = target_mb * 1024 * 1024 * 8
    audio_bits = 128 * 1000 * duration  # 128kbps 音频
    video_bitrate = max(int((target_bits - audio_bits) / duration), 100000)

    if use_gpu:
        cmd = [
            "ffmpeg", "-y", "-hwaccel", "cuda",
            "-i", input_path,
            "-c:v", "h264_nvenc", "-preset", "p4",
            "-b:v", str(video_bitrate), "-maxrate", str(int(video_bitrate * 1.5)),
            "-bufsize", str(video_bitrate * 2),
            "-profile:v", "main",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            output_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-c:v", "libx264", "-preset", "medium",
            "-b:v", str(video_bitrate), "-maxrate", str(int(video_bitrate * 1.5)),
            "-bufsize", str(video_bitrate * 2),
            "-profile:v", "main",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            output_path,
        ]
    return cmd


# ── GUI 主程序 ──────────────────────────────────────


class VideoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("批量视频压缩工具 2.0")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)

        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self._use_gpu = has_nvenc()
        self._ffmpeg_ok = find_ffmpeg()

        if not self._ffmpeg_ok:
            self._show_no_ffmpeg()
        else:
            self._show_start_page()

    def _clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    # ── ffmpeg 缺失提示 ─────────────────────────────

    def _show_no_ffmpeg(self):
        self._clear()
        frame = tk.Frame(self.container)
        frame.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(frame, text="未检测到 ffmpeg", font=("Microsoft YaHei", 20, "bold"), fg="#c62828").pack(pady=(0, 12))
        tk.Label(frame, text="本程序依赖 ffmpeg 进行视频压缩，请先安装：", font=("Microsoft YaHei", 11)).pack()
        tk.Label(frame, text="https://ffmpeg.org/download.html", font=("Consolas", 11), fg="#1a73e8").pack(pady=8)
        tk.Label(frame, text="安装后确保 ffmpeg 已加入系统 PATH，然后重新打开本程序。",
                 font=("Microsoft YaHei", 10), fg="#666").pack(pady=(5, 0))

    # ── 开始页面 ─────────────────────────────────────

    def _show_start_page(self):
        self._clear()
        frame = tk.Frame(self.container)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame, text="批量视频压缩工具 2.0", font=("Microsoft YaHei", 24, "bold")).pack(pady=(0, 6))

        gpu_text = "已检测到 NVIDIA GPU 加速" if self._use_gpu else "未检测到 GPU，将使用 CPU 编码"
        gpu_color = "#2e7d32" if self._use_gpu else "#e65100"
        tk.Label(frame, text=gpu_text, font=("Microsoft YaHei", 10), fg=gpu_color).pack(pady=(0, 30))

        tk.Button(
            frame, text="选择视频文件夹", font=("Microsoft YaHei", 13),
            width=20, height=2, command=self._on_select_folder,
        ).pack(pady=6)

        tk.Label(frame, text="支持格式：MP4 / MOV / AVI / MKV / M4V / WMV / FLV / WebM",
                 font=("Microsoft YaHei", 9), fg="#999").pack(pady=(8, 0))
        tk.Label(frame, text="压缩后的文件会保存到单独的输出文件夹，不会覆盖原文件",
                 font=("Microsoft YaHei", 9), fg="#999").pack(pady=(4, 0))

    def _on_select_folder(self):
        folder = filedialog.askdirectory(title="选择包含视频的文件夹")
        if not folder:
            return
        videos = scan_videos(folder)
        if not videos:
            messagebox.showwarning("提示", "所选文件夹中没有找到视频文件。")
            return
        self._input_folder = folder
        self._video_list = videos
        self._show_settings_page()

    # ── 设置页面 ─────────────────────────────────────

    def _show_settings_page(self):
        self._clear()
        num = len(self._video_list)

        # 顶部
        top = tk.Frame(self.container)
        top.pack(fill="x", padx=20, pady=(15, 5))
        tk.Button(top, text="← 返回", font=("Microsoft YaHei", 10), command=self._show_start_page).pack(side="left")
        tk.Label(top, text="压缩设置", font=("Microsoft YaHei", 14, "bold")).pack(side="left", padx=15)

        body = tk.Frame(self.container)
        body.pack(fill="both", expand=True, padx=25, pady=10)

        # 文件夹信息
        tk.Label(body, text=f"已选择文件夹：{self._input_folder}", font=("Microsoft YaHei", 10), fg="#555").pack(anchor="w")
        tk.Label(body, text=f"共发现 {num} 个视频文件", font=("Microsoft YaHei", 11, "bold")).pack(anchor="w", pady=(2, 15))

        # 文件列表预览
        list_frame = tk.Frame(body)
        list_frame.pack(fill="x")
        tk.Label(list_frame, text="文件列表：", font=("Microsoft YaHei", 10)).pack(anchor="w")
        listbox = tk.Listbox(list_frame, height=min(6, num), font=("Microsoft YaHei", 9))
        for v in self._video_list:
            size = os.path.getsize(v)
            listbox.insert("end", f"  {os.path.basename(v)}    ({format_size(size)})")
        listbox.pack(fill="x", pady=(2, 10))

        # 压缩模式选择
        tk.Label(body, text="压缩模式：", font=("Microsoft YaHei", 11, "bold")).pack(anchor="w", pady=(5, 5))

        self._mode_var = tk.StringVar(value="preset")

        # 模式1：质量预设
        preset_frame = tk.Frame(body)
        preset_frame.pack(fill="x", pady=2)
        tk.Radiobutton(
            preset_frame, text="质量预设", variable=self._mode_var, value="preset",
            font=("Microsoft YaHei", 10), command=self._on_mode_change,
        ).pack(side="left")

        self._preset_var = tk.StringVar(value="均衡（推荐）")
        self._preset_menu = ttk.Combobox(
            preset_frame, textvariable=self._preset_var,
            values=list(QUALITY_PRESETS.keys()), state="readonly", width=22,
        )
        self._preset_menu.pack(side="left", padx=10)

        # 模式2：指定目标大小
        target_frame = tk.Frame(body)
        target_frame.pack(fill="x", pady=2)
        tk.Radiobutton(
            target_frame, text="指定目标大小", variable=self._mode_var, value="target",
            font=("Microsoft YaHei", 10), command=self._on_mode_change,
        ).pack(side="left")

        self._target_var = tk.StringVar(value="100")
        self._target_entry = tk.Entry(target_frame, textvariable=self._target_var, width=8, font=("Microsoft YaHei", 10))
        self._target_entry.pack(side="left", padx=10)
        self._target_entry.config(state="disabled")
        tk.Label(target_frame, text="MB（每个文件压缩到约这个大小）", font=("Microsoft YaHei", 9), fg="#888").pack(side="left")

        # 开始按钮
        tk.Button(
            body, text="开始压缩", font=("Microsoft YaHei", 13, "bold"),
            width=16, height=2, command=self._start_compress,
        ).pack(pady=(20, 0))

    def _on_mode_change(self):
        mode = self._mode_var.get()
        if mode == "preset":
            self._preset_menu.config(state="readonly")
            self._target_entry.config(state="disabled")
        else:
            self._preset_menu.config(state="disabled")
            self._target_entry.config(state="normal")

    # ── 压缩执行页面 ─────────────────────────────────

    def _start_compress(self):
        mode = self._mode_var.get()

        if mode == "target":
            try:
                target_mb = float(self._target_var.get())
                if target_mb <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("提示", "请输入一个有效的目标大小（正数）。")
                return
            self._target_mb = target_mb
            self._crf = None
        else:
            preset_name = self._preset_var.get()
            self._crf = QUALITY_PRESETS[preset_name]
            self._target_mb = None

        # 创建输出文件夹
        self._output_folder = os.path.join(self._input_folder, "压缩输出")
        os.makedirs(self._output_folder, exist_ok=True)

        self._show_progress_page()

        # 在后台线程执行压缩
        self._compress_thread = threading.Thread(target=self._compress_worker, daemon=True)
        self._compress_thread.start()

    def _show_progress_page(self):
        self._clear()

        top = tk.Frame(self.container)
        top.pack(fill="x", padx=20, pady=(15, 5))
        tk.Label(top, text="正在压缩...", font=("Microsoft YaHei", 14, "bold")).pack(side="left")

        encoder = "NVIDIA GPU (h264_nvenc)" if self._use_gpu else "CPU (libx264)"
        tk.Label(top, text=f"编码器：{encoder}", font=("Microsoft YaHei", 9), fg="#888").pack(side="right")

        body = tk.Frame(self.container)
        body.pack(fill="both", expand=True, padx=20, pady=10)

        # 总进度
        self._progress_label = tk.Label(body, text="准备中...", font=("Microsoft YaHei", 11))
        self._progress_label.pack(anchor="w", pady=(0, 3))
        self._progress_bar = ttk.Progressbar(body, length=WINDOW_WIDTH - 50, maximum=len(self._video_list))
        self._progress_bar.pack(fill="x", pady=(0, 10))

        # 当前文件
        self._current_label = tk.Label(body, text="", font=("Microsoft YaHei", 10), fg="#555")
        self._current_label.pack(anchor="w", pady=(0, 8))

        # 文件状态列表
        columns = ("name", "original", "compressed", "ratio", "status")
        self._tree = ttk.Treeview(body, columns=columns, show="headings", height=14)
        self._tree.heading("name", text="文件名")
        self._tree.heading("original", text="原始大小")
        self._tree.heading("compressed", text="压缩后")
        self._tree.heading("ratio", text="节省")
        self._tree.heading("status", text="状态")
        self._tree.column("name", width=260)
        self._tree.column("original", width=100, anchor="center")
        self._tree.column("compressed", width=100, anchor="center")
        self._tree.column("ratio", width=80, anchor="center")
        self._tree.column("status", width=100, anchor="center")

        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 预填充等待行
        self._tree_ids = {}
        for v in self._video_list:
            name = os.path.basename(v)
            orig_size = format_size(os.path.getsize(v))
            iid = self._tree.insert("", "end", values=(name, orig_size, "—", "—", "等待"))
            self._tree_ids[v] = iid

    def _update_tree_row(self, video_path, compressed_size_str, ratio_str, status):
        """线程安全地更新表格行"""
        iid = self._tree_ids.get(video_path)
        if iid:
            current = self._tree.item(iid, "values")
            self._tree.item(iid, values=(current[0], current[1], compressed_size_str, ratio_str, status))

    def _compress_worker(self):
        """后台线程：逐个压缩视频"""
        results = []  # (name, orig_size, new_size, success, error)
        total = len(self._video_list)

        for idx, video_path in enumerate(self._video_list):
            name = os.path.basename(video_path)
            stem, ext = os.path.splitext(name)
            output_path = os.path.join(self._output_folder, f"{stem}_压缩{ext}")
            orig_size = os.path.getsize(video_path)

            # 更新 UI
            self.after(0, lambda i=idx, n=name: self._on_file_start(i, n, total))

            # 更新状态为"压缩中"
            self.after(0, lambda vp=video_path: self._update_tree_row(vp, "...", "...", "压缩中"))

            try:
                if self._target_mb is not None:
                    # 目标大小模式 → 需要读时长
                    duration = get_video_duration(video_path)
                    if not duration or duration <= 0:
                        raise RuntimeError("无法读取视频时长")

                    # 如果原文件已经比目标小，跳过
                    orig_mb = orig_size / (1024 * 1024)
                    if orig_mb <= self._target_mb:
                        # 直接复制，不压缩
                        import shutil
                        shutil.copy2(video_path, output_path)
                        new_size = orig_size
                        self.after(0, lambda vp=video_path, ns=new_size: self._update_tree_row(
                            vp, format_size(ns), "已跳过", "已小于目标"))
                        results.append((name, orig_size, new_size, True, None))
                        continue

                    cmd = build_ffmpeg_cmd_target(video_path, output_path, self._target_mb, duration, self._use_gpu)
                else:
                    cmd = build_ffmpeg_cmd_crf(video_path, output_path, self._crf, self._use_gpu)

                subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    check=True,
                )

                new_size = os.path.getsize(output_path)
                saved = (1 - new_size / orig_size) * 100 if orig_size > 0 else 0
                ratio_str = f"-{saved:.1f}%"

                self.after(0, lambda vp=video_path, ns=new_size, rs=ratio_str:
                           self._update_tree_row(vp, format_size(ns), rs, "完成"))
                results.append((name, orig_size, new_size, True, None))

            except Exception as e:
                # 清理失败的输出文件
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except OSError:
                        pass
                self.after(0, lambda vp=video_path: self._update_tree_row(vp, "—", "—", "失败"))
                results.append((name, orig_size, 0, False, str(e)))

        # 全部完成
        self.after(0, lambda: self._on_all_done(results))

    def _on_file_start(self, idx, name, total):
        self._progress_label.config(text=f"进度：{idx + 1} / {total}")
        self._progress_bar["value"] = idx
        self._current_label.config(text=f"正在处理：{name}")

    def _on_all_done(self, results):
        self._progress_bar["value"] = self._progress_bar["maximum"]
        self._progress_label.config(text=f"全部完成 ({len(results)} 个文件)")
        self._current_label.config(text="")

        # 计算总体统计
        total_orig = sum(r[1] for r in results)
        total_new = sum(r[2] for r in results if r[3])
        success_count = sum(1 for r in results if r[3])
        fail_count = sum(1 for r in results if not r[3])

        self._show_summary_bar(total_orig, total_new, success_count, fail_count)

    def _show_summary_bar(self, total_orig, total_new, success, fail):
        """在底部显示总结信息和按钮"""
        summary = tk.Frame(self.container, bg="#f0f0f0", relief="groove", bd=1)
        summary.pack(fill="x", padx=15, pady=(0, 12))

        left = tk.Frame(summary, bg="#f0f0f0")
        left.pack(side="left", padx=15, pady=10)

        saved = (1 - total_new / total_orig) * 100 if total_orig > 0 else 0
        tk.Label(left, text=f"原始总大小：{format_size(total_orig)}  →  压缩后：{format_size(total_new)}  |  节省 {saved:.1f}%",
                 font=("Microsoft YaHei", 10, "bold"), bg="#f0f0f0").pack(anchor="w")

        status_text = f"成功 {success} 个"
        if fail:
            status_text += f"，失败 {fail} 个"
        tk.Label(left, text=status_text, font=("Microsoft YaHei", 9), fg="#666", bg="#f0f0f0").pack(anchor="w")

        right = tk.Frame(summary, bg="#f0f0f0")
        right.pack(side="right", padx=15, pady=10)

        tk.Button(right, text="打开输出文件夹", font=("Microsoft YaHei", 10),
                  command=lambda: os.startfile(self._output_folder)).pack(side="left", padx=4)
        tk.Button(right, text="返回首页", font=("Microsoft YaHei", 10),
                  command=self._show_start_page).pack(side="left", padx=4)


# ── 入口 ────────────────────────────────────────────

if __name__ == "__main__":
    app = VideoApp()
    app.mainloop()
