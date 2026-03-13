"""
色卡提取器 1.0 —— GUI 图形窗口版
从一张图片中提取主要颜色，生成配色方案
显示色块 + HEX + RGB，可复制色值，可导出色卡图片
支持自定义颜色数量（3-30）和排序方式
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from collections import Counter

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

WINDOW_WIDTH = 750
WINDOW_HEIGHT = 620

SORT_OPTIONS = {
    "由浅到深": "light_to_dark",
    "由深到浅": "dark_to_light",
    "按占比（多→少）": "frequency",
    "按色相（彩虹序）": "hue",
}


def _brightness(rgb):
    """计算感知亮度 (0=黑 255=白)"""
    r, g, b = rgb
    return 0.299 * r + 0.587 * g + 0.114 * b


def _hue(rgb):
    """计算色相值 0-360"""
    r, g, b = rgb[0] / 255, rgb[1] / 255, rgb[2] / 255
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == mn:
        return 0
    d = mx - mn
    if mx == r:
        h = (g - b) / d % 6
    elif mx == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return h * 60


def sort_colors(colors, method):
    """根据排序方式对颜色列表排序"""
    if method == "light_to_dark":
        return sorted(colors, key=lambda c: _brightness(c["rgb"]), reverse=True)
    elif method == "dark_to_light":
        return sorted(colors, key=lambda c: _brightness(c["rgb"]))
    elif method == "hue":
        return sorted(colors, key=lambda c: _hue(c["rgb"]))
    else:  # frequency
        return sorted(colors, key=lambda c: c["count"], reverse=True)


def extract_colors(image_path, num_colors=8):
    """从图片中提取主要颜色"""
    img = Image.open(image_path).convert("RGB")
    img.thumbnail((200, 200), Image.LANCZOS)

    # 量化颜色数多取一些，再从中选 top N
    quant_num = min(256, num_colors * 5)
    quantized = img.quantize(colors=quant_num, method=Image.Quantize.MEDIANCUT)
    palette = quantized.convert("RGB")

    pixels = list(palette.getdata())
    counter = Counter(pixels)

    colors = []
    for color, count in counter.most_common(num_colors):
        r, g, b = color
        hex_code = f"#{r:02X}{g:02X}{b:02X}"
        colors.append({
            "rgb": (r, g, b),
            "hex": hex_code,
            "count": count,
        })

    return colors


def export_palette_image(colors, save_path, swatch_w=100, swatch_h=100):
    """导出色卡为图片，自动换行"""
    n = len(colors)
    padding = 12
    text_h = 45
    cols = min(n, 10)  # 每行最多 10 个
    rows = (n + cols - 1) // cols

    total_w = padding + cols * (swatch_w + padding)
    total_h = padding + rows * (swatch_h + text_h + padding)

    img = Image.new("RGB", (total_w, total_h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    font = None
    for fp in ["C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/arial.ttf"]:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, 13)
                break
            except Exception:
                continue
    if not font:
        font = ImageFont.load_default()

    for i, c in enumerate(colors):
        col_idx = i % cols
        row_idx = i // cols
        x = padding + col_idx * (swatch_w + padding)
        y = padding + row_idx * (swatch_h + text_h + padding)

        draw.rectangle([x, y, x + swatch_w, y + swatch_h], fill=c["rgb"])
        draw.text((x + 3, y + swatch_h + 4), c["hex"], fill=(50, 50, 50), font=font)
        rgb_text = f"{c['rgb'][0]},{c['rgb'][1]},{c['rgb'][2]}"
        draw.text((x + 3, y + swatch_h + 22), rgb_text, fill=(120, 120, 120), font=font)

    img.save(save_path, "PNG")


class ColorExtractorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("色卡提取器 1.0")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)
        self._colors = []

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
        tk.Label(f, text="色卡提取器", font=("Microsoft YaHei", 24, "bold")).pack(pady=(0, 6))
        tk.Label(f, text="从图片中提取主要颜色，生成配色方案",
                 font=("Microsoft YaHei", 10), fg="#666").pack(pady=(0, 25))

        tk.Button(f, text="选择图片", font=("Microsoft YaHei", 13),
                  width=20, height=2, command=self._on_select).pack(pady=6)

        # 颜色数量
        r1 = tk.Frame(f); r1.pack(pady=(18, 5))
        tk.Label(r1, text="提取颜色数量：", font=("Microsoft YaHei", 10)).pack(side="left")
        self._num_var = tk.IntVar(value=8)
        tk.Spinbox(r1, from_=3, to=30, textvariable=self._num_var, width=4,
                   font=("Microsoft YaHei", 11)).pack(side="left", padx=5)
        tk.Label(r1, text="（3 ~ 30 个）", font=("Microsoft YaHei", 9), fg="#888").pack(side="left")

        # 排序方式
        r2 = tk.Frame(f); r2.pack(pady=(5, 0))
        tk.Label(r2, text="排序方式：", font=("Microsoft YaHei", 10)).pack(side="left")
        self._sort_var = tk.StringVar(value="由浅到深")
        ttk.Combobox(r2, textvariable=self._sort_var,
                     values=list(SORT_OPTIONS.keys()), state="readonly", width=16).pack(side="left", padx=5)

    def _on_select(self):
        path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("图片", "*.png *.jpg *.jpeg *.webp *.bmp")],
        )
        if not path:
            return
        try:
            colors = extract_colors(path, self._num_var.get())
        except Exception as e:
            messagebox.showerror("错误", str(e))
            return

        sort_method = SORT_OPTIONS.get(self._sort_var.get(), "light_to_dark")
        colors = sort_colors(colors, sort_method)

        self._colors = colors
        self._source_path = path
        self._show_result()

    # ── 结果页 ───────────────────────────────────────

    def _show_result(self):
        self._clear()

        top = tk.Frame(self.container)
        top.pack(fill="x", padx=20, pady=(15, 5))
        tk.Button(top, text="← 换一张", font=("Microsoft YaHei", 10), command=self._show_start).pack(side="left")
        tk.Label(top, text="提取结果", font=("Microsoft YaHei", 14, "bold")).pack(side="left", padx=15)

        # 重新排序按钮
        sort_frame = tk.Frame(top)
        sort_frame.pack(side="right")
        tk.Label(sort_frame, text="排序：", font=("Microsoft YaHei", 9)).pack(side="left")
        self._resort_var = tk.StringVar(value=self._sort_var.get())
        resort_cb = ttk.Combobox(sort_frame, textvariable=self._resort_var,
                                 values=list(SORT_OPTIONS.keys()), state="readonly", width=14)
        resort_cb.pack(side="left", padx=3)
        resort_cb.bind("<<ComboboxSelected>>", self._on_resort)

        body = tk.Frame(self.container)
        body.pack(fill="both", expand=True, padx=20, pady=5)

        tk.Label(body, text=f"来源：{os.path.basename(self._source_path)}  |  共 {len(self._colors)} 个颜色",
                 font=("Microsoft YaHei", 10), fg="#888").pack(anchor="w", pady=(0, 8))

        # 色块展示区（滚动支持，颜色多时自动换行）
        swatch_outer = tk.Frame(body)
        swatch_outer.pack(fill="x", pady=(0, 5))

        max_per_row = min(len(self._colors), max(6, (WINDOW_WIDTH - 60) // 75))
        swatch_size = min(65, (WINDOW_WIDTH - 60) // max_per_row - 10)

        row_frame = None
        for i, c in enumerate(self._colors):
            if i % max_per_row == 0:
                row_frame = tk.Frame(swatch_outer)
                row_frame.pack(anchor="w", pady=2)

            col = tk.Frame(row_frame)
            col.pack(side="left", padx=3)

            canvas = tk.Canvas(col, width=swatch_size, height=swatch_size,
                               highlightthickness=1, highlightbackground="#ddd")
            canvas.pack()
            canvas.create_rectangle(0, 0, swatch_size, swatch_size, fill=c["hex"], outline="")

            tk.Label(col, text=c["hex"], font=("Consolas", 8, "bold")).pack(pady=(2, 0))

        # 详情表格
        tk.Label(body, text="色值详情（点击行可复制 HEX 值）：",
                 font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", pady=(8, 3))

        tree_frame = tk.Frame(body)
        tree_frame.pack(fill="both", expand=True)

        cols = ("swatch", "hex", "rgb", "brightness", "pct")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                            height=min(10, len(self._colors)))
        tree.heading("swatch", text="#")
        tree.heading("hex", text="HEX")
        tree.heading("rgb", text="RGB")
        tree.heading("brightness", text="亮度")
        tree.heading("pct", text="占比")
        tree.column("swatch", width=35, anchor="center")
        tree.column("hex", width=100, anchor="center")
        tree.column("rgb", width=150, anchor="center")
        tree.column("brightness", width=60, anchor="center")
        tree.column("pct", width=70, anchor="center")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        total_count = sum(c["count"] for c in self._colors)
        for i, c in enumerate(self._colors):
            pct = f"{c['count'] / total_count * 100:.1f}%"
            r, g, b = c["rgb"]
            bright = int(_brightness(c["rgb"]))
            tree.insert("", "end", values=(f"{i+1}", c["hex"], f"RGB({r}, {g}, {b})", bright, pct))

        def on_click(event):
            item = tree.selection()
            if item:
                hex_val = tree.item(item[0])["values"][1]
                self.clipboard_clear()
                self.clipboard_append(hex_val)
                messagebox.showinfo("已复制", f"已复制到剪贴板：{hex_val}")

        tree.bind("<<TreeviewSelect>>", on_click)

        # 按钮
        btn = tk.Frame(body); btn.pack(pady=(8, 0))
        tk.Button(btn, text="导出色卡图片", font=("Microsoft YaHei", 11), width=14,
                  command=self._export).pack(side="left", padx=6)
        tk.Button(btn, text="复制全部 HEX", font=("Microsoft YaHei", 11), width=14,
                  command=self._copy_all).pack(side="left", padx=6)
        tk.Button(btn, text="返回首页", font=("Microsoft YaHei", 11), width=12,
                  command=self._show_start).pack(side="left", padx=6)

    def _on_resort(self, event=None):
        """结果页内重新排序"""
        method = SORT_OPTIONS.get(self._resort_var.get(), "light_to_dark")
        self._colors = sort_colors(self._colors, method)
        self._sort_var.set(self._resort_var.get())
        self._show_result()

    def _export(self):
        save_path = filedialog.asksaveasfilename(
            title="导出色卡图片",
            defaultextension=".png",
            initialfile=f"色卡_{len(self._colors)}色.png",
            filetypes=[("PNG", "*.png")],
        )
        if not save_path:
            return
        try:
            export_palette_image(self._colors, save_path)
            messagebox.showinfo("导出成功", f"色卡已保存至：\n{save_path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    def _copy_all(self):
        text = "  ".join(c["hex"] for c in self._colors)
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("已复制", f"已复制 {len(self._colors)} 个色值到剪贴板")


if __name__ == "__main__":
    app = ColorExtractorApp()
    app.mainloop()
