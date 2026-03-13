"""
波普效果生成器 1.0 —— GUI 图形窗口版
给图片添加半调网点（Halftone）波普艺术效果
支持调整网点大小、颜色、饱和度、深浅、色彩风格
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import os
import math
import threading

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

WINDOW_WIDTH = 820
WINDOW_HEIGHT = 660

# 波普配色预设
COLOR_PRESETS = {
    "经典黑白": {"dot": (0, 0, 0), "bg": (255, 255, 255)},
    "红白波普": {"dot": (220, 30, 50), "bg": (255, 240, 240)},
    "蓝白波普": {"dot": (30, 80, 200), "bg": (235, 240, 255)},
    "粉色甜美": {"dot": (230, 80, 130), "bg": (255, 245, 248)},
    "金色复古": {"dot": (180, 140, 50), "bg": (255, 250, 235)},
    "青绿清新": {"dot": (0, 160, 140), "bg": (240, 255, 252)},
    "自定义": {"dot": (0, 0, 0), "bg": (255, 255, 255)},
}


def apply_halftone(img, dot_spacing=8, dot_color=(0, 0, 0), bg_color=(255, 255, 255),
                   max_dot_ratio=0.9, saturation=1.0, contrast=1.0, blend=1.0):
    """
    给图片生成半调网点波普效果。
    返回 (合成图, 纯网点透明底图)
    """
    original = img.convert("RGB")

    # 调整饱和度和对比度
    work = original.copy()
    if saturation != 1.0:
        work = ImageEnhance.Color(work).enhance(saturation)
    if contrast != 1.0:
        work = ImageEnhance.Contrast(work).enhance(contrast)

    # 转灰度用于计算网点大小
    gray = work.convert("L")

    w, h = original.size
    halftone = Image.new("RGB", (w, h), bg_color)
    draw = ImageDraw.Draw(halftone)

    # 纯网点图（透明底）
    dots_only = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dots_draw = ImageDraw.Draw(dots_only)

    max_radius = dot_spacing * max_dot_ratio / 2

    dot_fill_rgba = dot_color + (255,)

    # 逐网格绘制圆点
    for y in range(0, h, dot_spacing):
        for x in range(0, w, dot_spacing):
            box = gray.crop((
                x, y,
                min(x + dot_spacing, w),
                min(y + dot_spacing, h),
            ))
            avg_brightness = sum(box.getdata()) / max(1, box.size[0] * box.size[1])

            darkness = 1 - (avg_brightness / 255)
            radius = max_radius * darkness

            if radius < 0.5:
                continue

            cx = x + dot_spacing // 2
            cy = y + dot_spacing // 2
            bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
            draw.ellipse(bbox, fill=dot_color)
            dots_draw.ellipse(bbox, fill=dot_fill_rgba)

    # 混合原图和波普效果
    if blend < 1.0:
        halftone = Image.blend(original, halftone, blend)

    return halftone, dots_only


def apply_color_halftone(img, dot_spacing=8, max_dot_ratio=0.9,
                         saturation=1.0, contrast=1.0):
    """
    彩色半调：分别对 C/M/Y 通道做半调，叠加出彩色波普效果。
    模拟印刷品的 CMYK 网点效果。
    返回 (合成图, 纯网点透明底图)
    """
    original = img.convert("RGB")

    work = original.copy()
    if saturation != 1.0:
        work = ImageEnhance.Color(work).enhance(saturation)
    if contrast != 1.0:
        work = ImageEnhance.Contrast(work).enhance(contrast)

    w, h = original.size
    result = Image.new("RGB", (w, h), (255, 255, 255))

    # 纯网点图（透明底）
    dots_only = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    r, g, b = work.split()

    channels = [
        (r, (0, 174, 239)),    # Cyan
        (g, (236, 0, 140)),    # Magenta
        (b, (255, 242, 0)),    # Yellow
    ]

    angles = [15, 75, 0]

    max_radius = dot_spacing * max_dot_ratio / 2

    for (channel, color), angle in zip(channels, angles):
        overlay = Image.new("RGBA", (w, h), (255, 255, 255, 0))
        odraw = ImageDraw.Draw(overlay)

        # 同时画到纯网点图
        dots_odraw = ImageDraw.Draw(dots_only)

        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        for gy in range(-dot_spacing, h + dot_spacing, dot_spacing):
            for gx in range(-dot_spacing, w + dot_spacing, dot_spacing):
                # 旋转网格
                cx = int(gx * cos_a - gy * sin_a) % (w + dot_spacing)
                cy = int(gx * sin_a + gy * cos_a) % (h + dot_spacing)

                if cx >= w or cy >= h or cx < 0 or cy < 0:
                    continue

                # 采样
                sx = max(0, min(cx, w - 1))
                sy = max(0, min(cy, h - 1))
                brightness = channel.getpixel((sx, sy))

                # 暗 = 大点（取反：255-brightness 因为是 CMY）
                darkness = 1 - (brightness / 255)
                radius = max_radius * darkness

                if radius < 0.3:
                    continue

                fill = color + (180,)  # 半透明
                odraw.ellipse(
                    [cx - radius, cy - radius, cx + radius, cy + radius],
                    fill=fill,
                )
                dots_odraw.ellipse(
                    [cx - radius, cy - radius, cx + radius, cy + radius],
                    fill=fill,
                )

        result = Image.alpha_composite(result.convert("RGBA"), overlay).convert("RGB")

    return result, dots_only


# ── GUI ─────────────────────────────────────────────

class PopArtApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("波普效果生成器 1.0")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)

        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self._source_path = None
        self._result_image = None
        self._tk_preview = None
        self._dot_color = (0, 0, 0)
        self._bg_color = (255, 255, 255)

        if not HAS_PIL:
            self._dep_error()
        else:
            self._show_start()

    def _clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    def _dep_error(self):
        self._clear()
        f = tk.Frame(self.container); f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="缺少依赖库", font=("Microsoft YaHei", 20, "bold"), fg="#c62828").pack(pady=(0, 12))
        tk.Label(f, text="pip install Pillow", font=("Consolas", 14, "bold"), fg="#1a73e8").pack(pady=12)

    # ── 开始页 ───────────────────────────────────────

    def _show_start(self):
        self._clear()
        f = tk.Frame(self.container); f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="波普效果生成器", font=("Microsoft YaHei", 24, "bold")).pack(pady=(0, 6))
        tk.Label(f, text="给图片添加半调网点（Halftone）波普艺术效果",
                 font=("Microsoft YaHei", 10), fg="#666").pack(pady=(0, 30))
        tk.Button(f, text="选择图片", font=("Microsoft YaHei", 13),
                  width=20, height=2, command=self._on_select).pack(pady=6)

    def _on_select(self):
        path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("图片", "*.png *.jpg *.jpeg *.webp *.bmp")],
        )
        if not path:
            return
        self._source_path = path
        self._show_editor()

    # ── 编辑页 ───────────────────────────────────────

    def _show_editor(self):
        self._clear()

        # 顶部
        top = tk.Frame(self.container)
        top.pack(fill="x", padx=15, pady=(10, 5))
        tk.Button(top, text="← 换图", font=("Microsoft YaHei", 10), command=self._show_start).pack(side="left")
        tk.Label(top, text=os.path.basename(self._source_path),
                 font=("Microsoft YaHei", 10), fg="#888").pack(side="left", padx=10)

        main = tk.Frame(self.container)
        main.pack(fill="both", expand=True, padx=15, pady=5)

        # ── 左侧控制面板 ────────────────────────────
        left = tk.Frame(main, width=320)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        # 效果模式
        tk.Label(left, text="效果模式：", font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", pady=(0, 3))
        self._mode_var = tk.StringVar(value="single")
        r1 = tk.Frame(left); r1.pack(fill="x")
        tk.Radiobutton(r1, text="单色网点", variable=self._mode_var, value="single",
                       font=("Microsoft YaHei", 10)).pack(side="left")
        tk.Radiobutton(r1, text="彩色印刷（CMYK风格）", variable=self._mode_var, value="cmyk",
                       font=("Microsoft YaHei", 10)).pack(side="left")

        # 配色预设
        tk.Label(left, text="配色预设：", font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", pady=(10, 3))
        self._preset_var = tk.StringVar(value="经典黑白")
        preset_cb = ttk.Combobox(left, textvariable=self._preset_var,
                                 values=list(COLOR_PRESETS.keys()), state="readonly", width=18)
        preset_cb.pack(anchor="w")
        preset_cb.bind("<<ComboboxSelected>>", self._on_preset)

        # 自定义颜色
        color_row = tk.Frame(left); color_row.pack(fill="x", pady=(5, 0))
        tk.Label(color_row, text="网点色：", font=("Microsoft YaHei", 9)).pack(side="left")
        self._dot_btn = tk.Button(color_row, text="  ", bg="black", width=3,
                                  command=lambda: self._pick_color("dot"))
        self._dot_btn.pack(side="left", padx=(0, 10))
        tk.Label(color_row, text="背景色：", font=("Microsoft YaHei", 9)).pack(side="left")
        self._bg_btn = tk.Button(color_row, text="  ", bg="white", width=3,
                                 command=lambda: self._pick_color("bg"))
        self._bg_btn.pack(side="left")

        # 参数滑块
        tk.Label(left, text="参数调整：", font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", pady=(12, 3))

        self._spacing_var = tk.IntVar(value=8)
        self._make_slider(left, "网点间距", self._spacing_var, 3, 20,
                          "小=密集细腻  大=稀疏粗犷")

        self._depth_var = tk.IntVar(value=85)
        self._make_slider(left, "深浅（网点最大占比%）", self._depth_var, 30, 100,
                          "小=淡淡的  大=浓重")

        self._saturation_var = tk.IntVar(value=120)
        self._make_slider(left, "饱和度%", self._saturation_var, 0, 200,
                          "0=灰色  100=原色  200=浓烈")

        self._contrast_var = tk.IntVar(value=120)
        self._make_slider(left, "对比度%", self._contrast_var, 50, 200,
                          "低=柔和  高=强烈")

        self._blend_var = tk.IntVar(value=100)
        self._make_slider(left, "效果强度%", self._blend_var, 0, 100,
                          "0=原图  100=纯波普")

        # 按钮
        btn_row = tk.Frame(left); btn_row.pack(fill="x", pady=(12, 0))
        tk.Button(btn_row, text="生成预览", font=("Microsoft YaHei", 11, "bold"),
                  bg="#1a73e8", fg="white", activebackground="#1557b0", activeforeground="white",
                  relief="flat", padx=12, command=self._generate).pack(side="left", padx=(0, 6))
        tk.Button(btn_row, text="保存图片", font=("Microsoft YaHei", 11),
                  command=self._save).pack(side="left")

        # ── 右侧预览区 ──────────────────────────────
        right = tk.Frame(main, bg="#f0f0f0", relief="groove", bd=1)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))

        tk.Label(right, text="预览", font=("Microsoft YaHei", 9, "bold"), bg="#f0f0f0").pack(pady=(5, 0))
        self._preview_label = tk.Label(right, text="点击「生成预览」查看效果",
                                       font=("Microsoft YaHei", 10), fg="#999", bg="#f0f0f0")
        self._preview_label.pack(expand=True)

        self._status_label = tk.Label(right, text="", font=("Microsoft YaHei", 9), fg="#888", bg="#f0f0f0")
        self._status_label.pack(pady=(0, 5))

    def _make_slider(self, parent, label, var, from_, to, hint):
        f = tk.Frame(parent); f.pack(fill="x", pady=1)
        tk.Label(f, text=label, font=("Microsoft YaHei", 9)).pack(anchor="w")
        sf = tk.Frame(f); sf.pack(fill="x")
        tk.Scale(sf, from_=from_, to=to, orient="horizontal", variable=var, length=220,
                 showvalue=True).pack(side="left")
        tk.Label(sf, text=hint, font=("Microsoft YaHei", 8), fg="#aaa").pack(side="left", padx=5)

    def _on_preset(self, event=None):
        name = self._preset_var.get()
        if name in COLOR_PRESETS and name != "自定义":
            p = COLOR_PRESETS[name]
            self._dot_color = p["dot"]
            self._bg_color = p["bg"]
            r, g, b = self._dot_color
            self._dot_btn.config(bg=f"#{r:02x}{g:02x}{b:02x}")
            r, g, b = self._bg_color
            self._bg_btn.config(bg=f"#{r:02x}{g:02x}{b:02x}")

    def _pick_color(self, target):
        initial = self._dot_color if target == "dot" else self._bg_color
        color = colorchooser.askcolor(initialcolor=initial, title="选择颜色")
        if color[0]:
            rgb = tuple(int(c) for c in color[0])
            if target == "dot":
                self._dot_color = rgb
                self._dot_btn.config(bg=color[1])
            else:
                self._bg_color = rgb
                self._bg_btn.config(bg=color[1])
            self._preset_var.set("自定义")

    def _generate(self):
        self._preview_label.config(text="正在生成...", image="", fg="#1a73e8")
        self._status_label.config(text="")
        self.update()

        threading.Thread(target=self._generate_worker, daemon=True).start()

    def _generate_worker(self):
        try:
            img = Image.open(self._source_path)

            mode = self._mode_var.get()
            spacing = self._spacing_var.get()
            depth = self._depth_var.get() / 100
            sat = self._saturation_var.get() / 100
            con = self._contrast_var.get() / 100
            blend = self._blend_var.get() / 100

            if mode == "cmyk":
                result, dots_only = apply_color_halftone(img, dot_spacing=spacing,
                                              max_dot_ratio=depth,
                                              saturation=sat, contrast=con)
                if blend < 1.0:
                    result = Image.blend(img.convert("RGB"), result, blend)
            else:
                result, dots_only = apply_halftone(img, dot_spacing=spacing,
                                        dot_color=self._dot_color, bg_color=self._bg_color,
                                        max_dot_ratio=depth, saturation=sat,
                                        contrast=con, blend=blend)

            self._result_image = result
            self._dots_only_image = dots_only

            # 缩放预览
            preview = result.copy()
            preview.thumbnail((420, 480), Image.LANCZOS)
            self._tk_preview = ImageTk.PhotoImage(preview)

            self.after(0, lambda: (
                self._preview_label.config(image=self._tk_preview, text=""),
                self._status_label.config(text=f"原图 {img.size[0]}x{img.size[1]} → 效果已生成"),
            ))
        except Exception as e:
            self.after(0, lambda: self._preview_label.config(
                text=f"生成失败：{e}", image="", fg="#c62828"))

    def _save(self):
        if not self._result_image:
            messagebox.showinfo("提示", "请先生成预览。")
            return

        stem = os.path.splitext(os.path.basename(self._source_path))[0]
        save_path = filedialog.asksaveasfilename(
            title="保存波普效果图（会同时输出两个文件）",
            defaultextension=".png",
            initialfile=f"{stem}_波普效果.png",
            filetypes=[("PNG", "*.png"), ("JPG", "*.jpg")],
        )
        if not save_path:
            return
        try:
            ext = os.path.splitext(save_path)[1].lower()
            save_dir = os.path.dirname(save_path)
            save_stem = os.path.splitext(os.path.basename(save_path))[0]

            # 1. 保存合成图
            if ext in (".jpg", ".jpeg"):
                self._result_image.convert("RGB").save(save_path, "JPEG", quality=95)
            else:
                self._result_image.save(save_path, "PNG")

            # 2. 保存纯网点图（透明底 PNG）
            dots_path = os.path.join(save_dir, f"{save_stem}_纯网点.png")
            self._dots_only_image.save(dots_path, "PNG")

            messagebox.showinfo("保存成功",
                f"已保存两个文件：\n\n"
                f"1. 合成图：\n{os.path.basename(save_path)}\n\n"
                f"2. 纯网点图（透明底）：\n{os.path.basename(dots_path)}\n\n"
                f"位置：{save_dir}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))


if __name__ == "__main__":
    app = PopArtApp()
    app.mainloop()
