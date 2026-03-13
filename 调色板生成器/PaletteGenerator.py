"""
调色板生成器 —— GUI 图形窗口版
输入一个基准色，自动生成多种经典配色方案
支持互补色、邻近色、三角色、分裂互补、四角色
可复制色值、导出色卡图片
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import colorsys
import os

try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

WINDOW_WIDTH = 780
WINDOW_HEIGHT = 640

# ── 配色方案定义 ──
# 每种方案以 HSV 色相偏移角度定义

SCHEMES = {
    "互补色 Complementary": [0, 180],
    "邻近色 Analogous": [-30, 0, 30],
    "三角色 Triadic": [0, 120, 240],
    "分裂互补 Split-Comp.": [0, 150, 210],
    "四角色 Tetradic": [0, 90, 180, 270],
    "单色系 Monochromatic": "mono",
}


def hex_to_rgb(hex_str):
    """HEX 转 RGB"""
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(r, g, b):
    """RGB 转 HEX"""
    return f"#{int(r):02X}{int(g):02X}{int(b):02X}"


def rgb_to_hsv(r, g, b):
    """RGB(0-255) → HSV(0-360, 0-1, 0-1)"""
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return h * 360, s, v


def hsv_to_rgb(h, s, v):
    """HSV(0-360, 0-1, 0-1) → RGB(0-255)"""
    h = h % 360
    r, g, b = colorsys.hsv_to_rgb(h / 360, max(0, min(1, s)),
                                   max(0, min(1, v)))
    return int(r * 255), int(g * 255), int(b * 255)


def generate_palette(base_rgb, scheme_name):
    """根据基准色和方案名生成配色列表，返回 [(r,g,b), ...]"""
    h, s, v = rgb_to_hsv(*base_rgb)
    offsets = SCHEMES.get(scheme_name)

    if offsets == "mono":
        # 单色系：同色相，不同明度/饱和度
        colors = []
        for vv in [0.95, 0.75, 0.55, 0.35, 0.2]:
            colors.append(hsv_to_rgb(h, s * 0.8, vv))
        # 再插入原色
        colors.insert(2, base_rgb)
        return colors[:6]

    if offsets is None:
        return [base_rgb]

    colors = []
    for offset in offsets:
        new_h = (h + offset) % 360
        colors.append(hsv_to_rgb(new_h, s, v))
    return colors


def generate_tints_shades(base_rgb, count=5):
    """生成一组从浅到深的色调变化"""
    h, s, v = rgb_to_hsv(*base_rgb)
    result = []
    for i in range(count):
        t = (i + 1) / (count + 1)
        # 从浅（高 V 低 S）到深（低 V 高 S）
        nv = 1.0 - t * (1.0 - v * 0.3)
        ns = s * (0.3 + t * 0.7)
        result.append(hsv_to_rgb(h, ns, nv))
    return result


def export_palette_image(scheme_colors, output_path):
    """导出所有配色方案为一张图片"""
    swatch_w, swatch_h = 80, 80
    text_h = 40
    padding = 15
    section_gap = 20

    try:
        font = ImageFont.truetype(
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"),
                         "Fonts", "msyh.ttc"),
            13)
        font_small = ImageFont.truetype(
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"),
                         "Fonts", "msyh.ttc"),
            11)
    except Exception:
        font = ImageFont.load_default()
        font_small = font

    # 计算画布尺寸
    max_cols = max(len(colors) for _, colors in scheme_colors)
    img_w = padding * 2 + max_cols * (swatch_w + 8)
    img_w = max(img_w, 500)
    rows = len(scheme_colors)
    img_h = padding + rows * (30 + swatch_h + text_h + section_gap)

    canvas = Image.new("RGB", (img_w, img_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    y = padding
    for name, colors in scheme_colors:
        # 方案名称
        draw.text((padding, y), name, fill=(50, 50, 50), font=font)
        y += 28

        x = padding
        for rgb in colors:
            hex_val = rgb_to_hex(*rgb)

            # 色块
            draw.rounded_rectangle(
                [x, y, x + swatch_w, y + swatch_h],
                radius=6, fill=rgb, outline=(220, 220, 220))

            # HEX 文字
            draw.text((x, y + swatch_h + 4), hex_val,
                      fill=(80, 80, 80), font=font_small)
            # RGB 文字
            rgb_text = f"{rgb[0]},{rgb[1]},{rgb[2]}"
            draw.text((x, y + swatch_h + 18), rgb_text,
                      fill=(150, 150, 150), font=font_small)

            x += swatch_w + 8

        y += swatch_h + text_h + section_gap

    canvas.save(output_path, "PNG")
    return output_path


# ══════════════════════════════════════════════════════════
#  GUI 界面
# ══════════════════════════════════════════════════════════

class PaletteApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("调色板生成器")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self._base_color = (66, 133, 244)  # 默认蓝色
        self._scheme_data = []  # [(name, [(r,g,b), ...]), ...]

        if not HAS_PIL:
            self._dep_error()
        else:
            self._build_ui()
            self._generate()

    def _dep_error(self):
        f = tk.Frame(self)
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="缺少依赖库", font=("Microsoft YaHei", 20, "bold"),
                 fg="#c62828").pack(pady=(0, 12))
        tk.Label(f, text="pip install Pillow",
                 font=("Consolas", 14, "bold"), fg="#1a73e8").pack(pady=12)

    def _build_ui(self):
        # 顶部：基准色选择
        top = tk.Frame(self)
        top.pack(fill="x", padx=16, pady=(16, 8))

        tk.Label(top, text="调色板生成器",
                 font=("Microsoft YaHei", 16, "bold")).pack(side="left")

        # 右侧控件
        right_ctrls = tk.Frame(top)
        right_ctrls.pack(side="right")

        tk.Button(right_ctrls, text="导出色卡图片",
                  font=("Microsoft YaHei", 10),
                  command=self._export).pack(side="right", padx=(8, 0))
        tk.Button(right_ctrls, text="复制全部色值",
                  font=("Microsoft YaHei", 10),
                  command=self._copy_all).pack(side="right", padx=(8, 0))

        # 基准色区域
        color_frame = tk.Frame(self)
        color_frame.pack(fill="x", padx=16, pady=(0, 8))

        tk.Label(color_frame, text="基准色：",
                 font=("Microsoft YaHei", 11)).pack(side="left")

        self._base_btn = tk.Button(color_frame, text="   ", width=4, height=1,
                                   bg=rgb_to_hex(*self._base_color),
                                   relief="solid",
                                   command=self._pick_color)
        self._base_btn.pack(side="left", padx=(4, 8))

        self._hex_var = tk.StringVar(value=rgb_to_hex(*self._base_color))
        hex_entry = tk.Entry(color_frame, textvariable=self._hex_var,
                             font=("Consolas", 12), width=9)
        hex_entry.pack(side="left", padx=(0, 8))
        hex_entry.bind("<Return>", self._on_hex_enter)

        tk.Button(color_frame, text="应用",
                  font=("Microsoft YaHei", 10),
                  command=self._on_hex_enter).pack(side="left", padx=(0, 12))

        # 预设颜色快捷按钮
        presets = [
            ("#FF4444", "红"), ("#FF8800", "橙"), ("#FFCC00", "黄"),
            ("#44BB44", "绿"), ("#4285F4", "蓝"), ("#9933CC", "紫"),
            ("#FF69B4", "粉"), ("#333333", "黑"), ("#FFFFFF", "白"),
        ]
        for hex_c, label in presets:
            b = tk.Button(color_frame, text="  ", width=2,
                          bg=hex_c, relief="solid",
                          command=lambda c=hex_c: self._set_color(c))
            b.pack(side="left", padx=1)

        # 分割线
        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=16, pady=4)

        # 配色方案滚动区域
        container = tk.Frame(self)
        container.pack(fill="both", expand=True, padx=16, pady=(4, 16))

        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical",
                                  command=canvas.yview)
        self._scroll_frame = tk.Frame(canvas)

        self._scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self._canvas = canvas

    def _pick_color(self):
        color = colorchooser.askcolor(
            initialcolor=self._base_color, title="选择基准色")
        if color[0]:
            self._base_color = tuple(int(c) for c in color[0])
            hex_val = rgb_to_hex(*self._base_color)
            self._hex_var.set(hex_val)
            self._base_btn.configure(bg=hex_val)
            self._generate()

    def _set_color(self, hex_val):
        self._base_color = hex_to_rgb(hex_val)
        self._hex_var.set(hex_val)
        self._base_btn.configure(bg=hex_val)
        self._generate()

    def _on_hex_enter(self, event=None):
        hex_val = self._hex_var.get().strip()
        if not hex_val.startswith("#"):
            hex_val = "#" + hex_val
        hex_val = hex_val.upper()
        if len(hex_val) != 7:
            messagebox.showwarning("格式错误", "请输入正确的 HEX 色值，如 #FF5500")
            return
        try:
            self._base_color = hex_to_rgb(hex_val)
            self._hex_var.set(hex_val)
            self._base_btn.configure(bg=hex_val)
            self._generate()
        except ValueError:
            messagebox.showwarning("格式错误", "请输入正确的 HEX 色值，如 #FF5500")

    def _generate(self):
        """生成所有配色方案并显示"""
        # 清空旧内容
        for w in self._scroll_frame.winfo_children():
            w.destroy()
        self._scheme_data = []

        for scheme_name in SCHEMES:
            colors = generate_palette(self._base_color, scheme_name)
            self._scheme_data.append((scheme_name, colors))
            self._render_scheme(scheme_name, colors)

        # 额外：色调变化
        tints = generate_tints_shades(self._base_color, count=7)
        self._scheme_data.append(("色调渐变 Tints & Shades", tints))
        self._render_scheme("色调渐变 Tints & Shades", tints)

    def _render_scheme(self, name, colors):
        """渲染一个配色方案到界面"""
        section = tk.Frame(self._scroll_frame)
        section.pack(fill="x", pady=(0, 12), anchor="w")

        # 方案名称
        tk.Label(section, text=name,
                 font=("Microsoft YaHei", 11, "bold"),
                 fg="#333").pack(anchor="w", pady=(0, 4))

        # 色块行
        row = tk.Frame(section)
        row.pack(anchor="w")

        for rgb in colors:
            hex_val = rgb_to_hex(*rgb)
            brightness = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
            fg = "#FFFFFF" if brightness < 128 else "#333333"

            swatch = tk.Frame(row, width=88, height=72, bg=hex_val,
                              relief="solid", bd=1, cursor="hand2")
            swatch.pack(side="left", padx=(0, 6))
            swatch.pack_propagate(False)

            tk.Label(swatch, text=hex_val, bg=hex_val, fg=fg,
                     font=("Consolas", 10, "bold")).pack(expand=True)

            rgb_text = f"{rgb[0]},{rgb[1]},{rgb[2]}"
            tk.Label(swatch, text=rgb_text, bg=hex_val, fg=fg,
                     font=("Consolas", 8)).pack(pady=(0, 4))

            # 点击复制
            swatch.bind("<Button-1>",
                        lambda e, h=hex_val: self._copy_one(h))
            for child in swatch.winfo_children():
                child.bind("<Button-1>",
                           lambda e, h=hex_val: self._copy_one(h))

        # 分割线
        ttk.Separator(self._scroll_frame,
                      orient="horizontal").pack(fill="x", pady=(8, 0))

    def _copy_one(self, hex_val):
        self.clipboard_clear()
        self.clipboard_append(hex_val)
        self.title(f"调色板生成器  —  已复制 {hex_val}")
        self.after(2000, lambda: self.title("调色板生成器"))

    def _copy_all(self):
        if not self._scheme_data:
            return
        lines = []
        for name, colors in self._scheme_data:
            hexes = "  ".join(rgb_to_hex(*c) for c in colors)
            lines.append(f"【{name}】\n{hexes}")
        text = "\n\n".join(lines)
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("已复制", "所有配色方案色值已复制到剪贴板")

    def _export(self):
        if not self._scheme_data:
            return
        save_path = filedialog.asksaveasfilename(
            title="导出色卡图片",
            initialfile="调色板.png",
            defaultextension=".png",
            filetypes=[("PNG", "*.png")])
        if not save_path:
            return
        try:
            export_palette_image(self._scheme_data, save_path)
            messagebox.showinfo("导出成功", f"色卡已保存至：\n{save_path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))


if __name__ == "__main__":
    app = PaletteApp()
    app.mainloop()
