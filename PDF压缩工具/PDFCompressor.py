"""
PDF 压缩工具 v2 —— GUI 图形窗口版
对 PDF 内嵌图片进行智能重压缩
支持五档质量预设 + 自定义参数
新增：图片预览对比、提取图片、逐张详细日志
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
import io

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# ── 质量预设 ──
PRESETS = {
    "extreme": {"label": "极致压缩", "desc": "最小体积，图片会有可见模糊",
                "quality": 30, "max_dim": 1200},
    "standard": {"label": "标准压缩", "desc": "体积与画质均衡（推荐日常用）",
                 "quality": 60, "max_dim": 2000},
    "hd": {"label": "高清压缩", "desc": "画质几乎无损，体积也能减不少",
            "quality": 85, "max_dim": 4000},
    "lossless": {"label": "仅瘦身", "desc": "不碰图片质量，只清理冗余数据",
                  "quality": 100, "max_dim": 0},
}

WINDOW_W = 820
WINDOW_H = 720


def format_size(n):
    if n < 1024:
        return f"{n} B"
    elif n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    else:
        return f"{n / (1024 * 1024):.2f} MB"


def compress_image(pil_img, quality, max_dim):
    """压缩单张图片，返回 (new_bytes, new_pil) 或 None"""
    # 转为 RGB
    if pil_img.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", pil_img.size, (255, 255, 255))
        temp = pil_img.convert("RGBA") if pil_img.mode == "P" else pil_img
        bg.paste(temp, mask=temp.split()[-1] if "A" in temp.mode else None)
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
            pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)

    # 重压缩为 JPEG
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue(), pil_img


class PDFCompressorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF 压缩工具 v2")
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.resizable(False, False)
        self._files = []
        self._working = False
        self._preview_photos = [None, None]

        if not HAS_FITZ or not HAS_PIL:
            self._dep_error()
        else:
            self._build_ui()

    def _dep_error(self):
        f = tk.Frame(self)
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="需要安装依赖",
                 font=("Microsoft YaHei", 18, "bold"),
                 fg="#c62828").pack(pady=(0, 16))
        tk.Label(f, text="pip install PyMuPDF Pillow",
                 font=("Consolas", 14, "bold"), fg="#1a73e8").pack()

    def _build_ui(self):
        # ── 标题 ──
        top = tk.Frame(self)
        top.pack(fill="x", padx=14, pady=(10, 4))
        tk.Label(top, text="PDF 压缩工具",
                 font=("Microsoft YaHei", 16, "bold")).pack(side="left")
        tk.Label(top, text="图片智能重压缩 · 可预览 · 可提取",
                 font=("Microsoft YaHei", 10), fg="#888").pack(side="left", padx=10)

        # ── 文件列表 ──
        file_frame = tk.LabelFrame(self, text=" 待压缩文件 ",
                                    font=("Microsoft YaHei", 10, "bold"))
        file_frame.pack(fill="x", padx=14, pady=(0, 4))

        btn_row = tk.Frame(file_frame)
        btn_row.pack(fill="x", padx=8, pady=(4, 2))
        tk.Button(btn_row, text="添加 PDF",
                  font=("Microsoft YaHei", 9),
                  command=self._add_files).pack(side="left")
        tk.Button(btn_row, text="添加文件夹",
                  font=("Microsoft YaHei", 9),
                  command=self._add_folder).pack(side="left", padx=4)
        tk.Button(btn_row, text="清空",
                  font=("Microsoft YaHei", 9),
                  command=self._clear_files).pack(side="left", padx=4)
        self._file_count_label = tk.Label(
            btn_row, text="0 个文件", font=("Microsoft YaHei", 9), fg="#888")
        self._file_count_label.pack(side="right")

        self._file_listbox = tk.Listbox(
            file_frame, height=3, font=("Consolas", 9), selectmode="extended")
        self._file_listbox.pack(fill="x", padx=8, pady=(0, 6))

        # ── 设置（两列）──
        settings = tk.Frame(self)
        settings.pack(fill="x", padx=14, pady=(0, 4))

        col1 = tk.LabelFrame(settings, text=" 质量预设 ",
                              font=("Microsoft YaHei", 10, "bold"))
        col1.pack(side="left", fill="both", expand=True, padx=(0, 4))

        col2 = tk.LabelFrame(settings, text=" 自定义参数 ",
                              font=("Microsoft YaHei", 10, "bold"))
        col2.pack(side="right", fill="both", expand=True, padx=(4, 0))

        # 左列：预设
        self._preset_var = tk.StringVar(value="hd")
        for key, info in PRESETS.items():
            r = tk.Frame(col1)
            r.pack(fill="x", padx=6, pady=1)
            tk.Radiobutton(r, text=info["label"],
                           variable=self._preset_var, value=key,
                           font=("Microsoft YaHei", 9, "bold"),
                           command=self._on_preset_change).pack(side="left")
            tk.Label(r, text=info["desc"],
                     font=("Microsoft YaHei", 8), fg="#888").pack(side="left", padx=4)

        r_custom = tk.Frame(col1)
        r_custom.pack(fill="x", padx=6, pady=(1, 6))
        tk.Radiobutton(r_custom, text="自定义",
                       variable=self._preset_var, value="custom",
                       font=("Microsoft YaHei", 9, "bold"),
                       command=self._on_preset_change).pack(side="left")
        tk.Label(r_custom, text="手动调右侧参数",
                 font=("Microsoft YaHei", 8), fg="#888").pack(side="left", padx=4)

        # 右列：参数
        # 图片质量
        r_q = tk.Frame(col2)
        r_q.pack(fill="x", padx=6, pady=(6, 2))
        tk.Label(r_q, text="图片质量：",
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self._quality_var = tk.IntVar(value=85)
        self._quality_scale = tk.Scale(
            r_q, from_=10, to=100, orient="horizontal",
            variable=self._quality_var, length=140,
            font=("Microsoft YaHei", 8))
        self._quality_scale.pack(side="left", padx=2)
        self._quality_hint = tk.Label(
            r_q, text="85（高清）", font=("Microsoft YaHei", 8), fg="#1a73e8")
        self._quality_hint.pack(side="left")
        self._quality_var.trace_add("write", self._update_quality_hint)

        # 最大尺寸
        r_d = tk.Frame(col2)
        r_d.pack(fill="x", padx=6, pady=2)
        tk.Label(r_d, text="最大边 px：",
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self._maxdim_var = tk.IntVar(value=4000)
        ttk.Combobox(r_d, values=["不限制", "1200", "1600", "2000",
                                   "3000", "4000", "5000"],
                     textvariable=self._maxdim_var, width=7,
                     font=("Microsoft YaHei", 9)).pack(side="left", padx=2)
        tk.Label(r_d, text="超过会缩小",
                 font=("Microsoft YaHei", 8), fg="#888").pack(side="left", padx=2)

        # 选项行
        r_opt = tk.Frame(col2)
        r_opt.pack(fill="x", padx=6, pady=(2, 4))
        self._clean_meta_var = tk.BooleanVar(value=True)
        tk.Checkbutton(r_opt, text="清理元数据",
                       variable=self._clean_meta_var,
                       font=("Microsoft YaHei", 9)).pack(side="left")
        self._suffix_var = tk.StringVar(value="_compressed")
        tk.Label(r_opt, text="后缀：",
                 font=("Microsoft YaHei", 9)).pack(side="left", padx=(8, 0))
        tk.Entry(r_opt, textvariable=self._suffix_var,
                 font=("Microsoft YaHei", 9), width=12).pack(side="left", padx=2)

        self._on_preset_change()

        # ── 操作按钮 ──
        act_frame = tk.Frame(self)
        act_frame.pack(fill="x", padx=14, pady=(0, 4))

        self._start_btn = tk.Button(
            act_frame, text="开始压缩",
            font=("Microsoft YaHei", 12, "bold"),
            command=self._start_compress)
        self._start_btn.pack(side="left", padx=(0, 6))

        tk.Button(act_frame, text="预览对比",
                  font=("Microsoft YaHei", 10),
                  command=self._preview_compare).pack(side="left", padx=(0, 6))

        tk.Button(act_frame, text="提取全部图片",
                  font=("Microsoft YaHei", 10),
                  command=self._extract_images).pack(side="left", padx=(0, 6))

        self._progress = ttk.Progressbar(act_frame, length=160,
                                          mode="determinate")
        self._progress.pack(side="left", padx=(6, 6))
        self._status_label = tk.Label(
            act_frame, text="就绪", font=("Microsoft YaHei", 10), fg="#666")
        self._status_label.pack(side="left")

        # ── 预览区（左原图 右压缩后）──
        self._preview_frame = tk.LabelFrame(
            self, text=" 图片预览对比（选 PDF 后点「预览对比」）",
            font=("Microsoft YaHei", 9))
        self._preview_frame.pack(fill="x", padx=14, pady=(0, 4))

        prev_inner = tk.Frame(self._preview_frame)
        prev_inner.pack(fill="x", padx=6, pady=6)

        # 左：原图
        pf1 = tk.Frame(prev_inner)
        pf1.pack(side="left", fill="both", expand=True, padx=(0, 4))
        self._prev_label1_title = tk.Label(
            pf1, text="原图", font=("Microsoft YaHei", 9, "bold"), fg="#333")
        self._prev_label1_title.pack()
        self._prev_label1 = tk.Label(pf1, bg="#f0f0f0", height=6)
        self._prev_label1.pack(fill="both", expand=True)

        # 右：压缩后
        pf2 = tk.Frame(prev_inner)
        pf2.pack(side="right", fill="both", expand=True, padx=(4, 0))
        self._prev_label2_title = tk.Label(
            pf2, text="压缩后", font=("Microsoft YaHei", 9, "bold"), fg="#333")
        self._prev_label2_title.pack()
        self._prev_label2 = tk.Label(pf2, bg="#f0f0f0", height=6)
        self._prev_label2.pack(fill="both", expand=True)

        # ── 日志 ──
        self._log = scrolledtext.ScrolledText(
            self, font=("Consolas", 9), height=6, state="disabled",
            bg="#fafafa")
        self._log.pack(fill="both", expand=True, padx=14, pady=(0, 10))

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
        for name in os.listdir(folder):
            if name.lower().endswith(".pdf"):
                p = os.path.join(folder, name)
                if p not in self._files:
                    self._files.append(p)
                    self._file_listbox.insert("end", name)
        self._file_count_label.configure(text=f"{len(self._files)} 个文件")

    def _clear_files(self):
        self._files.clear()
        self._file_listbox.delete(0, "end")
        self._file_count_label.configure(text="0 个文件")

    # ── 预设 ──

    def _on_preset_change(self):
        preset = self._preset_var.get()
        is_custom = (preset == "custom")
        self._quality_scale.configure(state="normal" if is_custom else "disabled")
        if not is_custom and preset in PRESETS:
            info = PRESETS[preset]
            self._quality_var.set(info["quality"])
            if info["max_dim"] > 0:
                self._maxdim_var.set(info["max_dim"])

    def _update_quality_hint(self, *args):
        try:
            q = self._quality_var.get()
            if q >= 85:
                self._quality_hint.configure(text=f"{q}（高清）")
            elif q >= 60:
                self._quality_hint.configure(text=f"{q}（标准）")
            elif q >= 40:
                self._quality_hint.configure(text=f"{q}（中等）")
            else:
                self._quality_hint.configure(text=f"{q}（压缩较重）")
        except (tk.TclError, ValueError):
            pass

    def _log_msg(self, msg):
        self._log.configure(state="normal")
        self._log.insert("end", msg + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _set_status(self, text, color="#666"):
        self._status_label.configure(text=text, fg=color)

    def _get_max_dim(self):
        try:
            v = self._maxdim_var.get()
            return int(v) if int(v) > 0 else 0
        except (ValueError, tk.TclError):
            return 0

    # ── 预览对比 ──

    def _preview_compare(self):
        if not self._files:
            messagebox.showwarning("提示", "请先添加 PDF 文件")
            return

        quality = self._quality_var.get()
        max_dim = self._get_max_dim()

        def task():
            try:
                self.after(0, self._set_status, "正在提取预览图...", "#1a73e8")
                doc = fitz.open(self._files[0])

                # 找第一张足够大的图片
                target_xref = None
                for page in doc:
                    for img_info in page.get_images(full=True):
                        xref = img_info[0]
                        base_img = doc.extract_image(xref)
                        if base_img and len(base_img["image"]) > 5000:
                            target_xref = xref
                            break
                    if target_xref:
                        break

                if not target_xref:
                    self.after(0, messagebox.showinfo, "提示",
                               "该 PDF 没有找到足够大的图片")
                    doc.close()
                    return

                base_img = doc.extract_image(target_xref)
                orig_bytes = base_img["image"]
                orig_pil = Image.open(io.BytesIO(orig_bytes))
                orig_w, orig_h = orig_pil.size

                # 压缩
                new_bytes, new_pil = compress_image(
                    orig_pil.copy(), quality, max_dim)
                new_w, new_h = new_pil.size

                doc.close()

                # 显示预览
                self.after(0, self._show_preview,
                           orig_pil, new_pil,
                           len(orig_bytes), len(new_bytes),
                           orig_w, orig_h, new_w, new_h, quality)
                self.after(0, self._set_status, "预览完成", "#2e7d32")
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("错误", str(e)))

        threading.Thread(target=task, daemon=True).start()

    def _show_preview(self, orig, comp, orig_size, comp_size,
                      ow, oh, nw, nh, quality):
        pw, ph = 370, 100
        # 原图
        r1 = min(pw / orig.width, ph / orig.height, 1.0)
        d1 = orig.resize((max(int(orig.width * r1), 1),
                           max(int(orig.height * r1), 1)), Image.LANCZOS)
        if d1.mode != "RGB":
            d1 = d1.convert("RGB")
        self._preview_photos[0] = ImageTk.PhotoImage(d1)
        self._prev_label1.configure(image=self._preview_photos[0])
        self._prev_label1_title.configure(
            text=f"原图  {ow}×{oh}  {format_size(orig_size)}")

        # 压缩后
        r2 = min(pw / comp.width, ph / comp.height, 1.0)
        d2 = comp.resize((max(int(comp.width * r2), 1),
                           max(int(comp.height * r2), 1)), Image.LANCZOS)
        self._preview_photos[1] = ImageTk.PhotoImage(d2)
        self._prev_label2.configure(image=self._preview_photos[1])
        saved = (1 - comp_size / orig_size) * 100 if orig_size > 0 else 0
        self._prev_label2_title.configure(
            text=f"质量{quality}  {nw}×{nh}  "
                 f"{format_size(comp_size)}  节省{saved:.0f}%")

    # ── 提取全部图片 ──

    def _extract_images(self):
        if not self._files:
            messagebox.showwarning("提示", "请先添加 PDF 文件")
            return

        out_dir = filedialog.askdirectory(title="选择保存文件夹")
        if not out_dir:
            return

        def task():
            total = 0
            for fp in self._files:
                name = os.path.splitext(os.path.basename(fp))[0]
                self.after(0, self._set_status,
                           f"提取: {name}", "#1a73e8")
                try:
                    doc = fitz.open(fp)
                    seen = set()
                    idx = 0
                    for page in doc:
                        for img_info in page.get_images(full=True):
                            xref = img_info[0]
                            if xref in seen:
                                continue
                            seen.add(xref)
                            base_img = doc.extract_image(xref)
                            if not base_img:
                                continue
                            ext = base_img["ext"]
                            img_bytes = base_img["image"]
                            w = base_img["width"]
                            h = base_img["height"]

                            idx += 1
                            fname = f"{name}_img{idx}_{w}x{h}.{ext}"
                            out_path = os.path.join(out_dir, fname)
                            with open(out_path, "wb") as f:
                                f.write(img_bytes)

                            self.after(0, self._log_msg,
                                       f"  {fname}  {format_size(len(img_bytes))}")
                            total += 1
                    doc.close()
                except Exception as e:
                    self.after(0, self._log_msg, f"  {name} 失败: {e}")

            self.after(0, self._log_msg,
                       f"\n提取完成！共 {total} 张图片 → {out_dir}")
            self.after(0, self._set_status,
                       f"提取完成！{total} 张图片", "#2e7d32")
            self.after(0, lambda: os.startfile(out_dir))

        threading.Thread(target=task, daemon=True).start()

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
        threading.Thread(target=self._compress_thread, daemon=True).start()

    def _compress_thread(self):
        quality = self._quality_var.get()
        max_dim = self._get_max_dim()
        suffix = self._suffix_var.get()
        clean_meta = self._clean_meta_var.get()
        preset = self._preset_var.get()
        images_skip = (preset == "lossless")

        total_before = 0
        total_after = 0

        self.after(0, self._log_msg, "=" * 60)
        preset_name = PRESETS.get(preset, {}).get("label", "自定义")
        self.after(0, self._log_msg,
                   f"开始压缩  质量={quality}  最大边={max_dim or '不限'}  "
                   f"模式={preset_name}")
        self.after(0, self._log_msg, "=" * 60)

        for idx, filepath in enumerate(self._files):
            name = os.path.basename(filepath)
            self.after(0, self._set_status,
                       f"[{idx + 1}/{len(self._files)}] {name}", "#1a73e8")

            try:
                before_size = os.path.getsize(filepath)
                total_before += before_size

                base, ext = os.path.splitext(filepath)
                out_path = f"{base}{suffix}{ext}"

                doc = fitz.open(filepath)
                img_count = 0
                compressed_count = 0
                saved_bytes = 0

                if not images_skip:
                    # 收集所有图片 xref（去重）
                    seen_xrefs = set()
                    for page in doc:
                        for img_info in page.get_images(full=True):
                            seen_xrefs.add(img_info[0])

                    img_count = len(seen_xrefs)
                    self.after(0, self._log_msg,
                               f"\n  {name} ({format_size(before_size)}) "
                               f"- 发现 {img_count} 张图片")

                    for xref in seen_xrefs:
                        try:
                            base_image = doc.extract_image(xref)
                            if not base_image:
                                continue

                            img_bytes = base_image["image"]
                            orig_size = len(img_bytes)
                            orig_w = base_image["width"]
                            orig_h = base_image["height"]

                            pil_img = Image.open(io.BytesIO(img_bytes))
                            result = compress_image(pil_img, quality, max_dim)
                            if result is None:
                                continue
                            new_bytes, new_pil = result
                            new_size = len(new_bytes)

                            # 只有变小了才替换
                            if new_size < orig_size:
                                # 清除旧的滤镜相关 key（避免冲突）
                                try:
                                    doc.xref_set_key(xref, "DecodeParms", "null")
                                except Exception:
                                    pass
                                try:
                                    doc.xref_set_key(xref, "Predictor", "null")
                                except Exception:
                                    pass

                                doc.xref_set_key(xref, "Filter", "/DCTDecode")
                                doc.xref_set_key(xref, "ColorSpace", "/DeviceRGB")
                                doc.xref_set_key(xref, "Width", str(new_pil.width))
                                doc.xref_set_key(xref, "Height", str(new_pil.height))
                                doc.xref_set_key(xref, "BitsPerComponent", "8")
                                doc.update_stream(xref, new_bytes)

                                diff = orig_size - new_size
                                saved_bytes += diff
                                compressed_count += 1

                                self.after(0, self._log_msg,
                                           f"    [{compressed_count}] "
                                           f"{orig_w}x{orig_h} → "
                                           f"{new_pil.width}x{new_pil.height}  "
                                           f"{format_size(orig_size)} → "
                                           f"{format_size(new_size)}  "
                                           f"(-{format_size(diff)})")
                            else:
                                self.after(0, self._log_msg,
                                           f"    [跳过] {orig_w}x{orig_h}  "
                                           f"{format_size(orig_size)}  "
                                           f"已经很小了")

                        except Exception as e:
                            self.after(0, self._log_msg,
                                       f"    [错误] xref={xref}: {e}")
                            continue

                # 保存
                save_opts = {"garbage": 4, "deflate": True, "clean": True}
                if clean_meta:
                    doc.set_metadata({})
                doc.save(out_path, **save_opts)
                doc.close()

                after_size = os.path.getsize(out_path)
                total_after += after_size
                ratio = (1 - after_size / before_size) * 100 if before_size > 0 else 0

                self.after(0, self._log_msg,
                           f"  ✓ {format_size(before_size)} → "
                           f"{format_size(after_size)}  "
                           f"压缩 {ratio:.1f}%  "
                           f"({compressed_count}/{img_count} 张图片已压缩)")
                self.after(0, self._log_msg, f"    → {out_path}")

            except Exception as e:
                self.after(0, self._log_msg, f"  ✗ {name} 失败: {e}")

            self.after(0, lambda v=idx + 1: self._progress.configure(value=v))

        # 汇总
        total_ratio = ((1 - total_after / total_before) * 100
                       if total_before > 0 else 0)
        self.after(0, self._log_msg, "\n" + "=" * 60)
        self.after(0, self._log_msg,
                   f"全部完成！{len(self._files)} 个文件")
        self.after(0, self._log_msg,
                   f"总计 {format_size(total_before)} → "
                   f"{format_size(total_after)}  "
                   f"节省 {format_size(total_before - total_after)}  "
                   f"压缩率 {total_ratio:.1f}%")
        self.after(0, self._log_msg, "=" * 60)
        self.after(0, self._set_status,
                   f"完成！节省 {total_ratio:.1f}%", "#2e7d32")
        self.after(0, self._finish)

    def _finish(self):
        self._working = False
        self._start_btn.configure(state="normal")


if __name__ == "__main__":
    app = PDFCompressorApp()
    app.mainloop()
