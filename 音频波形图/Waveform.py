"""
音频波形图生成器 —— GUI 图形窗口版
将音频文件生成好看的波形可视化图片
支持多种配色方案、镜像模式、渐变条形
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import os
import struct
import math
import array

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

WINDOW_WIDTH = 840
WINDOW_HEIGHT = 680

# ── 配色方案 ──
# (名称, 顶部色, 底部色, 背景色, 是否彩虹)

COLOR_PRESETS = [
    ("海洋蓝",   (0, 180, 255),   (0, 60, 140),    (15, 18, 30),   False),
    ("霓虹紫",   (200, 80, 255),  (80, 20, 180),   (18, 12, 30),   False),
    ("日落橙",   (255, 180, 50),  (255, 50, 80),   (25, 15, 15),   False),
    ("翡翠绿",   (0, 230, 160),   (0, 100, 80),    (12, 22, 18),   False),
    ("樱花粉",   (255, 140, 180), (200, 50, 110),  (28, 15, 20),   False),
    ("极光",     (0, 255, 200),   (100, 0, 255),   (10, 10, 20),   True),
    ("纯白",     (255, 255, 255), (160, 160, 180),  (20, 20, 25),  False),
    ("烈焰红",   (255, 80, 50),   (180, 0, 40),    (25, 10, 10),   False),
    ("金色",     (255, 215, 0),   (180, 130, 0),   (22, 18, 8),    False),
]


def _lerp_color(c1, c2, t):
    """线性插值两个颜色"""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _hsv_to_rgb(h, s, v):
    """HSV(0-360,0-1,0-1) → RGB(0-255)"""
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h / 360, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


def load_audio_samples(audio_path):
    """加载音频文件，返回 (samples_list, sample_rate, duration_sec, channels)"""
    audio = AudioSegment.from_file(audio_path)
    samples = audio.get_array_of_samples()

    # 立体声转单声道
    if audio.channels == 2:
        mono = []
        for i in range(0, len(samples), 2):
            mono.append((samples[i] + samples[i + 1]) // 2)
        samples = mono

    return samples, audio.frame_rate, len(audio) / 1000.0


def generate_waveform(samples, duration,
                      width=1600, height=500,
                      bar_width=3, gap=1, mirror=True,
                      color_preset_idx=0, bg_color=None,
                      rounded=True, glow=True, center_line=True,
                      show_time=True):
    """
    生成波形图，返回 PIL Image
    """
    preset = COLOR_PRESETS[color_preset_idx]
    preset_name, color_top, color_bot, default_bg, is_rainbow = preset

    if bg_color is None:
        bg_color = default_bg

    # 创建画布
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # 计算条形数量
    step = bar_width + gap
    num_bars = (width - 10) // step  # 左右各留5px
    x_offset = (width - num_bars * step) // 2

    if num_bars < 2 or len(samples) < num_bars:
        return img

    # 分段取峰值
    chunk_size = len(samples) // num_bars
    peaks = []
    for i in range(num_bars):
        start = i * chunk_size
        end = min(start + chunk_size, len(samples))
        chunk = samples[start:end]
        if chunk:
            peak = max(abs(min(chunk)), abs(max(chunk)))
        else:
            peak = 0
        peaks.append(peak)

    # 归一化
    max_peak = max(peaks) if max(peaks) > 0 else 1
    normalized = [p / max_peak for p in peaks]

    # 轻微平滑（相邻 3 个取平均）
    smoothed = []
    for i in range(len(normalized)):
        start = max(0, i - 1)
        end = min(len(normalized), i + 2)
        avg = sum(normalized[start:end]) / (end - start)
        smoothed.append(avg)
    normalized = smoothed

    # 绘图参数
    if mirror:
        center_y = height // 2
        if show_time:
            center_y = (height - 30) // 2
        max_bar_h = center_y - 8
    else:
        bottom_y = height - 10
        if show_time:
            bottom_y = height - 35
        max_bar_h = bottom_y - 10

    radius = max(bar_width // 2, 1) if rounded else 0

    # ── 发光层（可选）──
    if glow:
        glow_img = Image.new("RGB", (width, height), (0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_img)

    # ── 逐条绘制 ──
    for i, amp in enumerate(normalized):
        x = x_offset + i * step
        bar_h = max(int(amp * max_bar_h), 1)

        # 计算颜色
        if is_rainbow:
            # 彩虹：按水平位置变色
            hue = (i / num_bars) * 300  # 0-300° 避免回到红
            t = min(amp * 1.2, 1.0)
            color = _hsv_to_rgb(hue, 0.8, 0.6 + 0.4 * t)
            color_dim = _hsv_to_rgb(hue, 0.6, 0.4 + 0.2 * t)
        else:
            # 按振幅插值颜色
            t = min(amp * 1.3, 1.0)
            color = _lerp_color(color_bot, color_top, t)
            color_dim = _lerp_color(
                tuple(c * 2 // 5 for c in color_bot),
                tuple(c * 3 // 4 for c in color_top),
                t)

        if mirror:
            # 上半部分
            y1 = center_y - bar_h
            y2 = center_y
            draw.rounded_rectangle([x, y1, x + bar_width, y2],
                                   radius=radius, fill=color)
            # 下半部分（稍暗）
            y3 = center_y
            y4 = center_y + bar_h
            draw.rounded_rectangle([x, y3, x + bar_width, y4],
                                   radius=radius, fill=color_dim)

            # 发光
            if glow:
                glow_draw.rounded_rectangle(
                    [x - 1, y1 - 1, x + bar_width + 1, y2 + 1],
                    radius=radius + 1, fill=color)
                glow_draw.rounded_rectangle(
                    [x - 1, y3 - 1, x + bar_width + 1, y4 + 1],
                    radius=radius + 1, fill=color_dim)
        else:
            y1 = bottom_y - bar_h
            y2 = bottom_y
            draw.rounded_rectangle([x, y1, x + bar_width, y2],
                                   radius=radius, fill=color)
            if glow:
                glow_draw.rounded_rectangle(
                    [x - 1, y1 - 1, x + bar_width + 1, y2 + 1],
                    radius=radius + 1, fill=color)

    # ── 叠加发光效果 ──
    if glow:
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=4))
        from PIL import ImageChops
        img = ImageChops.add(img, glow_img, scale=2, offset=0)
        # 重新获取 draw
        draw = ImageDraw.Draw(img)

    # ── 中线 ──
    if center_line and mirror:
        line_color = tuple(min(c + 30, 255) for c in bg_color)
        draw.line([(x_offset, center_y), (x_offset + num_bars * step, center_y)],
                  fill=line_color, width=1)

    # ── 时间标尺 ──
    if show_time and duration > 0:
        try:
            font_path = os.path.join(
                os.environ.get("WINDIR", "C:\\Windows"),
                "Fonts", "consola.ttf")
            time_font = ImageFont.truetype(font_path, 12)
        except Exception:
            time_font = ImageFont.load_default()

        time_y = height - 22
        text_color = tuple(min(c + 60, 255) for c in bg_color)

        # 根据时长决定间隔
        if duration < 30:
            interval = 5
        elif duration < 120:
            interval = 15
        elif duration < 300:
            interval = 30
        else:
            interval = 60

        t = 0
        while t <= duration:
            x_pos = x_offset + int((t / duration) * (num_bars * step))
            mm = int(t) // 60
            ss = int(t) % 60
            label = f"{mm}:{ss:02d}"
            draw.text((x_pos, time_y), label, fill=text_color, font=time_font)

            # 刻度线
            tick_y = time_y - 4
            draw.line([(x_pos, tick_y), (x_pos, tick_y + 3)],
                      fill=text_color, width=1)
            t += interval

    return img


# ══════════════════════════════════════════════════════════
#  GUI
# ══════════════════════════════════════════════════════════

class WaveformApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("音频波形图生成器")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self._audio_path = None
        self._samples = None
        self._duration = 0
        self._preview_photo = None

        missing = []
        if not HAS_PYDUB:
            missing.append("pydub")
        if not HAS_PIL:
            missing.append("Pillow")

        if missing:
            self._dep_error(missing)
        else:
            self._build_ui()

    def _dep_error(self, missing):
        f = tk.Frame(self)
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="缺少依赖库", font=("Microsoft YaHei", 20, "bold"),
                 fg="#c62828").pack(pady=(0, 12))
        libs = " ".join(missing)
        tk.Label(f, text=f"pip install {libs}",
                 font=("Consolas", 14, "bold"), fg="#1a73e8").pack(pady=6)
        tk.Label(f, text="另外需要系统安装 ffmpeg",
                 font=("Microsoft YaHei", 10), fg="#888").pack(pady=6)

    def _build_ui(self):
        # ── 顶部：文件选择 ──
        top = tk.Frame(self)
        top.pack(fill="x", padx=16, pady=(16, 8))

        tk.Label(top, text="音频波形图生成器",
                 font=("Microsoft YaHei", 16, "bold")).pack(side="left")

        # ── 文件选择行 ──
        file_row = tk.Frame(self)
        file_row.pack(fill="x", padx=16, pady=(0, 8))

        self._path_var = tk.StringVar(value="请选择音频文件...")
        tk.Entry(file_row, textvariable=self._path_var,
                 font=("Microsoft YaHei", 9), state="readonly").pack(
            side="left", fill="x", expand=True, padx=(0, 8))
        tk.Button(file_row, text="选择音频",
                  font=("Microsoft YaHei", 10),
                  command=self._select_audio).pack(side="right")

        self._audio_info = tk.Label(self, text="",
                                    font=("Microsoft YaHei", 9), fg="#666")
        self._audio_info.pack(anchor="w", padx=16)

        # ── 预览区 ──
        preview_frame = tk.Frame(self, bg="#14121e", relief="sunken", bd=1)
        preview_frame.pack(fill="x", padx=16, pady=8, ipady=4)

        self._preview_label = tk.Label(preview_frame, bg="#14121e",
                                       text="选择音频文件后点「生成预览」查看效果",
                                       font=("Microsoft YaHei", 10),
                                       fg="#555")
        self._preview_label.pack(fill="both", expand=True, padx=4, pady=4)

        # ── 参数区（两列布局）──
        params = tk.Frame(self)
        params.pack(fill="x", padx=16, pady=(4, 8))

        col_left = tk.LabelFrame(params, text=" 样式设置 ",
                                 font=("Microsoft YaHei", 10, "bold"))
        col_left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        col_right = tk.LabelFrame(params, text=" 输出设置 ",
                                  font=("Microsoft YaHei", 10, "bold"))
        col_right.pack(side="right", fill="both", expand=True, padx=(6, 0))

        # ─ 左列：样式 ─

        # 配色方案
        r1 = tk.Frame(col_left)
        r1.pack(fill="x", padx=8, pady=(8, 3))
        tk.Label(r1, text="配色：", font=("Microsoft YaHei", 9)).pack(side="left")
        self._preset_var = tk.IntVar(value=0)
        preset_names = [p[0] for p in COLOR_PRESETS]
        self._preset_combo = ttk.Combobox(r1, values=preset_names,
                                          state="readonly", width=12)
        self._preset_combo.current(0)
        self._preset_combo.pack(side="left", padx=4)
        self._preset_combo.bind("<<ComboboxSelected>>", self._on_preset_change)

        # 色块预览
        self._color_preview = tk.Canvas(r1, width=60, height=18,
                                        highlightthickness=0)
        self._color_preview.pack(side="left", padx=4)
        self._update_color_preview()

        # 条形宽度
        r2 = tk.Frame(col_left)
        r2.pack(fill="x", padx=8, pady=3)
        tk.Label(r2, text="条形宽：", font=("Microsoft YaHei", 9)).pack(side="left")
        self._bar_w_var = tk.IntVar(value=3)
        tk.Spinbox(r2, from_=1, to=12, textvariable=self._bar_w_var,
                   width=4, font=("Microsoft YaHei", 10)).pack(side="left", padx=4)
        tk.Label(r2, text="px", font=("Microsoft YaHei", 8),
                 fg="#888").pack(side="left")

        tk.Label(r2, text="  间距：", font=("Microsoft YaHei", 9)).pack(side="left")
        self._gap_var = tk.IntVar(value=1)
        tk.Spinbox(r2, from_=0, to=8, textvariable=self._gap_var,
                   width=4, font=("Microsoft YaHei", 10)).pack(side="left", padx=4)
        tk.Label(r2, text="px", font=("Microsoft YaHei", 8),
                 fg="#888").pack(side="left")

        # 勾选项
        r3 = tk.Frame(col_left)
        r3.pack(fill="x", padx=8, pady=3)
        self._mirror_var = tk.BooleanVar(value=True)
        tk.Checkbutton(r3, text="镜像模式", variable=self._mirror_var,
                       font=("Microsoft YaHei", 9)).pack(side="left")

        self._round_var = tk.BooleanVar(value=True)
        tk.Checkbutton(r3, text="圆角条形", variable=self._round_var,
                       font=("Microsoft YaHei", 9)).pack(side="left")

        r4 = tk.Frame(col_left)
        r4.pack(fill="x", padx=8, pady=(3, 8))
        self._glow_var = tk.BooleanVar(value=True)
        tk.Checkbutton(r4, text="发光效果", variable=self._glow_var,
                       font=("Microsoft YaHei", 9)).pack(side="left")

        self._time_var = tk.BooleanVar(value=True)
        tk.Checkbutton(r4, text="显示时间", variable=self._time_var,
                       font=("Microsoft YaHei", 9)).pack(side="left")

        self._centerline_var = tk.BooleanVar(value=True)
        tk.Checkbutton(r4, text="中线", variable=self._centerline_var,
                       font=("Microsoft YaHei", 9)).pack(side="left")

        # ─ 右列：输出 ─

        # 图片尺寸
        r5 = tk.Frame(col_right)
        r5.pack(fill="x", padx=8, pady=(8, 3))
        tk.Label(r5, text="宽度：", font=("Microsoft YaHei", 9)).pack(side="left")
        self._width_var = tk.IntVar(value=1920)
        size_combo = ttk.Combobox(r5, values=["800", "1200", "1600", "1920", "2560", "3840"],
                                  textvariable=self._width_var, width=6)
        size_combo.pack(side="left", padx=4)
        tk.Label(r5, text="px", font=("Microsoft YaHei", 8),
                 fg="#888").pack(side="left")

        r6 = tk.Frame(col_right)
        r6.pack(fill="x", padx=8, pady=3)
        tk.Label(r6, text="高度：", font=("Microsoft YaHei", 9)).pack(side="left")
        self._height_var = tk.IntVar(value=500)
        h_combo = ttk.Combobox(r6, values=["300", "400", "500", "600", "800"],
                               textvariable=self._height_var, width=6)
        h_combo.pack(side="left", padx=4)
        tk.Label(r6, text="px", font=("Microsoft YaHei", 8),
                 fg="#888").pack(side="left")

        # 背景色
        r7 = tk.Frame(col_right)
        r7.pack(fill="x", padx=8, pady=3)
        self._custom_bg_var = tk.BooleanVar(value=False)
        tk.Checkbutton(r7, text="自定义背景色：",
                       variable=self._custom_bg_var,
                       font=("Microsoft YaHei", 9)).pack(side="left")
        self._bg_color = (20, 20, 25)
        self._bg_btn = tk.Button(r7, text="  ", width=3,
                                 bg="#141419", relief="solid",
                                 command=self._pick_bg)
        self._bg_btn.pack(side="left", padx=4)

        # 透明背景
        r8 = tk.Frame(col_right)
        r8.pack(fill="x", padx=8, pady=(3, 8))
        self._transp_var = tk.BooleanVar(value=False)
        tk.Checkbutton(r8, text="透明背景（PNG）",
                       variable=self._transp_var,
                       font=("Microsoft YaHei", 9)).pack(side="left")

        # ── 底部按钮 ──
        btn_row = tk.Frame(self)
        btn_row.pack(fill="x", padx=16, pady=(4, 16))

        tk.Button(btn_row, text="生成预览",
                  font=("Microsoft YaHei", 12, "bold"),
                  command=self._preview).pack(side="left", padx=(0, 10))
        tk.Button(btn_row, text="保存图片",
                  font=("Microsoft YaHei", 12),
                  command=self._save).pack(side="left")

    def _select_audio(self):
        path = filedialog.askopenfilename(
            title="选择音频文件",
            filetypes=[("音频文件", "*.mp3 *.wav *.flac *.ogg *.aac *.m4a *.wma"),
                       ("所有文件", "*.*")])
        if not path:
            return

        self._path_var.set(path)
        self._audio_info.configure(text="正在加载音频...")
        self.update_idletasks()

        try:
            self._samples, sr, self._duration = load_audio_samples(path)
            self._audio_path = path
            mm = int(self._duration) // 60
            ss = int(self._duration) % 60
            name = os.path.basename(path)
            self._audio_info.configure(
                text=f"{name}    时长 {mm}:{ss:02d}    采样率 {sr}Hz    "
                     f"样本数 {len(self._samples):,}")
        except Exception as e:
            messagebox.showerror("加载失败", f"无法读取音频文件：\n{e}")
            self._audio_info.configure(text="")

    def _on_preset_change(self, event=None):
        self._update_color_preview()

    def _update_color_preview(self):
        idx = self._preset_combo.current()
        if idx < 0:
            idx = 0
        preset = COLOR_PRESETS[idx]
        _, c_top, c_bot, bg, _ = preset

        self._color_preview.delete("all")
        # 画一个小渐变条
        for x in range(60):
            t = x / 60
            c = _lerp_color(c_top, c_bot, t)
            hex_c = f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"
            self._color_preview.create_line(x, 0, x, 18, fill=hex_c)

    def _pick_bg(self):
        color = colorchooser.askcolor(initialcolor=self._bg_color,
                                      title="选择背景色")
        if color[0]:
            self._bg_color = tuple(int(c) for c in color[0])
            self._bg_btn.configure(bg=color[1])

    def _get_params(self):
        """收集当前参数"""
        idx = self._preset_combo.current()
        if idx < 0:
            idx = 0

        bg = None
        if self._custom_bg_var.get():
            bg = self._bg_color

        return dict(
            width=self._width_var.get(),
            height=self._height_var.get(),
            bar_width=self._bar_w_var.get(),
            gap=self._gap_var.get(),
            mirror=self._mirror_var.get(),
            color_preset_idx=idx,
            bg_color=bg,
            rounded=self._round_var.get(),
            glow=self._glow_var.get(),
            center_line=self._centerline_var.get(),
            show_time=self._time_var.get(),
        )

    def _do_generate(self):
        if self._samples is None:
            messagebox.showwarning("提示", "请先选择音频文件")
            return None
        params = self._get_params()
        try:
            return generate_waveform(self._samples, self._duration, **params)
        except Exception as e:
            messagebox.showerror("生成失败", str(e))
            return None

    def _preview(self):
        result = self._do_generate()
        if result is None:
            return

        self._result_image = result

        # 缩放到预览区宽度
        preview_w = WINDOW_WIDTH - 40
        ratio = preview_w / result.width
        disp_h = int(result.height * ratio)
        disp_h = min(disp_h, 200)
        disp_w = int(result.width * (disp_h / result.height))

        disp = result.resize((disp_w, disp_h), Image.LANCZOS)
        self._preview_photo = ImageTk.PhotoImage(disp)
        self._preview_label.configure(image=self._preview_photo, text="")

    def _save(self):
        if not hasattr(self, '_result_image') or self._result_image is None:
            result = self._do_generate()
            if result is None:
                return
            self._result_image = result

        name = ""
        if self._audio_path:
            name = os.path.splitext(os.path.basename(self._audio_path))[0]

        default_name = f"{name}_waveform.png" if name else "waveform.png"

        save_path = filedialog.asksaveasfilename(
            title="保存波形图",
            initialfile=default_name,
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if not save_path:
            return

        try:
            output = self._result_image

            # 透明背景
            if self._transp_var.get() and save_path.lower().endswith(".png"):
                params = self._get_params()
                bg = params.get("bg_color")
                if bg is None:
                    idx = self._preset_combo.current()
                    bg = COLOR_PRESETS[max(idx, 0)][3]
                # 将背景色替换为透明
                rgba = output.convert("RGBA")
                data = rgba.getdata()
                new_data = []
                for pixel in data:
                    r, g, b, a = pixel
                    # 如果颜色接近背景色，设为透明
                    if (abs(r - bg[0]) < 15 and abs(g - bg[1]) < 15
                            and abs(b - bg[2]) < 15):
                        new_data.append((r, g, b, 0))
                    else:
                        new_data.append(pixel)
                rgba.putdata(new_data)
                rgba.save(save_path, "PNG")
            elif save_path.lower().endswith((".jpg", ".jpeg")):
                output.convert("RGB").save(save_path, "JPEG", quality=95)
            else:
                output.save(save_path, "PNG")

            messagebox.showinfo("保存成功", f"波形图已保存至：\n{save_path}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))


if __name__ == "__main__":
    app = WaveformApp()
    app.mainloop()
