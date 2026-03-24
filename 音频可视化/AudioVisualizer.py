"""
音频可视化工具 —— GUI 图形窗口版
将 MP3/WAV 音频渲染为精美波形图
支持 5 种可视化风格 + 多种配色 + 批量导出
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
import struct
import math
import colorsys

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False

try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

WINDOW_W = 850
WINDOW_H = 720

# ── 配色方案 ──
COLOR_THEMES = {
    "霓虹蓝紫": {
        "bg": (15, 15, 35),
        "colors": [(0, 195, 255), (138, 43, 226), (255, 0, 128)],
    },
    "日落橙红": {
        "bg": (25, 15, 15),
        "colors": [(255, 200, 50), (255, 120, 30), (255, 40, 80)],
    },
    "森林绿": {
        "bg": (10, 25, 15),
        "colors": [(80, 255, 120), (30, 200, 100), (0, 150, 80)],
    },
    "海洋青蓝": {
        "bg": (10, 15, 30),
        "colors": [(0, 255, 200), (0, 150, 255), (50, 80, 200)],
    },
    "樱花粉": {
        "bg": (30, 15, 20),
        "colors": [(255, 150, 200), (255, 100, 150), (200, 50, 120)],
    },
    "纯白极简": {
        "bg": (255, 255, 255),
        "colors": [(50, 50, 50), (100, 100, 100), (150, 150, 150)],
    },
    "赛博黄绿": {
        "bg": (5, 5, 5),
        "colors": [(0, 255, 65), (180, 255, 0), (255, 255, 0)],
    },
    "深空灰橙": {
        "bg": (28, 28, 32),
        "colors": [(255, 165, 0), (255, 100, 50), (200, 60, 30)],
    },
}

# ── 可视化风格 ──
VIS_STYLES = [
    "经典波形",
    "柱状波形",
    "镜像波形",
    "渐变山脊",
    "频谱色带",
]


def format_duration(ms):
    s = int(ms / 1000)
    m = s // 60
    s = s % 60
    return f"{m}:{s:02d}"


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def get_gradient_color(colors, t):
    """从颜色列表中按 t(0~1) 插值"""
    if len(colors) == 1:
        return colors[0]
    t = max(0, min(1, t))
    seg = t * (len(colors) - 1)
    idx = int(seg)
    frac = seg - idx
    if idx >= len(colors) - 1:
        return colors[-1]
    return lerp_color(colors[idx], colors[idx + 1], frac)


def get_samples(audio):
    """从 pydub AudioSegment 提取样本数据（单声道、归一化）"""
    # 转单声道
    mono = audio.set_channels(1)
    raw = mono.raw_data
    sample_width = mono.sample_width

    if sample_width == 1:
        fmt = "<" + "b" * (len(raw))
        max_val = 128.0
    elif sample_width == 2:
        count = len(raw) // 2
        fmt = "<" + "h" * count
        max_val = 32768.0
    elif sample_width == 4:
        count = len(raw) // 4
        fmt = "<" + "i" * count
        max_val = 2147483648.0
    else:
        return []

    samples = struct.unpack(fmt, raw)
    return [s / max_val for s in samples]


def downsample(samples, target_count):
    """将样本降采样到指定数量（取每段最大绝对值）"""
    n = len(samples)
    if n == 0:
        return []
    chunk_size = max(n // target_count, 1)
    result = []
    for i in range(0, n, chunk_size):
        chunk = samples[i:i + chunk_size]
        if chunk:
            # 取绝对值最大的
            pos = max(chunk)
            neg = min(chunk)
            result.append((pos, neg))
        if len(result) >= target_count:
            break
    return result


# ── 渲染函数 ──

def render_classic(draw, data, x0, y0, w, h, colors, bg):
    """经典波形线"""
    mid_y = y0 + h // 2
    n = len(data)
    bar_w = w / n

    points_top = []
    points_bot = []
    for i, (pos, neg) in enumerate(data):
        x = x0 + i * bar_w + bar_w / 2
        yt = mid_y - pos * (h / 2) * 0.9
        yb = mid_y - neg * (h / 2) * 0.9
        points_top.append((x, yt))
        points_bot.append((x, yb))

    # 填充区域
    fill_points = points_top + list(reversed(points_bot))
    if len(fill_points) > 2:
        # 逐列填充渐变
        for i in range(n - 1):
            t = i / max(n - 1, 1)
            color = get_gradient_color(colors, t)
            fade = color + (60,)  # 半透明
            x1 = x0 + i * bar_w + bar_w / 2
            x2 = x0 + (i + 1) * bar_w + bar_w / 2
            yt1 = points_top[i][1]
            yb1 = points_bot[i][1]
            yt2 = points_top[i + 1][1]
            yb2 = points_bot[i + 1][1]
            draw.polygon([(x1, yt1), (x2, yt2), (x2, yb2), (x1, yb1)],
                         fill=fade)

    # 上下轮廓线
    for i in range(n - 1):
        t = i / max(n - 1, 1)
        color = get_gradient_color(colors, t)
        draw.line([points_top[i], points_top[i + 1]], fill=color, width=2)
        draw.line([points_bot[i], points_bot[i + 1]], fill=color, width=2)


def render_bars(draw, data, x0, y0, w, h, colors, bg):
    """柱状波形"""
    mid_y = y0 + h // 2
    n = len(data)
    bar_w = max(w / n, 1)
    gap = max(bar_w * 0.15, 1)

    for i, (pos, neg) in enumerate(data):
        t = i / max(n - 1, 1)
        color = get_gradient_color(colors, t)
        x = x0 + i * bar_w
        ht = abs(pos) * (h / 2) * 0.9
        hb = abs(neg) * (h / 2) * 0.9
        draw.rectangle(
            [x + gap / 2, mid_y - ht, x + bar_w - gap / 2, mid_y + hb],
            fill=color)


def render_mirror(draw, data, x0, y0, w, h, colors, bg):
    """镜像波形（上下对称）"""
    mid_y = y0 + h // 2
    n = len(data)
    bar_w = max(w / n, 1)
    gap = max(bar_w * 0.15, 1)

    for i, (pos, neg) in enumerate(data):
        t = i / max(n - 1, 1)
        color = get_gradient_color(colors, t)
        amp = max(abs(pos), abs(neg))
        x = x0 + i * bar_w
        ht = amp * (h / 2) * 0.9

        # 上半：实色
        draw.rectangle(
            [x + gap / 2, mid_y - ht, x + bar_w - gap / 2, mid_y],
            fill=color)
        # 下半：淡色镜像
        fade = tuple(int(c * 0.4) for c in color)
        draw.rectangle(
            [x + gap / 2, mid_y, x + bar_w - gap / 2, mid_y + ht],
            fill=fade)

    # 中线
    line_color = get_gradient_color(colors, 0.5) + (100,)
    draw.line([(x0, mid_y), (x0 + w, mid_y)], fill=line_color, width=1)


def render_ridge(draw, data, x0, y0, w, h, colors, bg):
    """渐变山脊（从底部生长）"""
    base_y = y0 + h
    n = len(data)
    bar_w = max(w / n, 1)

    for i, (pos, neg) in enumerate(data):
        t = i / max(n - 1, 1)
        amp = max(abs(pos), abs(neg))
        ht = amp * h * 0.9

        x = x0 + i * bar_w

        # 从底到顶渐变填充
        steps = max(int(ht), 1)
        for s in range(steps):
            st = s / max(steps, 1)
            color = get_gradient_color(colors, st)
            # 越往顶越亮
            bright = 0.3 + 0.7 * st
            c = tuple(int(v * bright) for v in color)
            y = base_y - s
            draw.line([(x, y), (x + bar_w - 1, y)], fill=c)


def render_spectrum(draw, data, x0, y0, w, h, colors, bg):
    """频谱色带（彩虹色映射振幅）"""
    mid_y = y0 + h // 2
    n = len(data)
    bar_w = max(w / n, 1)
    gap = max(bar_w * 0.1, 0.5)

    for i, (pos, neg) in enumerate(data):
        amp = max(abs(pos), abs(neg))
        ht = amp * (h / 2) * 0.9

        # 用振幅映射色相
        hue = amp * 0.8  # 0~0.8 范围
        r, g, b = colorsys.hsv_to_rgb(hue, 0.9, 0.95)
        color = (int(r * 255), int(g * 255), int(b * 255))

        x = x0 + i * bar_w
        draw.rectangle(
            [x + gap / 2, mid_y - ht,
             x + bar_w - gap / 2, mid_y + ht * 0.6],
            fill=color)


RENDERERS = {
    "经典波形": render_classic,
    "柱状波形": render_bars,
    "镜像波形": render_mirror,
    "渐变山脊": render_ridge,
    "频谱色带": render_spectrum,
}


def render_waveform(audio, style, theme_name, img_w, img_h,
                    show_info=True, title_text="", bar_count=0):
    """完整渲染一张波形图"""
    theme = COLOR_THEMES.get(theme_name, COLOR_THEMES["霓虹蓝紫"])
    bg = theme["bg"]
    colors = theme["colors"]

    img = Image.new("RGBA", (img_w, img_h), bg + (255,))
    draw = ImageDraw.Draw(img)

    # 边距
    pad_x = 40
    pad_top = 60 if show_info else 20
    pad_bot = 40 if show_info else 20

    wave_x = pad_x
    wave_y = pad_top
    wave_w = img_w - pad_x * 2
    wave_h = img_h - pad_top - pad_bot

    # 提取样本
    samples = get_samples(audio)
    if not samples:
        return img

    count = bar_count if bar_count > 0 else max(wave_w // 3, 100)
    data = downsample(samples, count)

    # 渲染波形
    renderer = RENDERERS.get(style, render_bars)
    renderer(draw, data, wave_x, wave_y, wave_w, wave_h, colors, bg)

    # 信息文字
    if show_info:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 16)
            font_sm = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 12)
        except Exception:
            font = ImageFont.load_default()
            font_sm = font

        # 标题
        fg = (255, 255, 255) if sum(bg) < 384 else (30, 30, 30)
        fg_dim = tuple(int(c * 0.5) for c in fg)
        if title_text:
            draw.text((pad_x, 16), title_text, fill=fg, font=font)

        # 时长
        dur = format_duration(len(audio))
        hz = f"{audio.frame_rate} Hz"
        ch = "立体声" if audio.channels == 2 else "单声道"
        info = f"{dur}  |  {hz}  |  {ch}"
        draw.text((pad_x, img_h - 30), info, fill=fg_dim, font=font_sm)

        # 时间轴标记
        total_sec = len(audio) / 1000
        marks = 5
        for i in range(marks + 1):
            t = i / marks
            x = wave_x + wave_w * t
            sec = total_sec * t
            m = int(sec) // 60
            s = int(sec) % 60
            label = f"{m}:{s:02d}"
            draw.text((x - 10, img_h - 30), label, fill=fg_dim, font=font_sm)
            # 刻度线
            draw.line([(x, wave_y + wave_h), (x, wave_y + wave_h + 4)],
                      fill=fg_dim, width=1)

    return img


class AudioVisualizerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("音频可视化工具")
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.resizable(False, False)
        self._files = []
        self._working = False
        self._preview_photo = None
        self._result_image = None

        if not HAS_PYDUB or not HAS_PIL:
            self._dep_error()
        else:
            self._build_ui()

    def _dep_error(self):
        f = tk.Frame(self)
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="需要安装依赖",
                 font=("Microsoft YaHei", 18, "bold"),
                 fg="#c62828").pack(pady=(0, 16))
        tk.Label(f, text="pip install pydub Pillow",
                 font=("Consolas", 14, "bold"), fg="#1a73e8").pack()
        tk.Label(f, text="\n还需要安装 FFmpeg（用于读取 MP3）",
                 font=("Microsoft YaHei", 10), fg="#888").pack()

    def _build_ui(self):
        # ── 标题 ──
        top = tk.Frame(self)
        top.pack(fill="x", padx=16, pady=(12, 4))
        tk.Label(top, text="音频可视化工具",
                 font=("Microsoft YaHei", 16, "bold")).pack(side="left")
        tk.Label(top, text="MP3/WAV → 精美波形图",
                 font=("Microsoft YaHei", 10), fg="#888").pack(side="left", padx=12)

        # ── 文件区 ──
        file_frame = tk.LabelFrame(self, text=" 音频文件 ",
                                    font=("Microsoft YaHei", 10, "bold"))
        file_frame.pack(fill="x", padx=16, pady=(0, 6))

        btn_row = tk.Frame(file_frame)
        btn_row.pack(fill="x", padx=8, pady=(6, 3))
        tk.Button(btn_row, text="添加音频",
                  font=("Microsoft YaHei", 9),
                  command=self._add_files).pack(side="left")
        tk.Button(btn_row, text="添加文件夹",
                  font=("Microsoft YaHei", 9),
                  command=self._add_folder).pack(side="left", padx=6)
        tk.Button(btn_row, text="清空",
                  font=("Microsoft YaHei", 9),
                  command=self._clear_files).pack(side="left")
        self._file_count = tk.Label(btn_row, text="0 个文件",
                                     font=("Microsoft YaHei", 9), fg="#888")
        self._file_count.pack(side="right")

        self._file_listbox = tk.Listbox(file_frame, height=3,
                                         font=("Consolas", 9))
        self._file_listbox.pack(fill="x", padx=8, pady=(0, 8))

        # ── 设置（两列）──
        settings = tk.Frame(self)
        settings.pack(fill="x", padx=16, pady=(0, 6))

        col1 = tk.LabelFrame(settings, text=" 可视化风格 ",
                              font=("Microsoft YaHei", 10, "bold"))
        col1.pack(side="left", fill="both", expand=True, padx=(0, 6))

        col2 = tk.LabelFrame(settings, text=" 输出设置 ",
                              font=("Microsoft YaHei", 10, "bold"))
        col2.pack(side="right", fill="both", expand=True, padx=(6, 0))

        # ─ 左列：风格 ─
        self._style_var = tk.StringVar(value="镜像波形")
        for s in VIS_STYLES:
            tk.Radiobutton(col1, text=s, variable=self._style_var, value=s,
                           font=("Microsoft YaHei", 10),
                           ).pack(anchor="w", padx=8, pady=1)

        # 配色
        r_theme = tk.Frame(col1)
        r_theme.pack(fill="x", padx=8, pady=(6, 8))
        tk.Label(r_theme, text="配色：",
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self._theme_var = tk.StringVar(value="霓虹蓝紫")
        ttk.Combobox(r_theme, values=list(COLOR_THEMES.keys()),
                     textvariable=self._theme_var, width=12,
                     font=("Microsoft YaHei", 9)).pack(side="left", padx=4)

        # ─ 右列：输出 ─

        # 分辨率
        r_res = tk.Frame(col2)
        r_res.pack(fill="x", padx=8, pady=(8, 3))
        tk.Label(r_res, text="图片宽度：",
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self._width_var = tk.IntVar(value=1920)
        ttk.Combobox(r_res, values=["800", "1200", "1920", "2560", "3840"],
                     textvariable=self._width_var, width=6).pack(side="left", padx=4)
        tk.Label(r_res, text="高度：",
                 font=("Microsoft YaHei", 9)).pack(side="left", padx=(8, 0))
        self._height_var = tk.IntVar(value=600)
        ttk.Combobox(r_res, values=["400", "500", "600", "800", "1080"],
                     textvariable=self._height_var, width=6).pack(side="left", padx=4)

        # 柱子数量
        r_bars = tk.Frame(col2)
        r_bars.pack(fill="x", padx=8, pady=3)
        tk.Label(r_bars, text="波形精度：",
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self._bars_var = tk.IntVar(value=0)
        ttk.Combobox(r_bars, values=["自动", "100", "200", "400", "600", "800"],
                     width=8, font=("Microsoft YaHei", 9)
                     ).pack(side="left", padx=4)
        # 因为有"自动"选项，用单独变量
        self._bars_combo = r_bars.winfo_children()[-1]
        self._bars_combo.set("自动")

        # 显示信息
        r_opt = tk.Frame(col2)
        r_opt.pack(fill="x", padx=8, pady=3)
        self._show_info_var = tk.BooleanVar(value=True)
        tk.Checkbutton(r_opt, text="显示时长/采样率信息",
                       variable=self._show_info_var,
                       font=("Microsoft YaHei", 9)).pack(side="left")

        # 文件名作为标题
        self._show_title_var = tk.BooleanVar(value=True)
        tk.Checkbutton(r_opt, text="显示文件名",
                       variable=self._show_title_var,
                       font=("Microsoft YaHei", 9)).pack(side="left", padx=(8, 0))

        # 预设快捷
        r_preset = tk.Frame(col2)
        r_preset.pack(fill="x", padx=8, pady=(6, 8))
        tk.Label(r_preset, text="预设：",
                 font=("Microsoft YaHei", 8), fg="#888").pack(side="left")
        presets = [
            ("手机壁纸", 1080, 1920), ("电脑壁纸", 1920, 1080),
            ("社交封面", 1200, 630), ("正方形", 1080, 1080),
        ]
        for name, w, h in presets:
            tk.Button(r_preset, text=name, font=("Microsoft YaHei", 8),
                      command=lambda ww=w, hh=h: self._set_size(ww, hh)
                      ).pack(side="left", padx=2)

        # ── 预览区 ──
        prev_frame = tk.Frame(self, bg="#1a1a2e", relief="sunken", bd=1)
        prev_frame.pack(fill="both", expand=True, padx=16, pady=(0, 6))
        self._preview_label = tk.Label(prev_frame, bg="#1a1a2e",
                                        text="添加音频后点「预览」或「生成」",
                                        font=("Microsoft YaHei", 10), fg="#555")
        self._preview_label.pack(fill="both", expand=True, padx=4, pady=4)

        # ── 底部按钮 ──
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill="x", padx=16, pady=(0, 4))

        tk.Button(btn_frame, text="预览第一个",
                  font=("Microsoft YaHei", 11, "bold"),
                  command=self._preview).pack(side="left", padx=(0, 8))
        tk.Button(btn_frame, text="单个保存",
                  font=("Microsoft YaHei", 11),
                  command=self._save_single).pack(side="left", padx=(0, 8))
        tk.Button(btn_frame, text="批量导出全部",
                  font=("Microsoft YaHei", 11, "bold"),
                  bg="#1a73e8", fg="white",
                  command=self._batch_export).pack(side="left", padx=(0, 8))

        self._progress = ttk.Progressbar(btn_frame, length=180,
                                          mode="determinate")
        self._progress.pack(side="left", padx=(8, 8))
        self._status = tk.Label(btn_frame, text="就绪",
                                 font=("Microsoft YaHei", 10), fg="#666")
        self._status.pack(side="left")

        # ── 日志 ──
        self._log = scrolledtext.ScrolledText(
            self, font=("Consolas", 9), height=3, state="disabled",
            bg="#fafafa")
        self._log.pack(fill="x", padx=16, pady=(0, 10))

    # ── 文件管理 ──

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="选择音频文件",
            filetypes=[("音频文件", "*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.wma"),
                       ("所有文件", "*.*")])
        for p in paths:
            if p not in self._files:
                self._files.append(p)
                self._file_listbox.insert("end", os.path.basename(p))
        self._file_count.configure(text=f"{len(self._files)} 个文件")

    def _add_folder(self):
        folder = filedialog.askdirectory(title="选择文件夹")
        if not folder:
            return
        exts = (".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma")
        for name in os.listdir(folder):
            if name.lower().endswith(exts):
                p = os.path.join(folder, name)
                if p not in self._files:
                    self._files.append(p)
                    self._file_listbox.insert("end", name)
        self._file_count.configure(text=f"{len(self._files)} 个文件")

    def _clear_files(self):
        self._files.clear()
        self._file_listbox.delete(0, "end")
        self._file_count.configure(text="0 个文件")

    def _set_size(self, w, h):
        self._width_var.set(w)
        self._height_var.set(h)

    def _log_msg(self, msg):
        self._log.configure(state="normal")
        self._log.insert("end", msg + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _get_bar_count(self):
        try:
            val = self._bars_combo.get()
            if val == "自动":
                return 0
            return int(val)
        except (ValueError, AttributeError):
            return 0

    # ── 渲染 ──

    def _render_one(self, filepath):
        audio = AudioSegment.from_file(filepath)
        style = self._style_var.get()
        theme = self._theme_var.get()
        img_w = self._width_var.get()
        img_h = self._height_var.get()
        show_info = self._show_info_var.get()
        show_title = self._show_title_var.get()
        bar_count = self._get_bar_count()

        title = os.path.splitext(os.path.basename(filepath))[0] if show_title else ""

        return render_waveform(audio, style, theme, img_w, img_h,
                               show_info=show_info, title_text=title,
                               bar_count=bar_count)

    # ── 预览 ──

    def _preview(self):
        if not self._files:
            messagebox.showwarning("提示", "请先添加音频文件")
            return

        self._status.configure(text="正在渲染预览...", fg="#1a73e8")
        self.update()

        def task():
            try:
                img = self._render_one(self._files[0])
                self._result_image = img
                self.after(0, self._show_preview, img)
                self.after(0, self._log_msg,
                           f"预览: {os.path.basename(self._files[0])}  "
                           f"{img.width}x{img.height}")
                self.after(0, lambda: self._status.configure(
                    text="预览完成", fg="#2e7d32"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("错误", str(e)))
                self.after(0, lambda: self._status.configure(
                    text="渲染失败", fg="#c62828"))

        threading.Thread(target=task, daemon=True).start()

    def _show_preview(self, img):
        pw = WINDOW_W - 40
        ph = 170
        ratio = min(pw / img.width, ph / img.height, 1.0)
        dw = max(int(img.width * ratio), 1)
        dh = max(int(img.height * ratio), 1)
        disp = img.resize((dw, dh), Image.LANCZOS)
        self._preview_photo = ImageTk.PhotoImage(disp)
        self._preview_label.configure(image=self._preview_photo, text="")

    # ── 单个保存 ──

    def _save_single(self):
        if not self._files:
            messagebox.showwarning("提示", "请先添加音频文件")
            return

        path = filedialog.asksaveasfilename(
            title="保存波形图",
            initialfile="waveform.png",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if not path:
            return

        self._status.configure(text="正在渲染...", fg="#1a73e8")
        self.update()

        def task():
            try:
                img = self._render_one(self._files[0])
                if path.lower().endswith(".jpg"):
                    img = img.convert("RGB")
                    img.save(path, quality=95)
                else:
                    img.save(path)
                self.after(0, self._show_preview, img)
                self.after(0, self._log_msg,
                           f"已保存: {path}  ({img.width}x{img.height})")
                self.after(0, lambda: self._status.configure(
                    text="保存完成!", fg="#2e7d32"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("错误", str(e)))

        threading.Thread(target=task, daemon=True).start()

    # ── 批量导出 ──

    def _batch_export(self):
        if not self._files:
            messagebox.showwarning("提示", "请先添加音频文件")
            return
        if self._working:
            return

        out_dir = filedialog.askdirectory(title="选择保存文件夹")
        if not out_dir:
            return

        self._working = True
        self._progress["value"] = 0
        self._progress["maximum"] = len(self._files)

        def task():
            for i, fp in enumerate(self._files):
                name = os.path.splitext(os.path.basename(fp))[0]
                self.after(0, lambda n=name, idx=i:
                           self._status.configure(
                               text=f"[{idx + 1}/{len(self._files)}] {n}",
                               fg="#1a73e8"))
                try:
                    img = self._render_one(fp)
                    out_path = os.path.join(out_dir, f"{name}_waveform.png")
                    img.save(out_path)
                    self.after(0, self._log_msg,
                               f"  [{i + 1}] {name}_waveform.png  "
                               f"({img.width}x{img.height})")
                except Exception as e:
                    self.after(0, self._log_msg,
                               f"  [{i + 1}] {name} 失败: {e}")

                self.after(0, lambda v=i + 1:
                           self._progress.configure(value=v))

            self.after(0, self._log_msg,
                       f"\n批量导出完成: {len(self._files)} 个文件 → {out_dir}")
            self.after(0, lambda: self._status.configure(
                text=f"全部完成!", fg="#2e7d32"))
            self.after(0, lambda: os.startfile(out_dir))
            self._working = False

        threading.Thread(target=task, daemon=True).start()


if __name__ == "__main__":
    app = AudioVisualizerApp()
    app.mainloop()
