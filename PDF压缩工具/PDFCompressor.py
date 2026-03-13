"""
PDF 压缩工具 —— GUI 图形窗口版
对 PDF 内嵌图片进行智能重压缩
支持四档质量预设 + 自定义参数
批量压缩、实时预览压缩率
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
import io
import time

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# ── 质量预设 ──
PRESETS = {
    "extreme": {"label": "极致压缩", "desc": "最小体积，图片会有可见模糊",
                "quality": 30, "max_dim": 1200, "dpi": 96},
    "standard": {"label": "标准压缩", "desc": "体积与画质均衡（推荐日常用）",
                 "quality": 60, "max_dim": 2000, "dpi": 150},
    "hd": {"label": "高清压缩", "desc": "画质几乎无损，体积也能减不少",
            "quality": 85, "max_dim": 4000, "dpi": 300},
    "lossless": {"label": "仅瘦身", "desc": "不碰图片质量，只清理冗余数据",
                  "quality": 100, "max_dim": 0, "dpi": 0},
}

WINDOW_W = 780
WINDOW_H = 640


def format_size(n):
    if n < 1024:
        return f"{n} B"
    elif n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    else:
        return f"{n / (1024 * 1024):.2f} MB"


class PDFCompressorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF 压缩工具")
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.resizable(False, False)
        self._files = []
        self._working = False

        if not HAS_FITZ or not HAS_PIL:
            self._dep_error()
        else:
            self._build_ui()

    # ── 缺少依赖 ──
    def _dep_error(self):
        f = tk.Frame(self)
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="需要安装依赖",
                 font=("Microsoft YaHei", 18, "bold"),
                 fg="#c62828").pack(pady=(0, 16))
        tk.Label(f, text="pip install PyMuPDF Pillow",
                 font=("Consolas", 14, "bold"), fg="#1a73e8").pack()

    # ── 界面 ──
    def _build_ui(self):
        # 标题
        top = tk.Frame(self)
        top.pack(fill="x", padx=16, pady=(14, 6))
        tk.Label(top, text="PDF 压缩工具",
                 font=("Microsoft YaHei", 16, "bold")).pack(side="left")
        tk.Label(top, text="图片智能重压缩，体积小画质好",
                 font=("Microsoft YaHei", 10), fg="#888").pack(side="left", padx=12)

        # ── 文件列表 ──
        file_frame = tk.LabelFrame(self, text=" 待压缩文件 ",
                                    font=("Microsoft YaHei", 10, "bold"))
        file_frame.pack(fill="x", padx=16, pady=(0, 6))

        btn_row = tk.Frame(file_frame)
        btn_row.pack(fill="x", padx=8, pady=(6, 3))
        tk.Button(btn_row, text="添加 PDF 文件",
                  font=("Microsoft YaHei", 9),
                  command=self._add_files).pack(side="left")
        tk.Button(btn_row, text="添加整个文件夹",
                  font=("Microsoft YaHei", 9),
                  command=self._add_folder).pack(side="left", padx=6)
        tk.Button(btn_row, text="清空列表",
                  font=("Microsoft YaHei", 9),
                  command=self._clear_files).pack(side="left")
        self._file_count_label = tk.Label(
            btn_row, text="0 个文件", font=("Microsoft YaHei", 9), fg="#888")
        self._file_count_label.pack(side="right")

        # 文件列表框
        list_frame = tk.Frame(file_frame)
        list_frame.pack(fill="x", padx=8, pady=(0, 8))
        self._file_listbox = tk.Listbox(
            list_frame, height=4, font=("Consolas", 9),
            selectmode="extended")
        self._file_listbox.pack(side="left", fill="x", expand=True)
        sb = ttk.Scrollbar(list_frame, command=self._file_listbox.yview)
        sb.pack(side="right", fill="y")
        self._file_listbox.configure(yscrollcommand=sb.set)

        # ── 压缩设置（两列）──
        settings = tk.Frame(self)
        settings.pack(fill="x", padx=16, pady=(0, 6))

        col1 = tk.LabelFrame(settings, text=" 质量预设 ",
                              font=("Microsoft YaHei", 10, "bold"))
        col1.pack(side="left", fill="both", expand=True, padx=(0, 6))

        col2 = tk.LabelFrame(settings, text=" 自定义参数 ",
                              font=("Microsoft YaHei", 10, "bold"))
        col2.pack(side="right", fill="both", expand=True, padx=(6, 0))

        # ─ 左列：预设 ─
        self._preset_var = tk.StringVar(value="hd")
        for key, info in PRESETS.items():
            r = tk.Frame(col1)
            r.pack(fill="x", padx=8, pady=2)
            tk.Radiobutton(r, text=info["label"],
                           variable=self._preset_var, value=key,
                           font=("Microsoft YaHei", 10, "bold"),
                           command=self._on_preset_change).pack(side="left")
            tk.Label(r, text=info["desc"],
                     font=("Microsoft YaHei", 8), fg="#888").pack(side="left", padx=6)

        # 自定义选项
        r_custom = tk.Frame(col1)
        r_custom.pack(fill="x", padx=8, pady=(2, 8))
        tk.Radiobutton(r_custom, text="自定义",
                       variable=self._preset_var, value="custom",
                       font=("Microsoft YaHei", 10, "bold"),
                       command=self._on_preset_change).pack(side="left")
        tk.Label(r_custom, text="手动调节右侧参数",
                 font=("Microsoft YaHei", 8), fg="#888").pack(side="left", padx=6)

        # ─ 右列：参数 ─

        # JPEG 质量
        r_q = tk.Frame(col2)
        r_q.pack(fill="x", padx=8, pady=(8, 3))
        tk.Label(r_q, text="图片质量：",
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self._quality_var = tk.IntVar(value=85)
        self._quality_scale = tk.Scale(
            r_q, from_=10, to=100, orient="horizontal",
            variable=self._quality_var, length=160,
            font=("Microsoft YaHei", 8))
        self._quality_scale.pack(side="left", padx=4)
        self._quality_hint = tk.Label(
            r_q, text="85（高清）", font=("Microsoft YaHei", 8), fg="#1a73e8")
        self._quality_hint.pack(side="left")
        self._quality_var.trace_add("write", self._update_quality_hint)

        # 最大尺寸
        r_d = tk.Frame(col2)
        r_d.pack(fill="x", padx=8, pady=3)
        tk.Label(r_d, text="图片最大边：",
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self._maxdim_var = tk.IntVar(value=4000)
        ttk.Combobox(r_d, values=["不限制", "1200", "1600", "2000",
                                   "3000", "4000", "5000"],
                     textvariable=self._maxdim_var, width=8,
                     font=("Microsoft YaHei", 9)).pack(side="left", padx=4)
        tk.Label(r_d, text="px（超过此尺寸的图会缩小）",
                 font=("Microsoft YaHei", 8), fg="#888").pack(side="left")

        # 输出 DPI
        r_dpi = tk.Frame(col2)
        r_dpi.pack(fill="x", padx=8, pady=(3, 4))
        tk.Label(r_dpi, text="输出 DPI：",
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self._dpi_var = tk.IntVar(value=300)
        ttk.Combobox(r_dpi, values=["72", "96", "150", "200", "300"],
                     textvariable=self._dpi_var, width=6,
                     font=("Microsoft YaHei", 9)).pack(side="left", padx=4)

        # 其他选项
        r_opt = tk.Frame(col2)
        r_opt.pack(fill="x", padx=8, pady=(0, 8))
        self._clean_meta_var = tk.BooleanVar(value=True)
        tk.Checkbutton(r_opt, text="清理元数据",
                       variable=self._clean_meta_var,
                       font=("Microsoft YaHei", 9)).pack(side="left")
        self._suffix_var = tk.StringVar(value="_compressed")
        tk.Label(r_opt, text="后缀：",
                 font=("Microsoft YaHei", 9)).pack(side="left", padx=(12, 0))
        tk.Entry(r_opt, textvariable=self._suffix_var,
                 font=("Microsoft YaHei", 9), width=14).pack(side="left", padx=4)

        # 禁用参数（预设模式下）
        self._custom_widgets = [self._quality_scale]
        self._on_preset_change()

        # ── 底部：按钮 + 进度 ──
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill="x", padx=16, pady=(0, 4))

        self._start_btn = tk.Button(
            btn_frame, text="开始压缩",
            font=("Microsoft YaHei", 13, "bold"),
            command=self._start_compress)
        self._start_btn.pack(side="left", padx=(0, 10))

        self._progress = ttk.Progressbar(btn_frame, length=240, mode="determinate")
        self._progress.pack(side="left", padx=(0, 10))

        self._status_label = tk.Label(
            btn_frame, text="就绪", font=("Microsoft YaHei", 10), fg="#666")
        self._status_label.pack(side="left")

        # ── 日志 ──
        self._log = scrolledtext.ScrolledText(
            self, font=("Consolas", 9), height=7, state="disabled",
            bg="#fafafa")
        self._log.pack(fill="both", expand=True, padx=16, pady=(0, 12))

    # ── 文件管理 ──

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="选择 PDF 文件",
            filetypes=[("PDF 文件", "*.pdf")])
        for p in paths:
            if p not in self._files:
                self._files.append(p)
                self._file_listbox.insert("end", os.path.basename(p))
        self._file_count_label.configure(text=f"{len(self._files)} 个文件")

    def _add_folder(self):
        folder = filedialog.askdirectory(title="选择文件夹")
        if not folder:
            return
        count = 0
        for name in os.listdir(folder):
            if name.lower().endswith(".pdf"):
                p = os.path.join(folder, name)
                if p not in self._files:
                    self._files.append(p)
                    self._file_listbox.insert("end", name)
                    count += 1
        self._file_count_label.configure(text=f"{len(self._files)} 个文件")
        if count == 0:
            messagebox.showinfo("提示", "该文件夹中没有 PDF 文件")

    def _clear_files(self):
        self._files.clear()
        self._file_listbox.delete(0, "end")
        self._file_count_label.configure(text="0 个文件")

    # ── 预设切换 ──

    def _on_preset_change(self):
        preset = self._preset_var.get()
        is_custom = (preset == "custom")

        state = "normal" if is_custom else "disabled"
        self._quality_scale.configure(state=state)

        if not is_custom and preset in PRESETS:
            info = PRESETS[preset]
            self._quality_var.set(info["quality"])
            if info["max_dim"] > 0:
                self._maxdim_var.set(info["max_dim"])
            self._dpi_var.set(info["dpi"] if info["dpi"] > 0 else 300)

    def _update_quality_hint(self, *args):
        try:
            q = self._quality_var.get()
            if q >= 85:
                hint = f"{q}（高清）"
            elif q >= 60:
                hint = f"{q}（标准）"
            elif q >= 40:
                hint = f"{q}（中等）"
            else:
                hint = f"{q}（压缩较重）"
            self._quality_hint.configure(text=hint)
        except (tk.TclError, ValueError):
            pass

    # ── 日志 / 状态 ──

    def _log_msg(self, msg):
        self._log.configure(state="normal")
        self._log.insert("end", msg + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _set_status(self, text, color="#666"):
        self._status_label.configure(text=text, fg=color)

    # ── 压缩核心 ──

    def _start_compress(self):
        if not self._files:
            messagebox.showwarning("提示", "请先添加 PDF 文件")
            return
        if self._working:
            return

        self._working = True
        self._start_btn.configure(state="disabled")
        self._progress["value"] = 0
        self._progress["maximum"] = len(self._files)

        thread = threading.Thread(target=self._compress_thread, daemon=True)
        thread.start()

    def _compress_thread(self):
        quality = self._quality_var.get()
        try:
            max_dim_raw = self._maxdim_var.get()
            max_dim = int(max_dim_raw) if int(max_dim_raw) > 0 else 0
        except (ValueError, tk.TclError):
            max_dim = 0
        suffix = self._suffix_var.get()
        clean_meta = self._clean_meta_var.get()
        preset = self._preset_var.get()

        # 仅瘦身模式不动图片
        images_skip = (preset == "lossless")

        total_before = 0
        total_after = 0

        self.after(0, self._log_msg, "=" * 56)
        self.after(0, self._log_msg,
                   f"开始压缩  质量={quality}  最大边={max_dim or '不限'}  "
                   f"预设={PRESETS.get(preset, {}).get('label', '自定义')}")
        self.after(0, self._log_msg, "=" * 56)

        for idx, filepath in enumerate(self._files):
            name = os.path.basename(filepath)
            self.after(0, self._set_status,
                       f"[{idx + 1}/{len(self._files)}] {name}", "#1a73e8")

            try:
                before_size = os.path.getsize(filepath)
                total_before += before_size

                # 输出路径
                base, ext = os.path.splitext(filepath)
                out_path = f"{base}{suffix}{ext}"

                doc = fitz.open(filepath)
                img_count = 0
                compressed_count = 0

                if not images_skip:
                    # 收集所有图片 xref（去重）
                    seen_xrefs = set()
                    for page_num in range(len(doc)):
                        page = doc[page_num]
                        for img_info in page.get_images(full=True):
                            xref = img_info[0]
                            if xref not in seen_xrefs:
                                seen_xrefs.add(xref)

                    img_count = len(seen_xrefs)

                    for xref in seen_xrefs:
                        try:
                            base_image = doc.extract_image(xref)
                            if not base_image:
                                continue

                            img_bytes = base_image["image"]

                            # 打开图片
                            pil_img = Image.open(io.BytesIO(img_bytes))

                            # 转为 RGB（JPEG 不支持透明通道）
                            if pil_img.mode in ("RGBA", "P", "LA"):
                                bg = Image.new("RGB", pil_img.size,
                                               (255, 255, 255))
                                if pil_img.mode == "P":
                                    pil_img = pil_img.convert("RGBA")
                                bg.paste(pil_img,
                                         mask=pil_img.split()[-1]
                                         if "A" in pil_img.mode else None)
                                pil_img = bg
                            elif pil_img.mode != "RGB":
                                pil_img = pil_img.convert("RGB")

                            # 缩小超大图片
                            if max_dim > 0:
                                w, h = pil_img.size
                                if w > max_dim or h > max_dim:
                                    ratio = min(max_dim / w, max_dim / h)
                                    new_w = max(int(w * ratio), 1)
                                    new_h = max(int(h * ratio), 1)
                                    pil_img = pil_img.resize(
                                        (new_w, new_h), Image.LANCZOS)

                            # 重压缩为 JPEG
                            buf = io.BytesIO()
                            pil_img.save(buf, format="JPEG",
                                         quality=quality, optimize=True)
                            new_bytes = buf.getvalue()

                            # 只有确实变小了才替换（直接写流）
                            if len(new_bytes) < len(img_bytes):
                                # 用 replace_image 替换（PyMuPDF ≥ 1.21）
                                try:
                                    pix = fitz.Pixmap(new_bytes)
                                    doc.xref_set_key(xref, "Filter",
                                                     "/DCTDecode")
                                    doc.xref_set_key(xref, "ColorSpace",
                                                     "/DeviceRGB")
                                    doc.xref_set_key(xref, "Width",
                                                     str(pil_img.width))
                                    doc.xref_set_key(xref, "Height",
                                                     str(pil_img.height))
                                    doc.xref_set_key(xref, "BitsPerComponent",
                                                     "8")
                                    doc.update_stream(xref, new_bytes)
                                    compressed_count += 1
                                except Exception:
                                    pass

                        except Exception:
                            continue

                # 保存（清理垃圾对象 + 压缩流）
                save_opts = {
                    "garbage": 4,
                    "deflate": True,
                    "clean": True,
                }
                if clean_meta:
                    doc.set_metadata({})

                doc.save(out_path, **save_opts)
                doc.close()

                after_size = os.path.getsize(out_path)
                total_after += after_size
                ratio = (1 - after_size / before_size) * 100 if before_size > 0 else 0

                self.after(0, self._log_msg,
                           f"  {name}")
                self.after(0, self._log_msg,
                           f"    {format_size(before_size)} → "
                           f"{format_size(after_size)}  "
                           f"压缩率 {ratio:.1f}%  "
                           f"图片 {compressed_count}/{img_count} 张已压缩")
                self.after(0, self._log_msg,
                           f"    → {out_path}")

            except Exception as e:
                self.after(0, self._log_msg, f"  {name} 失败: {e}")

            self.after(0, lambda v=idx + 1: self._progress.configure(value=v))

        # 汇总
        total_ratio = ((1 - total_after / total_before) * 100
                       if total_before > 0 else 0)
        self.after(0, self._log_msg, "")
        self.after(0, self._log_msg, "=" * 56)
        self.after(0, self._log_msg,
                   f"全部完成！{len(self._files)} 个文件")
        self.after(0, self._log_msg,
                   f"总计 {format_size(total_before)} → "
                   f"{format_size(total_after)}  "
                   f"节省 {format_size(total_before - total_after)}  "
                   f"压缩率 {total_ratio:.1f}%")
        self.after(0, self._log_msg, "=" * 56)
        self.after(0, self._set_status,
                   f"完成！节省 {total_ratio:.1f}%", "#2e7d32")
        self.after(0, self._finish)

    def _finish(self):
        self._working = False
        self._start_btn.configure(state="normal")


if __name__ == "__main__":
    app = PDFCompressorApp()
    app.mainloop()
