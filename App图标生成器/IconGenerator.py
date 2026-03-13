"""
App 图标生成器 —— GUI 图形窗口版
一张图自动导出 iOS / Android / Web 全套图标尺寸
支持圆角裁剪、预览、批量导出
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

try:
    from PIL import Image, ImageDraw, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

WINDOW_WIDTH = 720
WINDOW_HEIGHT = 640

# ── 图标尺寸定义 ──

IOS_SIZES = [
    ("iPhone Notification @2x",  40),
    ("iPhone Notification @3x",  60),
    ("iPhone Settings @2x",      58),
    ("iPhone Settings @3x",      87),
    ("iPhone Spotlight @2x",     80),
    ("iPhone Spotlight @3x",    120),
    ("iPhone App @2x",          120),
    ("iPhone App @3x",          180),
    ("iPad Notification @1x",    20),
    ("iPad Notification @2x",    40),
    ("iPad Settings @1x",        29),
    ("iPad Settings @2x",        58),
    ("iPad Spotlight @1x",       40),
    ("iPad Spotlight @2x",       80),
    ("iPad App @1x",             76),
    ("iPad App @2x",            152),
    ("iPad Pro App @2x",        167),
    ("App Store",              1024),
]

ANDROID_SIZES = [
    ("mdpi (48dp)",       48),
    ("hdpi (72dp)",       72),
    ("xhdpi (96dp)",      96),
    ("xxhdpi (144dp)",   144),
    ("xxxhdpi (192dp)",  192),
    ("Google Play",      512),
]

WEB_SIZES = [
    ("favicon 16",    16),
    ("favicon 32",    32),
    ("favicon 48",    48),
    ("PWA 72",        72),
    ("PWA 96",        96),
    ("PWA 128",      128),
    ("PWA 144",      144),
    ("PWA 192",      192),
    ("PWA 512",      512),
]


def add_rounded_corners(img, radius_ratio=0.2):
    """给图片加圆角（iOS 风格）"""
    size = img.size[0]
    radius = int(size * radius_ratio)

    # 创建圆角蒙版
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, size - 1, size - 1],
                           radius=radius, fill=255)

    result = img.copy().convert("RGBA")
    result.putalpha(mask)
    return result


def generate_icons(source_img, output_dir, platforms, rounded=False,
                   radius_ratio=0.2, progress_callback=None):
    """
    生成全套图标
    platforms: dict {"ios": bool, "android": bool, "web": bool}
    返回生成的文件数量
    """
    # 确保是正方形 RGBA
    img = source_img.convert("RGBA")
    w, h = img.size
    if w != h:
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))

    count = 0
    total = 0
    if platforms.get("ios"):
        total += len(IOS_SIZES)
    if platforms.get("android"):
        total += len(ANDROID_SIZES)
    if platforms.get("web"):
        total += len(WEB_SIZES)

    def _save_set(sizes, folder_name, apply_round):
        nonlocal count
        folder = os.path.join(output_dir, folder_name)
        os.makedirs(folder, exist_ok=True)

        for name, size in sizes:
            resized = img.resize((size, size), Image.LANCZOS)
            if apply_round:
                resized = add_rounded_corners(resized, radius_ratio)

            # 文件名：尺寸_名称.png
            safe_name = name.replace(" ", "_").replace("@", "").replace("(", "").replace(")", "")
            filename = f"{size}x{size}_{safe_name}.png"
            resized.save(os.path.join(folder, filename), "PNG")
            count += 1
            if progress_callback:
                progress_callback(count, total)

    if platforms.get("ios"):
        _save_set(IOS_SIZES, "iOS", rounded)

    if platforms.get("android"):
        _save_set(ANDROID_SIZES, "Android", False)  # Android 自己处理圆角

    if platforms.get("web"):
        _save_set(WEB_SIZES, "Web", False)

    return count


class IconGeneratorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("App 图标生成器")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self._source_img = None
        self._preview_photo = None

        if not HAS_PIL:
            self._dep_error()
        else:
            self._build_ui()

    def _dep_error(self):
        f = tk.Frame(self)
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="缺少依赖库", font=("Microsoft YaHei", 20, "bold"),
                 fg="#c62828").pack(pady=(0, 12))
        tk.Label(f, text="pip install Pillow",
                 font=("Consolas", 14, "bold"), fg="#1a73e8").pack(pady=12)

    def _build_ui(self):
        # ── 左侧：预览 + 信息 ──
        left = tk.Frame(self, width=320)
        left.pack(side="left", fill="y", padx=(16, 0), pady=16)
        left.pack_propagate(False)

        tk.Label(left, text="App 图标生成器",
                 font=("Microsoft YaHei", 16, "bold")).pack(anchor="w")
        tk.Label(left, text="一张图 → 全套 iOS/Android/Web 图标",
                 font=("Microsoft YaHei", 9), fg="#888").pack(anchor="w", pady=(0, 12))

        # 选择图片按钮
        tk.Button(left, text="选择源图片",
                  font=("Microsoft YaHei", 11),
                  command=self._select_image).pack(fill="x", pady=(0, 8))

        # 预览区
        preview_frame = tk.Frame(left, width=280, height=280,
                                 bg="#f0f0f0", relief="sunken", bd=1)
        preview_frame.pack(pady=(0, 8))
        preview_frame.pack_propagate(False)

        self._preview_label = tk.Label(preview_frame, bg="#f0f0f0",
                                       text="暂无图片\n\n建议使用正方形\n1024x1024 以上的图片",
                                       font=("Microsoft YaHei", 10),
                                       fg="#aaa", justify="center")
        self._preview_label.pack(expand=True)

        # 图片信息
        self._info_label = tk.Label(left, text="",
                                    font=("Microsoft YaHei", 9), fg="#666")
        self._info_label.pack(anchor="w")

        # 圆角预览
        self._preview_row = tk.Frame(left)
        self._preview_row.pack(fill="x", pady=(12, 0))

        tk.Label(self._preview_row, text="预览：",
                 font=("Microsoft YaHei", 9), fg="#666").pack(side="left")

        self._mini_previews = []
        for size_label in ["180px", "120px", "80px", "60px", "40px"]:
            f = tk.Frame(self._preview_row)
            f.pack(side="left", padx=2)
            lbl = tk.Label(f, bg="#f0f0f0", relief="solid", bd=1)
            lbl.pack()
            tk.Label(f, text=size_label, font=("Microsoft YaHei", 7),
                     fg="#aaa").pack()
            self._mini_previews.append(lbl)

        # ── 右侧：设置 ──
        right = tk.Frame(self)
        right.pack(side="right", fill="both", expand=True,
                   padx=16, pady=16)

        # 平台选择
        plat_frame = tk.LabelFrame(right, text=" 导出平台 ",
                                   font=("Microsoft YaHei", 10, "bold"))
        plat_frame.pack(fill="x", pady=(0, 12))

        self._ios_var = tk.BooleanVar(value=True)
        self._android_var = tk.BooleanVar(value=True)
        self._web_var = tk.BooleanVar(value=False)

        ios_row = tk.Frame(plat_frame)
        ios_row.pack(fill="x", padx=10, pady=(6, 2))
        tk.Checkbutton(ios_row, text="iOS",
                       variable=self._ios_var,
                       font=("Microsoft YaHei", 10, "bold")).pack(side="left")
        tk.Label(ios_row, text=f"（{len(IOS_SIZES)} 个尺寸，含 App Store 1024px）",
                 font=("Microsoft YaHei", 9), fg="#888").pack(side="left")

        android_row = tk.Frame(plat_frame)
        android_row.pack(fill="x", padx=10, pady=2)
        tk.Checkbutton(android_row, text="Android",
                       variable=self._android_var,
                       font=("Microsoft YaHei", 10, "bold")).pack(side="left")
        tk.Label(android_row, text=f"（{len(ANDROID_SIZES)} 个尺寸，含 Google Play 512px）",
                 font=("Microsoft YaHei", 9), fg="#888").pack(side="left")

        web_row = tk.Frame(plat_frame)
        web_row.pack(fill="x", padx=10, pady=(2, 6))
        tk.Checkbutton(web_row, text="Web / PWA",
                       variable=self._web_var,
                       font=("Microsoft YaHei", 10, "bold")).pack(side="left")
        tk.Label(web_row, text=f"（{len(WEB_SIZES)} 个尺寸，favicon + PWA 图标）",
                 font=("Microsoft YaHei", 9), fg="#888").pack(side="left")

        # 圆角设置
        round_frame = tk.LabelFrame(right, text=" iOS 圆角 ",
                                    font=("Microsoft YaHei", 10, "bold"))
        round_frame.pack(fill="x", pady=(0, 12))

        r1 = tk.Frame(round_frame)
        r1.pack(fill="x", padx=10, pady=(6, 2))
        self._round_var = tk.BooleanVar(value=True)
        tk.Checkbutton(r1, text="iOS 图标加圆角",
                       variable=self._round_var,
                       font=("Microsoft YaHei", 10),
                       command=self._update_mini_previews).pack(side="left")

        r2 = tk.Frame(round_frame)
        r2.pack(fill="x", padx=10, pady=(2, 6))
        tk.Label(r2, text="圆角比例：",
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self._radius_var = tk.DoubleVar(value=0.22)
        radius_scale = ttk.Scale(r2, from_=0.05, to=0.40,
                                 variable=self._radius_var, length=180,
                                 command=lambda v: self._update_mini_previews())
        radius_scale.pack(side="left", padx=4)
        self._radius_label = tk.Label(r2, text="22%",
                                      font=("Microsoft YaHei", 9), fg="#666")
        self._radius_label.pack(side="left")

        # 尺寸清单
        list_frame = tk.LabelFrame(right, text=" 将生成以下图标 ",
                                   font=("Microsoft YaHei", 10, "bold"))
        list_frame.pack(fill="both", expand=True, pady=(0, 12))

        self._size_text = tk.Text(list_frame, font=("Consolas", 9),
                                  height=8, state="disabled", bg="#fafafa",
                                  wrap="word")
        self._size_text.pack(fill="both", expand=True, padx=6, pady=6)

        self._update_size_list()

        # 绑定平台勾选事件
        self._ios_var.trace_add("write", lambda *a: self._update_size_list())
        self._android_var.trace_add("write", lambda *a: self._update_size_list())
        self._web_var.trace_add("write", lambda *a: self._update_size_list())

        # 进度条
        self._progress = ttk.Progressbar(right, mode="determinate")
        self._progress.pack(fill="x", pady=(0, 8))

        # 生成按钮
        tk.Button(right, text="选择输出文件夹并生成",
                  font=("Microsoft YaHei", 13, "bold"),
                  command=self._generate).pack(fill="x")

    def _select_image(self):
        path = filedialog.askopenfilename(
            title="选择源图片（建议 1024x1024 以上）",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.webp *.tiff")])
        if not path:
            return

        try:
            self._source_img = Image.open(path)
        except Exception as e:
            messagebox.showerror("打开失败", str(e))
            return

        w, h = self._source_img.size
        is_square = "正方形" if w == h else "非正方形（将自动居中裁剪）"
        warn = ""
        if max(w, h) < 1024:
            warn = "\n\u26a0 建议使用 1024px 以上的图片以保证清晰度"
        self._info_label.configure(
            text=f"尺寸：{w} x {h} px    {is_square}{warn}")

        # 主预览
        preview = self._source_img.copy()
        preview.thumbnail((270, 270), Image.LANCZOS)
        self._preview_photo = ImageTk.PhotoImage(preview)
        self._preview_label.configure(image=self._preview_photo, text="")

        self._update_mini_previews()

    def _update_mini_previews(self, *args):
        if self._source_img is None:
            return

        # 更新圆角百分比标签
        ratio = self._radius_var.get()
        self._radius_label.configure(text=f"{int(ratio * 100)}%")

        img = self._source_img.convert("RGBA")
        w, h = img.size
        if w != h:
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            img = img.crop((left, top, left + side, top + side))

        rounded = self._round_var.get()
        display_sizes = [50, 40, 32, 24, 18]

        self._mini_photos = []
        for i, size in enumerate(display_sizes):
            small = img.resize((size, size), Image.LANCZOS)
            if rounded:
                small = add_rounded_corners(small, ratio)
            # 放到白色背景上
            bg = Image.new("RGBA", (size, size), (240, 240, 240, 255))
            bg.paste(small, (0, 0), small)
            photo = ImageTk.PhotoImage(bg)
            self._mini_photos.append(photo)
            self._mini_previews[i].configure(image=photo)

    def _update_size_list(self):
        lines = []
        total = 0

        if self._ios_var.get():
            lines.append("【iOS】")
            for name, size in IOS_SIZES:
                lines.append(f"  {size:>4}x{size:<4}  {name}")
            total += len(IOS_SIZES)
            lines.append("")

        if self._android_var.get():
            lines.append("【Android】")
            for name, size in ANDROID_SIZES:
                lines.append(f"  {size:>4}x{size:<4}  {name}")
            total += len(ANDROID_SIZES)
            lines.append("")

        if self._web_var.get():
            lines.append("【Web / PWA】")
            for name, size in WEB_SIZES:
                lines.append(f"  {size:>4}x{size:<4}  {name}")
            total += len(WEB_SIZES)

        if not lines:
            lines.append("请至少勾选一个平台")

        lines.append(f"\n共 {total} 个图标文件")

        self._size_text.configure(state="normal")
        self._size_text.delete("1.0", "end")
        self._size_text.insert("1.0", "\n".join(lines))
        self._size_text.configure(state="disabled")

    def _generate(self):
        if self._source_img is None:
            messagebox.showwarning("提示", "请先选择源图片")
            return

        platforms = {
            "ios": self._ios_var.get(),
            "android": self._android_var.get(),
            "web": self._web_var.get(),
        }
        if not any(platforms.values()):
            messagebox.showwarning("提示", "请至少勾选一个导出平台")
            return

        output_dir = filedialog.askdirectory(title="选择图标输出文件夹")
        if not output_dir:
            return

        # 计算总数
        total = 0
        if platforms["ios"]:
            total += len(IOS_SIZES)
        if platforms["android"]:
            total += len(ANDROID_SIZES)
        if platforms["web"]:
            total += len(WEB_SIZES)

        self._progress["maximum"] = total
        self._progress["value"] = 0

        def on_progress(current, total_n):
            self._progress["value"] = current
            self.update_idletasks()

        try:
            count = generate_icons(
                self._source_img, output_dir, platforms,
                rounded=self._round_var.get(),
                radius_ratio=self._radius_var.get(),
                progress_callback=on_progress)

            messagebox.showinfo("生成完成",
                                f"已生成 {count} 个图标文件\n\n"
                                f"输出目录：\n{output_dir}")

            # 打开输出文件夹
            os.startfile(output_dir)

        except Exception as e:
            messagebox.showerror("生成失败", str(e))
        finally:
            self._progress["value"] = 0


if __name__ == "__main__":
    app = IconGeneratorApp()
    app.mainloop()
