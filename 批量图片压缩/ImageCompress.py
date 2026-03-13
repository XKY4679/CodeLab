"""
批量图片压缩工具 1.0 —— GUI 图形窗口版
支持 PNG / JPG / WebP 批量压缩
质量预设 / 指定目标大小 / 按比例缩放
压缩前后大小对比
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ── 配置 ────────────────────────────────────────────
WINDOW_WIDTH = 780
WINDOW_HEIGHT = 600
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

QUALITY_PRESETS = {
    "高质量（体积较大）": 90,
    "均衡（推荐）": 70,
    "小体积（画质有损）": 45,
}


def format_size(b):
    if b < 1024:
        return f"{b} B"
    elif b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    else:
        return f"{b / (1024 * 1024):.2f} MB"


def scan_images(folder):
    imgs = []
    for f in sorted(os.listdir(folder)):
        full = os.path.join(folder, f)
        if os.path.isfile(full) and os.path.splitext(f)[1].lower() in IMAGE_EXTS:
            imgs.append(full)
    return imgs


def compress_image(src, dst, quality=70, max_size_kb=None, scale=None):
    """
    压缩单张图片。
    quality: JPEG/WebP 质量 1-100，PNG 会自动优化。
    max_size_kb: 如果指定，则反复降低质量直到文件 ≤ 目标大小。
    scale: 0-100 缩放百分比，None 表示不缩放。
    """
    img = Image.open(src)

    # RGBA → RGB（JPEG 不支持透明通道）
    if img.mode in ("RGBA", "P") and dst.lower().endswith((".jpg", ".jpeg")):
        img = img.convert("RGB")

    # 缩放
    if scale and 0 < scale < 100:
        w, h = img.size
        new_w = max(1, int(w * scale / 100))
        new_h = max(1, int(h * scale / 100))
        img = img.resize((new_w, new_h), Image.LANCZOS)

    ext = os.path.splitext(dst)[1].lower()

    if max_size_kb:
        # 逐步降低质量逼近目标大小
        q = 95
        while q >= 10:
            _save(img, dst, ext, q)
            if os.path.getsize(dst) <= max_size_kb * 1024:
                return
            q -= 5
        # 最低质量还是超了，就这样了
    else:
        _save(img, dst, ext, quality)


def _save(img, path, ext, quality):
    if ext == ".png":
        img.save(path, "PNG", optimize=True)
    elif ext == ".webp":
        img.save(path, "WEBP", quality=quality)
    else:
        img.save(path, "JPEG", quality=quality, optimize=True)


# ── GUI ─────────────────────────────────────────────


class ImageCompressApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("批量图片压缩工具 1.0")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)

        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        if not HAS_PIL:
            self._show_dep_error()
        else:
            self._show_start_page()

    def _clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    # ── 依赖缺失 ────────────────────────────────────

    def _show_dep_error(self):
        self._clear()
        f = tk.Frame(self.container)
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="缺少依赖库", font=("Microsoft YaHei", 20, "bold"), fg="#c62828").pack(pady=(0, 12))
        tk.Label(f, text="请在命令行中运行：", font=("Microsoft YaHei", 11)).pack()
        tk.Label(f, text="pip install Pillow", font=("Consolas", 14, "bold"), fg="#1a73e8").pack(pady=12)

    # ── 开始页面 ─────────────────────────────────────

    def _show_start_page(self):
        self._clear()
        f = tk.Frame(self.container)
        f.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(f, text="批量图片压缩工具", font=("Microsoft YaHei", 24, "bold")).pack(pady=(0, 6))
        tk.Label(f, text="支持 PNG / JPG / WebP / BMP 批量压缩",
                 font=("Microsoft YaHei", 10), fg="#666").pack(pady=(0, 30))

        tk.Button(f, text="选择图片文件夹", font=("Microsoft YaHei", 13),
                  width=20, height=2, command=self._on_select).pack(pady=6)

        tk.Label(f, text="压缩后保存到\"压缩输出\"子文件夹，不覆盖原文件",
                 font=("Microsoft YaHei", 9), fg="#999").pack(pady=(10, 0))

    def _on_select(self):
        folder = filedialog.askdirectory(title="选择图片文件夹")
        if not folder:
            return
        imgs = scan_images(folder)
        if not imgs:
            messagebox.showwarning("提示", "文件夹中没有找到图片文件。")
            return
        self._folder = folder
        self._images = imgs
        self._show_settings()

    # ── 设置页面 ─────────────────────────────────────

    def _show_settings(self):
        self._clear()
        num = len(self._images)

        top = tk.Frame(self.container)
        top.pack(fill="x", padx=20, pady=(15, 5))
        tk.Button(top, text="← 返回", font=("Microsoft YaHei", 10), command=self._show_start_page).pack(side="left")
        tk.Label(top, text="压缩设置", font=("Microsoft YaHei", 14, "bold")).pack(side="left", padx=15)

        body = tk.Frame(self.container)
        body.pack(fill="both", expand=True, padx=25, pady=10)

        tk.Label(body, text=f"已选择：{self._folder}", font=("Microsoft YaHei", 10), fg="#555").pack(anchor="w")
        tk.Label(body, text=f"共 {num} 张图片", font=("Microsoft YaHei", 11, "bold")).pack(anchor="w", pady=(2, 12))

        # 文件预览
        lb = tk.Listbox(body, height=min(5, num), font=("Microsoft YaHei", 9))
        for v in self._images:
            s = os.path.getsize(v)
            lb.insert("end", f"  {os.path.basename(v)}    ({format_size(s)})")
        lb.pack(fill="x", pady=(0, 10))

        # 模式选择
        tk.Label(body, text="压缩模式：", font=("Microsoft YaHei", 11, "bold")).pack(anchor="w", pady=(5, 5))

        self._mode = tk.StringVar(value="preset")

        # 质量预设
        r1 = tk.Frame(body)
        r1.pack(fill="x", pady=2)
        tk.Radiobutton(r1, text="质量预设", variable=self._mode, value="preset",
                       font=("Microsoft YaHei", 10), command=self._on_mode).pack(side="left")
        self._preset_var = tk.StringVar(value="均衡（推荐）")
        self._preset_cb = ttk.Combobox(r1, textvariable=self._preset_var,
                                       values=list(QUALITY_PRESETS.keys()), state="readonly", width=22)
        self._preset_cb.pack(side="left", padx=10)

        # 目标大小
        r2 = tk.Frame(body)
        r2.pack(fill="x", pady=2)
        tk.Radiobutton(r2, text="指定目标大小", variable=self._mode, value="target",
                       font=("Microsoft YaHei", 10), command=self._on_mode).pack(side="left")
        self._target_var = tk.StringVar(value="500")
        self._target_entry = tk.Entry(r2, textvariable=self._target_var, width=8, font=("Microsoft YaHei", 10))
        self._target_entry.pack(side="left", padx=10)
        self._target_entry.config(state="disabled")
        tk.Label(r2, text="KB（每张压到约这个大小）", font=("Microsoft YaHei", 9), fg="#888").pack(side="left")

        # 缩放选项
        r3 = tk.Frame(body)
        r3.pack(fill="x", pady=(10, 0))
        self._scale_enabled = tk.BooleanVar(value=False)
        tk.Checkbutton(r3, text="同时缩小尺寸", variable=self._scale_enabled,
                       font=("Microsoft YaHei", 10), command=self._on_mode).pack(side="left")
        self._scale_var = tk.StringVar(value="50")
        self._scale_entry = tk.Entry(r3, textvariable=self._scale_var, width=5, font=("Microsoft YaHei", 10))
        self._scale_entry.pack(side="left", padx=10)
        self._scale_entry.config(state="disabled")
        tk.Label(r3, text="% （如 50 表示缩到原尺寸一半）", font=("Microsoft YaHei", 9), fg="#888").pack(side="left")

        # 开始
        tk.Button(body, text="开始压缩", font=("Microsoft YaHei", 13, "bold"),
                  width=16, height=2, command=self._start).pack(pady=(18, 0))

    def _on_mode(self):
        m = self._mode.get()
        self._preset_cb.config(state="readonly" if m == "preset" else "disabled")
        self._target_entry.config(state="normal" if m == "target" else "disabled")
        self._scale_entry.config(state="normal" if self._scale_enabled.get() else "disabled")

    # ── 压缩执行 ─────────────────────────────────────

    def _start(self):
        mode = self._mode.get()
        if mode == "target":
            try:
                self._target_kb = float(self._target_var.get())
                if self._target_kb <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("提示", "请输入有效的目标大小。")
                return
            self._quality = None
        else:
            self._quality = QUALITY_PRESETS[self._preset_var.get()]
            self._target_kb = None

        self._scale = None
        if self._scale_enabled.get():
            try:
                self._scale = int(self._scale_var.get())
                if self._scale <= 0 or self._scale >= 100:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("提示", "缩放比例请输入 1-99。")
                return

        self._out_folder = os.path.join(self._folder, "压缩输出")
        os.makedirs(self._out_folder, exist_ok=True)

        self._show_progress()
        threading.Thread(target=self._worker, daemon=True).start()

    def _show_progress(self):
        self._clear()

        top = tk.Frame(self.container)
        top.pack(fill="x", padx=20, pady=(15, 5))
        tk.Label(top, text="正在压缩...", font=("Microsoft YaHei", 14, "bold")).pack(side="left")

        body = tk.Frame(self.container)
        body.pack(fill="both", expand=True, padx=20, pady=10)

        self._prog_label = tk.Label(body, text="准备中...", font=("Microsoft YaHei", 11))
        self._prog_label.pack(anchor="w", pady=(0, 3))
        self._prog_bar = ttk.Progressbar(body, length=WINDOW_WIDTH - 50, maximum=len(self._images))
        self._prog_bar.pack(fill="x", pady=(0, 10))
        self._cur_label = tk.Label(body, text="", font=("Microsoft YaHei", 10), fg="#555")
        self._cur_label.pack(anchor="w", pady=(0, 8))

        cols = ("name", "orig", "comp", "ratio", "status")
        self._tree = ttk.Treeview(body, columns=cols, show="headings", height=14)
        self._tree.heading("name", text="文件名")
        self._tree.heading("orig", text="原始大小")
        self._tree.heading("comp", text="压缩后")
        self._tree.heading("ratio", text="节省")
        self._tree.heading("status", text="状态")
        self._tree.column("name", width=260)
        self._tree.column("orig", width=100, anchor="center")
        self._tree.column("comp", width=100, anchor="center")
        self._tree.column("ratio", width=80, anchor="center")
        self._tree.column("status", width=100, anchor="center")
        sb = ttk.Scrollbar(body, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._iids = {}
        for v in self._images:
            name = os.path.basename(v)
            iid = self._tree.insert("", "end", values=(name, format_size(os.path.getsize(v)), "—", "—", "等待"))
            self._iids[v] = iid

    def _update_row(self, path, comp_str, ratio_str, status):
        iid = self._iids.get(path)
        if iid:
            cur = self._tree.item(iid, "values")
            self._tree.item(iid, values=(cur[0], cur[1], comp_str, ratio_str, status))

    def _worker(self):
        results = []
        total = len(self._images)

        for idx, src in enumerate(self._images):
            name = os.path.basename(src)
            dst = os.path.join(self._out_folder, name)
            orig = os.path.getsize(src)

            self.after(0, lambda i=idx, n=name: (
                self._prog_label.config(text=f"进度：{i+1} / {total}"),
                self._prog_bar.config(value=i),
                self._cur_label.config(text=f"正在处理：{n}"),
            ))
            self.after(0, lambda p=src: self._update_row(p, "...", "...", "压缩中"))

            try:
                compress_image(src, dst, quality=self._quality or 70,
                               max_size_kb=self._target_kb, scale=self._scale)
                ns = os.path.getsize(dst)
                saved = (1 - ns / orig) * 100 if orig > 0 else 0
                r = f"-{saved:.1f}%"
                self.after(0, lambda p=src, n2=ns, r2=r: self._update_row(p, format_size(n2), r2, "完成"))
                results.append((name, orig, ns, True))
            except Exception as e:
                if os.path.exists(dst):
                    try:
                        os.remove(dst)
                    except OSError:
                        pass
                self.after(0, lambda p=src: self._update_row(p, "—", "—", "失败"))
                results.append((name, orig, 0, False))

        self.after(0, lambda: self._done(results))

    def _done(self, results):
        self._prog_bar["value"] = self._prog_bar["maximum"]
        self._prog_label.config(text=f"全部完成 ({len(results)} 张)")
        self._cur_label.config(text="")

        total_orig = sum(r[1] for r in results)
        total_new = sum(r[2] for r in results if r[3])
        ok = sum(1 for r in results if r[3])
        fail = sum(1 for r in results if not r[3])

        bar = tk.Frame(self.container, bg="#f0f0f0", relief="groove", bd=1)
        bar.pack(fill="x", padx=15, pady=(0, 12))

        left = tk.Frame(bar, bg="#f0f0f0")
        left.pack(side="left", padx=15, pady=10)
        saved = (1 - total_new / total_orig) * 100 if total_orig > 0 else 0
        tk.Label(left, text=f"总计：{format_size(total_orig)} → {format_size(total_new)}  |  节省 {saved:.1f}%",
                 font=("Microsoft YaHei", 10, "bold"), bg="#f0f0f0").pack(anchor="w")
        st = f"成功 {ok} 张"
        if fail:
            st += f"，失败 {fail} 张"
        tk.Label(left, text=st, font=("Microsoft YaHei", 9), fg="#666", bg="#f0f0f0").pack(anchor="w")

        right = tk.Frame(bar, bg="#f0f0f0")
        right.pack(side="right", padx=15, pady=10)
        tk.Button(right, text="打开输出文件夹", font=("Microsoft YaHei", 10),
                  command=lambda: os.startfile(self._out_folder)).pack(side="left", padx=4)
        tk.Button(right, text="返回首页", font=("Microsoft YaHei", 10),
                  command=self._show_start_page).pack(side="left", padx=4)


if __name__ == "__main__":
    app = ImageCompressApp()
    app.mainloop()
