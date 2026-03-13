"""
批量加水印工具 1.0 —— GUI 图形窗口版
支持文字水印 / 图片水印，可调位置、透明度、大小
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import os
import threading

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

WINDOW_WIDTH = 760
WINDOW_HEIGHT = 600
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

POSITION_MAP = {
    "左上角": "top_left",
    "右上角": "top_right",
    "左下角": "bottom_left",
    "右下角": "bottom_right",
    "居中": "center",
    "平铺（满屏重复）": "tile",
}


def format_size(b):
    if b < 1024:
        return f"{b} B"
    elif b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b / (1024 * 1024):.2f} MB"


def scan_images(folder):
    imgs = []
    for f in sorted(os.listdir(folder)):
        full = os.path.join(folder, f)
        if os.path.isfile(full) and os.path.splitext(f)[1].lower() in IMAGE_EXTS:
            imgs.append(full)
    return imgs


def _get_font(size):
    """尝试加载中文字体，失败则用默认"""
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",    # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",   # 黑体
        "C:/Windows/Fonts/simsun.ttc",   # 宋体
        "C:/Windows/Fonts/arial.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _calc_position(img_w, img_h, wm_w, wm_h, pos, margin=20):
    """根据位置名计算左上角坐标"""
    if pos == "top_left":
        return margin, margin
    elif pos == "top_right":
        return img_w - wm_w - margin, margin
    elif pos == "bottom_left":
        return margin, img_h - wm_h - margin
    elif pos == "bottom_right":
        return img_w - wm_w - margin, img_h - wm_h - margin
    elif pos == "center":
        return (img_w - wm_w) // 2, (img_h - wm_h) // 2
    return margin, margin


def add_text_watermark(src, dst, text, font_size=40, opacity=80,
                       position="bottom_right", color=(255, 255, 255)):
    """给图片添加文字水印"""
    img = Image.open(src).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = _get_font(font_size)
    alpha = int(255 * opacity / 100)

    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    pos_key = POSITION_MAP.get(position, "bottom_right")
    fill = (color[0], color[1], color[2], alpha)

    if pos_key == "tile":
        spacing_x = tw + max(60, tw // 2)
        spacing_y = th + max(60, th)
        y = 0
        while y < img.size[1] + spacing_y:
            x = 0
            while x < img.size[0] + spacing_x:
                draw.text((x, y), text, font=font, fill=fill)
                x += spacing_x
            y += spacing_y
    else:
        x, y = _calc_position(img.size[0], img.size[1], tw, th, pos_key)
        draw.text((x, y), text, font=font, fill=fill)

    result = Image.alpha_composite(img, overlay)
    # 保存为原格式
    ext = os.path.splitext(dst)[1].lower()
    if ext in (".jpg", ".jpeg"):
        result = result.convert("RGB")
        result.save(dst, "JPEG", quality=95)
    elif ext == ".webp":
        result.save(dst, "WEBP", quality=95)
    elif ext == ".bmp":
        result = result.convert("RGB")
        result.save(dst, "BMP")
    else:
        result.save(dst, "PNG")


def add_image_watermark(src, dst, wm_path, scale_pct=20, opacity=80,
                        position="bottom_right"):
    """给图片添加图片水印"""
    img = Image.open(src).convert("RGBA")
    wm = Image.open(wm_path).convert("RGBA")

    # 缩放水印
    wm_w = max(1, int(img.size[0] * scale_pct / 100))
    wm_h = max(1, int(wm_w * wm.size[1] / wm.size[0]))
    wm = wm.resize((wm_w, wm_h), Image.LANCZOS)

    # 调整透明度
    alpha = wm.split()[3]
    alpha = alpha.point(lambda p: int(p * opacity / 100))
    wm.putalpha(alpha)

    pos_key = POSITION_MAP.get(position, "bottom_right")

    if pos_key == "tile":
        spacing_x = wm_w + max(40, wm_w // 2)
        spacing_y = wm_h + max(40, wm_h // 2)
        y = 0
        while y < img.size[1] + spacing_y:
            x = 0
            while x < img.size[0] + spacing_x:
                img.paste(wm, (x, y), wm)
                x += spacing_x
            y += spacing_y
    else:
        x, y = _calc_position(img.size[0], img.size[1], wm_w, wm_h, pos_key)
        img.paste(wm, (x, y), wm)

    ext = os.path.splitext(dst)[1].lower()
    if ext in (".jpg", ".jpeg"):
        img = img.convert("RGB")
        img.save(dst, "JPEG", quality=95)
    elif ext == ".webp":
        img.save(dst, "WEBP", quality=95)
    elif ext == ".bmp":
        img = img.convert("RGB")
        img.save(dst, "BMP")
    else:
        img.save(dst, "PNG")


# ── GUI ─────────────────────────────────────────────

class WatermarkApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("批量加水印工具 1.0")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

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
        tk.Label(f, text="批量加水印工具", font=("Microsoft YaHei", 24, "bold")).pack(pady=(0, 6))
        tk.Label(f, text="给图片批量添加文字水印或图片水印", font=("Microsoft YaHei", 10), fg="#666").pack(pady=(0, 35))

        tk.Button(f, text="文字水印", font=("Microsoft YaHei", 13), width=20, height=2,
                  command=self._show_text_wm).pack(pady=6)
        tk.Label(f, text="在图片上打上自定义文字", font=("Microsoft YaHei", 9), fg="#999").pack(pady=(0, 16))

        tk.Button(f, text="图片水印", font=("Microsoft YaHei", 13), width=20, height=2,
                  command=self._show_img_wm).pack(pady=6)
        tk.Label(f, text="用你的 LOGO 图片作为水印", font=("Microsoft YaHei", 9), fg="#999").pack()

    # ── 文字水印设置 ─────────────────────────────────

    def _show_text_wm(self):
        self._clear()
        self._wm_color = (255, 255, 255)

        top = tk.Frame(self.container); top.pack(fill="x", padx=20, pady=(15, 5))
        tk.Button(top, text="← 返回", font=("Microsoft YaHei", 10), command=self._show_start).pack(side="left")
        tk.Label(top, text="文字水印设置", font=("Microsoft YaHei", 14, "bold")).pack(side="left", padx=15)

        body = tk.Frame(self.container); body.pack(fill="both", expand=True, padx=25, pady=10)

        # 选择文件夹
        tk.Label(body, text="图片文件夹：", font=("Microsoft YaHei", 10)).pack(anchor="w", pady=(0, 3))
        row0 = tk.Frame(body); row0.pack(fill="x")
        self._folder_label = tk.Label(row0, text="未选择", font=("Microsoft YaHei", 10), fg="#999")
        self._folder_label.pack(side="left", fill="x", expand=True)
        tk.Button(row0, text="选择文件夹", font=("Microsoft YaHei", 10), command=self._pick_folder).pack(side="right")

        # 水印文字
        tk.Label(body, text="水印文字：", font=("Microsoft YaHei", 10)).pack(anchor="w", pady=(12, 3))
        self._text_var = tk.StringVar(value="Sample Watermark")
        tk.Entry(body, textvariable=self._text_var, font=("Microsoft YaHei", 11), width=40).pack(anchor="w")

        # 参数行
        params = tk.Frame(body); params.pack(fill="x", pady=(12, 0))

        tk.Label(params, text="字号：", font=("Microsoft YaHei", 10)).pack(side="left")
        self._fontsize_var = tk.IntVar(value=40)
        tk.Spinbox(params, from_=10, to=200, textvariable=self._fontsize_var, width=5, font=("Microsoft YaHei", 10)).pack(side="left", padx=(0, 15))

        tk.Label(params, text="透明度：", font=("Microsoft YaHei", 10)).pack(side="left")
        self._opacity_var = tk.IntVar(value=60)
        tk.Scale(params, from_=10, to=100, orient="horizontal", variable=self._opacity_var, length=120).pack(side="left", padx=(0, 15))

        self._color_btn = tk.Button(params, text="  颜色  ", font=("Microsoft YaHei", 10), bg="white",
                                    command=self._pick_color)
        self._color_btn.pack(side="left")

        # 位置
        tk.Label(body, text="位置：", font=("Microsoft YaHei", 10)).pack(anchor="w", pady=(12, 3))
        self._pos_var = tk.StringVar(value="右下角")
        pos_frame = tk.Frame(body); pos_frame.pack(fill="x")
        for p in POSITION_MAP:
            tk.Radiobutton(pos_frame, text=p, variable=self._pos_var, value=p,
                           font=("Microsoft YaHei", 9)).pack(side="left", padx=4)

        # 开始
        self._start_btn = tk.Button(body, text="开始加水印", font=("Microsoft YaHei", 13, "bold"),
                                    width=16, height=2, command=self._do_text_wm, state="disabled")
        self._start_btn.pack(pady=(20, 0))

    def _pick_folder(self):
        folder = filedialog.askdirectory(title="选择图片文件夹")
        if not folder:
            return
        imgs = scan_images(folder)
        if not imgs:
            messagebox.showwarning("提示", "文件夹中没有图片。"); return
        self._folder = folder
        self._images = imgs
        self._folder_label.config(text=f"{folder}  ({len(imgs)} 张)", fg="#333")
        self._start_btn.config(state="normal")

    def _pick_color(self):
        color = colorchooser.askcolor(initialcolor=self._wm_color, title="选择水印颜色")
        if color[0]:
            self._wm_color = tuple(int(c) for c in color[0])
            hex_color = color[1]
            self._color_btn.config(bg=hex_color)

    def _do_text_wm(self):
        text = self._text_var.get().strip()
        if not text:
            messagebox.showwarning("提示", "请输入水印文字。"); return

        out = os.path.join(self._folder, "水印输出")
        os.makedirs(out, exist_ok=True)
        self._out_folder = out

        params = dict(text=text, font_size=self._fontsize_var.get(),
                      opacity=self._opacity_var.get(), position=self._pos_var.get(),
                      color=self._wm_color)
        self._show_progress("文字水印")
        threading.Thread(target=self._text_worker, args=(params,), daemon=True).start()

    def _text_worker(self, params):
        ok, fail = 0, 0
        total = len(self._images)
        for i, src in enumerate(self._images):
            name = os.path.basename(src)
            dst = os.path.join(self._out_folder, name)
            self.after(0, lambda idx=i, n=name: (
                self._prog_label.config(text=f"进度：{idx+1} / {total}"),
                self._prog_bar.config(value=idx+1),
            ))
            try:
                add_text_watermark(src, dst, **params)
                ok += 1
            except Exception:
                fail += 1
        self.after(0, lambda: self._done(ok, fail))

    # ── 图片水印设置 ─────────────────────────────────

    def _show_img_wm(self):
        self._clear()
        self._wm_image_path = None

        top = tk.Frame(self.container); top.pack(fill="x", padx=20, pady=(15, 5))
        tk.Button(top, text="← 返回", font=("Microsoft YaHei", 10), command=self._show_start).pack(side="left")
        tk.Label(top, text="图片水印设置", font=("Microsoft YaHei", 14, "bold")).pack(side="left", padx=15)

        body = tk.Frame(self.container); body.pack(fill="both", expand=True, padx=25, pady=10)

        # 选择图片文件夹
        tk.Label(body, text="图片文件夹：", font=("Microsoft YaHei", 10)).pack(anchor="w", pady=(0, 3))
        row0 = tk.Frame(body); row0.pack(fill="x")
        self._folder_label = tk.Label(row0, text="未选择", font=("Microsoft YaHei", 10), fg="#999")
        self._folder_label.pack(side="left", fill="x", expand=True)
        tk.Button(row0, text="选择文件夹", font=("Microsoft YaHei", 10), command=self._pick_folder).pack(side="right")

        # 水印图片
        tk.Label(body, text="水印图片（建议用 PNG 透明底）：", font=("Microsoft YaHei", 10)).pack(anchor="w", pady=(12, 3))
        row1 = tk.Frame(body); row1.pack(fill="x")
        self._wm_img_label = tk.Label(row1, text="未选择", font=("Microsoft YaHei", 10), fg="#999")
        self._wm_img_label.pack(side="left", fill="x", expand=True)
        tk.Button(row1, text="选择图片", font=("Microsoft YaHei", 10), command=self._pick_wm_img).pack(side="right")

        # 参数
        params = tk.Frame(body); params.pack(fill="x", pady=(12, 0))
        tk.Label(params, text="水印大小（占图片宽度%）：", font=("Microsoft YaHei", 10)).pack(side="left")
        self._scale_var = tk.IntVar(value=20)
        tk.Scale(params, from_=5, to=80, orient="horizontal", variable=self._scale_var, length=150).pack(side="left", padx=(0, 15))

        tk.Label(params, text="透明度：", font=("Microsoft YaHei", 10)).pack(side="left")
        self._opacity_var = tk.IntVar(value=60)
        tk.Scale(params, from_=10, to=100, orient="horizontal", variable=self._opacity_var, length=120).pack(side="left")

        # 位置
        tk.Label(body, text="位置：", font=("Microsoft YaHei", 10)).pack(anchor="w", pady=(12, 3))
        self._pos_var = tk.StringVar(value="右下角")
        pos_frame = tk.Frame(body); pos_frame.pack(fill="x")
        for p in POSITION_MAP:
            tk.Radiobutton(pos_frame, text=p, variable=self._pos_var, value=p,
                           font=("Microsoft YaHei", 9)).pack(side="left", padx=4)

        self._start_btn = tk.Button(body, text="开始加水印", font=("Microsoft YaHei", 13, "bold"),
                                    width=16, height=2, command=self._do_img_wm, state="disabled")
        self._start_btn.pack(pady=(20, 0))

    def _pick_wm_img(self):
        path = filedialog.askopenfilename(title="选择水印图片",
                                          filetypes=[("图片", "*.png *.jpg *.jpeg *.webp *.bmp")])
        if path:
            self._wm_image_path = path
            self._wm_img_label.config(text=os.path.basename(path), fg="#333")
            if hasattr(self, "_images") and self._images:
                self._start_btn.config(state="normal")

    def _do_img_wm(self):
        if not self._wm_image_path:
            messagebox.showwarning("提示", "请选择水印图片。"); return

        out = os.path.join(self._folder, "水印输出")
        os.makedirs(out, exist_ok=True)
        self._out_folder = out

        params = dict(wm_path=self._wm_image_path, scale_pct=self._scale_var.get(),
                      opacity=self._opacity_var.get(), position=self._pos_var.get())
        self._show_progress("图片水印")
        threading.Thread(target=self._img_worker, args=(params,), daemon=True).start()

    def _img_worker(self, params):
        ok, fail = 0, 0
        total = len(self._images)
        for i, src in enumerate(self._images):
            name = os.path.basename(src)
            dst = os.path.join(self._out_folder, name)
            self.after(0, lambda idx=i, n=name: (
                self._prog_label.config(text=f"进度：{idx+1} / {total}"),
                self._prog_bar.config(value=idx+1),
            ))
            try:
                add_image_watermark(src, dst, **params)
                ok += 1
            except Exception:
                fail += 1
        self.after(0, lambda: self._done(ok, fail))

    # ── 进度 & 结果 ──────────────────────────────────

    def _show_progress(self, title):
        self._clear()
        top = tk.Frame(self.container); top.pack(fill="x", padx=20, pady=(15, 10))
        tk.Label(top, text=f"正在添加{title}...", font=("Microsoft YaHei", 14, "bold")).pack(side="left")

        body = tk.Frame(self.container); body.pack(fill="x", padx=25, pady=10)
        self._prog_label = tk.Label(body, text="准备中...", font=("Microsoft YaHei", 11))
        self._prog_label.pack(anchor="w")
        self._prog_bar = ttk.Progressbar(body, length=WINDOW_WIDTH - 60, maximum=len(self._images))
        self._prog_bar.pack(fill="x", pady=(5, 0))

    def _done(self, ok, fail):
        self._clear()
        f = tk.Frame(self.container); f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="加水印完成", font=("Microsoft YaHei", 22, "bold")).pack(pady=(0, 15))
        color = "#2e7d32" if fail == 0 else "#e65100"
        tk.Label(f, text=f"成功 {ok} 张", font=("Microsoft YaHei", 16, "bold"), fg=color).pack()
        if fail:
            tk.Label(f, text=f"失败 {fail} 张", font=("Microsoft YaHei", 12), fg="#c62828").pack(pady=(5, 0))

        btn = tk.Frame(f); btn.pack(pady=20)
        tk.Button(btn, text="打开输出文件夹", font=("Microsoft YaHei", 11), width=14,
                  command=lambda: os.startfile(self._out_folder)).pack(side="left", padx=6)
        tk.Button(btn, text="返回首页", font=("Microsoft YaHei", 11), width=12,
                  command=self._show_start).pack(side="left", padx=6)


if __name__ == "__main__":
    app = WatermarkApp()
    app.mainloop()
