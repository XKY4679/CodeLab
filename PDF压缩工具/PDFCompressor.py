"""
PDF 压缩工具 v3 —— GUI 图形窗口版
对 PDF 内嵌图片进行智能重压缩
支持五档质量预设 + 自定义参数
新增：逐图管理（单独设置每张图片质量）、预览对比、提取图片
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
    """压缩单张图片，返回 (new_bytes, new_pil)"""
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


def replace_xref_image(doc, xref, new_bytes, new_pil):
    """替换 PDF 中指定 xref 的图片流"""
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


# ══════════════════════════════════════════════
#  逐图管理弹窗
# ══════════════════════════════════════════════

class ImageManagerWindow(tk.Toplevel):
    """弹出窗口：浏览 PDF 中所有图片，逐张设置压缩质量"""

    def __init__(self, master, pdf_path, default_quality, default_max_dim,
                 suffix, clean_meta, log_func):
        super().__init__(master)
        self.title(f"逐图管理 - {os.path.basename(pdf_path)}")
        self.geometry("960x660")
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()

        self._pdf_path = pdf_path
        self._default_quality = default_quality
        self._default_max_dim = default_max_dim
        self._suffix = suffix
        self._clean_meta = clean_meta
        self._log_func = log_func
        self._images = []          # list of dicts
        self._current_idx = -1
        self._preview_photo_orig = None
        self._preview_photo_comp = None
        self._updating_preview = False

        self._build_ui()
        self._load_images()

    def _build_ui(self):
        # ── 顶部信息条 ──
        top = tk.Frame(self)
        top.pack(fill="x", padx=10, pady=(8, 4))
        self._info_label = tk.Label(
            top, text="正在加载图片...",
            font=("Microsoft YaHei", 10), fg="#666")
        self._info_label.pack(side="left")
        self._total_label = tk.Label(
            top, text="", font=("Microsoft YaHei", 10, "bold"), fg="#1a73e8")
        self._total_label.pack(side="right")

        # ── 主体：左列表 + 右预览 ──
        body = tk.Frame(self)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        # 左侧：图片列表
        left = tk.Frame(body, width=320)
        left.pack(side="left", fill="y", padx=(0, 6))
        left.pack_propagate(False)

        tk.Label(left, text="图片列表（点击选中）",
                 font=("Microsoft YaHei", 9, "bold")).pack(anchor="w")

        list_frame = tk.Frame(left)
        list_frame.pack(fill="both", expand=True)

        self._tree = ttk.Treeview(
            list_frame,
            columns=("idx", "size_dim", "orig_size", "quality", "status"),
            show="headings", height=18)
        self._tree.heading("idx", text="#")
        self._tree.heading("size_dim", text="尺寸")
        self._tree.heading("orig_size", text="大小")
        self._tree.heading("quality", text="质量")
        self._tree.heading("status", text="状态")
        self._tree.column("idx", width=30, anchor="center")
        self._tree.column("size_dim", width=90, anchor="center")
        self._tree.column("orig_size", width=65, anchor="center")
        self._tree.column("quality", width=45, anchor="center")
        self._tree.column("status", width=55, anchor="center")

        tree_scroll = ttk.Scrollbar(list_frame, orient="vertical",
                                     command=self._tree.yview)
        self._tree.configure(yscrollcommand=tree_scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # 左侧底部：批量操作
        batch_frame = tk.LabelFrame(left, text=" 批量操作 ",
                                     font=("Microsoft YaHei", 8))
        batch_frame.pack(fill="x", pady=(4, 0))

        tk.Button(batch_frame, text="全部设为此质量",
                  font=("Microsoft YaHei", 8),
                  command=self._apply_all).pack(side="left", padx=2, pady=2)
        tk.Button(batch_frame, text="恢复默认",
                  font=("Microsoft YaHei", 8),
                  command=self._reset_all).pack(side="left", padx=2, pady=2)
        tk.Button(batch_frame, text="大图压狠/小图保留",
                  font=("Microsoft YaHei", 8),
                  command=self._smart_assign).pack(side="left", padx=2, pady=2)

        # 右侧：预览 + 控制
        right = tk.Frame(body)
        right.pack(side="right", fill="both", expand=True)

        # 原图预览
        prev_frame = tk.LabelFrame(right, text=" 原图预览 ",
                                    font=("Microsoft YaHei", 9))
        prev_frame.pack(fill="both", expand=True, pady=(0, 4))

        self._orig_title = tk.Label(
            prev_frame, text="选择一张图片查看",
            font=("Microsoft YaHei", 9), fg="#888")
        self._orig_title.pack(pady=(2, 0))
        self._orig_label = tk.Label(prev_frame, bg="#f5f5f5")
        self._orig_label.pack(fill="both", expand=True, padx=4, pady=4)

        # 压缩预览
        comp_frame = tk.LabelFrame(right, text=" 压缩后预览 ",
                                    font=("Microsoft YaHei", 9))
        comp_frame.pack(fill="both", expand=True, pady=(0, 4))

        self._comp_title = tk.Label(
            comp_frame, text="拖动下方滑块查看压缩效果",
            font=("Microsoft YaHei", 9), fg="#888")
        self._comp_title.pack(pady=(2, 0))
        self._comp_label = tk.Label(comp_frame, bg="#f5f5f5")
        self._comp_label.pack(fill="both", expand=True, padx=4, pady=4)

        # 控制区
        ctrl = tk.Frame(right)
        ctrl.pack(fill="x", pady=(0, 2))

        tk.Label(ctrl, text="该图质量：",
                 font=("Microsoft YaHei", 9, "bold")).pack(side="left")

        self._img_quality_var = tk.IntVar(value=self._default_quality)
        self._img_quality_scale = tk.Scale(
            ctrl, from_=10, to=100, orient="horizontal",
            variable=self._img_quality_var, length=200,
            font=("Microsoft YaHei", 8),
            command=self._on_quality_change)
        self._img_quality_scale.pack(side="left", padx=4)

        self._img_quality_label = tk.Label(
            ctrl, text="", font=("Microsoft YaHei", 9, "bold"), fg="#1a73e8")
        self._img_quality_label.pack(side="left", padx=4)

        tk.Button(ctrl, text="跳过此图",
                  font=("Microsoft YaHei", 9), fg="#c62828",
                  command=self._toggle_skip).pack(side="right", padx=4)

        # ── 底部：预估 + 执行 ──
        bottom = tk.Frame(self)
        bottom.pack(fill="x", padx=10, pady=(0, 8))

        self._estimate_label = tk.Label(
            bottom, text="",
            font=("Microsoft YaHei", 10), fg="#333")
        self._estimate_label.pack(side="left")

        tk.Button(bottom, text="应用并压缩",
                  font=("Microsoft YaHei", 12, "bold"),
                  fg="#fff", bg="#1a73e8", activeforeground="#fff",
                  command=self._do_compress).pack(side="right", padx=(6, 0))

        tk.Button(bottom, text="取消",
                  font=("Microsoft YaHei", 10),
                  command=self.destroy).pack(side="right")

    def _load_images(self):
        """后台线程加载 PDF 中所有图片"""
        def task():
            try:
                doc = fitz.open(self._pdf_path)
                seen = set()
                images = []
                for page in doc:
                    for img_info in page.get_images(full=True):
                        xref = img_info[0]
                        if xref in seen:
                            continue
                        seen.add(xref)
                        base_img = doc.extract_image(xref)
                        if not base_img:
                            continue
                        img_bytes = base_img["image"]
                        # 跳过太小的图（图标/装饰）
                        if len(img_bytes) < 2000:
                            continue
                        try:
                            pil = Image.open(io.BytesIO(img_bytes))
                        except Exception:
                            continue
                        images.append({
                            "xref": xref,
                            "orig_bytes": img_bytes,
                            "orig_pil": pil,
                            "width": pil.width,
                            "height": pil.height,
                            "size": len(img_bytes),
                            "quality": self._default_quality,
                            "skip": False,
                        })
                doc.close()
                self.after(0, self._on_loaded, images)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("错误", str(e)))

        threading.Thread(target=task, daemon=True).start()

    def _on_loaded(self, images):
        self._images = images
        total_size = sum(img["size"] for img in images)
        self._info_label.configure(
            text=f"共 {len(images)} 张图片，"
                 f"原始总大小 {format_size(total_size)}")

        for i, img in enumerate(images):
            self._tree.insert("", "end", iid=str(i), values=(
                i + 1,
                f"{img['width']}x{img['height']}",
                format_size(img["size"]),
                img["quality"],
                "压缩",
            ))

        self._update_estimate()

        if images:
            self._tree.selection_set("0")

    def _on_select(self, event=None):
        sel = self._tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        self._current_idx = idx
        img = self._images[idx]

        # 更新滑块
        self._img_quality_var.set(img["quality"])

        # 显示原图
        self._show_orig(img)

        # 显示压缩预览
        self._show_compressed(img)

    def _show_orig(self, img):
        pil = img["orig_pil"]
        # 适配预览区大小
        max_w, max_h = 580, 140
        r = min(max_w / pil.width, max_h / pil.height, 1.0)
        display = pil.resize((max(int(pil.width * r), 1),
                               max(int(pil.height * r), 1)), Image.LANCZOS)
        if display.mode != "RGB":
            display = display.convert("RGB")
        self._preview_photo_orig = ImageTk.PhotoImage(display)
        self._orig_label.configure(image=self._preview_photo_orig)
        self._orig_title.configure(
            text=f"原图  {img['width']}x{img['height']}  "
                 f"{format_size(img['size'])}")

    def _show_compressed(self, img):
        quality = img["quality"]
        if img["skip"]:
            self._comp_title.configure(
                text="已标记跳过（不压缩）", fg="#999")
            self._comp_label.configure(image="")
            self._preview_photo_comp = None
            self._img_quality_label.configure(text="跳过", fg="#c62828")
            return

        pil = img["orig_pil"].copy()
        new_bytes, new_pil = compress_image(pil, quality, self._default_max_dim)
        new_size = len(new_bytes)

        max_w, max_h = 580, 140
        r = min(max_w / new_pil.width, max_h / new_pil.height, 1.0)
        display = new_pil.resize((max(int(new_pil.width * r), 1),
                                   max(int(new_pil.height * r), 1)),
                                  Image.LANCZOS)
        self._preview_photo_comp = ImageTk.PhotoImage(display)
        self._comp_label.configure(image=self._preview_photo_comp)

        saved = (1 - new_size / img["size"]) * 100 if img["size"] > 0 else 0
        self._comp_title.configure(
            text=f"质量 {quality}  "
                 f"{new_pil.width}x{new_pil.height}  "
                 f"{format_size(new_size)}  "
                 f"节省 {saved:.0f}%",
            fg="#2e7d32" if saved > 0 else "#c62828")

        # 质量文字
        if quality >= 85:
            hint = f"{quality} 高清"
        elif quality >= 60:
            hint = f"{quality} 标准"
        elif quality >= 40:
            hint = f"{quality} 中等"
        else:
            hint = f"{quality} 压缩重"
        self._img_quality_label.configure(text=hint, fg="#1a73e8")

    def _on_quality_change(self, val=None):
        if self._current_idx < 0 or self._current_idx >= len(self._images):
            return
        img = self._images[self._current_idx]
        new_q = self._img_quality_var.get()
        if img["quality"] == new_q:
            return
        img["quality"] = new_q
        img["skip"] = False

        # 更新列表显示
        self._tree.set(str(self._current_idx), "quality", new_q)
        self._tree.set(str(self._current_idx), "status", "压缩")

        # 延迟刷新预览（防止拖滑块卡顿）
        if self._updating_preview:
            return
        self._updating_preview = True
        self.after(150, self._delayed_preview)

    def _delayed_preview(self):
        self._updating_preview = False
        if self._current_idx < 0 or self._current_idx >= len(self._images):
            return
        self._show_compressed(self._images[self._current_idx])
        self._update_estimate()

    def _toggle_skip(self):
        if self._current_idx < 0:
            return
        img = self._images[self._current_idx]
        img["skip"] = not img["skip"]
        status = "跳过" if img["skip"] else "压缩"
        self._tree.set(str(self._current_idx), "status", status)
        self._show_compressed(img)
        self._update_estimate()

    def _apply_all(self):
        """把当前滑块质量应用到所有图片"""
        q = self._img_quality_var.get()
        for i, img in enumerate(self._images):
            img["quality"] = q
            img["skip"] = False
            self._tree.set(str(i), "quality", q)
            self._tree.set(str(i), "status", "压缩")
        self._update_estimate()

    def _reset_all(self):
        """恢复所有图片为默认质量"""
        for i, img in enumerate(self._images):
            img["quality"] = self._default_quality
            img["skip"] = False
            self._tree.set(str(i), "quality", self._default_quality)
            self._tree.set(str(i), "status", "压缩")
        if self._current_idx >= 0:
            self._img_quality_var.set(self._default_quality)
            self._show_compressed(self._images[self._current_idx])
        self._update_estimate()

    def _smart_assign(self):
        """智能分配：大图压狠，小图保高清"""
        if not self._images:
            return
        sizes = [img["size"] for img in self._images]
        median = sorted(sizes)[len(sizes) // 2]

        for i, img in enumerate(self._images):
            if img["size"] > median * 2:
                # 大图：压狠一点
                q = 45
            elif img["size"] > median:
                # 中图：标准压
                q = 65
            else:
                # 小图：高清保留
                q = 90
            img["quality"] = q
            img["skip"] = False
            self._tree.set(str(i), "quality", q)
            self._tree.set(str(i), "status", "压缩")

        if self._current_idx >= 0:
            self._img_quality_var.set(
                self._images[self._current_idx]["quality"])
            self._show_compressed(self._images[self._current_idx])
        self._update_estimate()

    def _update_estimate(self):
        """更新底部的预估大小"""
        if not self._images:
            return
        orig_total = sum(img["size"] for img in self._images)
        est_total = 0
        for img in self._images:
            if img["skip"]:
                est_total += img["size"]
            else:
                # 快速估算压缩后大小
                q = img["quality"]
                # JPEG 压缩率粗略估计
                ratio = q / 100.0 * 0.7 + 0.05
                est_total += int(img["size"] * ratio)

        saved = orig_total - est_total
        pct = (saved / orig_total * 100) if orig_total > 0 else 0
        self._estimate_label.configure(
            text=f"预估节省 ~{format_size(saved)}（~{pct:.0f}%）  "
                 f"[仅图片部分的估算，实际以压缩结果为准]")
        self._total_label.configure(
            text=f"图片原始: {format_size(orig_total)}")

    def _do_compress(self):
        """按逐图设置执行压缩"""
        if not self._images:
            return

        self._log_func("=" * 60)
        self._log_func(f"逐图管理压缩: {os.path.basename(self._pdf_path)}")
        self._log_func("=" * 60)

        def task():
            try:
                before_size = os.path.getsize(self._pdf_path)
                self.after(0, self._log_func,
                           f"原始文件: {format_size(before_size)}")

                doc = fitz.open(self._pdf_path)
                compressed_count = 0

                for i, img_info in enumerate(self._images):
                    xref = img_info["xref"]
                    if img_info["skip"]:
                        self.after(0, self._log_func,
                                   f"  [{i+1}] {img_info['width']}x"
                                   f"{img_info['height']}  "
                                   f"{format_size(img_info['size'])}  "
                                   f"→ 跳过")
                        continue

                    quality = img_info["quality"]
                    pil = img_info["orig_pil"].copy()
                    new_bytes, new_pil = compress_image(
                        pil, quality, self._default_max_dim)
                    new_size = len(new_bytes)
                    orig_size = img_info["size"]

                    if new_size < orig_size:
                        replace_xref_image(doc, xref, new_bytes, new_pil)
                        diff = orig_size - new_size
                        compressed_count += 1
                        self.after(0, self._log_func,
                                   f"  [{i+1}] Q={quality}  "
                                   f"{img_info['width']}x{img_info['height']}"
                                   f" → {new_pil.width}x{new_pil.height}  "
                                   f"{format_size(orig_size)} → "
                                   f"{format_size(new_size)}  "
                                   f"(-{format_size(diff)})")
                    else:
                        self.after(0, self._log_func,
                                   f"  [{i+1}] Q={quality}  "
                                   f"{img_info['width']}x{img_info['height']}"
                                   f"  {format_size(orig_size)}  "
                                   f"已最优，跳过")

                # 保存
                base, ext = os.path.splitext(self._pdf_path)
                out_path = f"{base}{self._suffix}{ext}"

                save_opts = {"garbage": 4, "deflate": True, "clean": True}
                if self._clean_meta:
                    doc.set_metadata({})
                doc.save(out_path, **save_opts)
                doc.close()

                after_size = os.path.getsize(out_path)
                ratio = ((1 - after_size / before_size) * 100
                         if before_size > 0 else 0)

                self.after(0, self._log_func,
                           f"\n  {format_size(before_size)} → "
                           f"{format_size(after_size)}  "
                           f"压缩 {ratio:.1f}%  "
                           f"({compressed_count}/{len(self._images)} 张已压缩)")
                self.after(0, self._log_func, f"  → {out_path}")
                self.after(0, self._log_func, "=" * 60)

                self.after(0, lambda: messagebox.showinfo(
                    "完成",
                    f"压缩完成！\n"
                    f"{format_size(before_size)} → {format_size(after_size)}\n"
                    f"节省 {ratio:.1f}%\n\n"
                    f"保存至: {out_path}"))

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("压缩失败", str(e)))

        threading.Thread(target=task, daemon=True).start()


# ══════════════════════════════════════════════
#  主窗口
# ══════════════════════════════════════════════

class PDFCompressorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF 压缩工具 v3")
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
        tk.Label(top, text="图片智能重压缩 · 逐图管理 · 可预览 · 可提取",
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

        tk.Button(act_frame, text="逐图管理",
                  font=("Microsoft YaHei", 10, "bold"),
                  fg="#1a73e8",
                  command=self._open_image_manager).pack(side="left", padx=(0, 6))

        tk.Button(act_frame, text="预览对比",
                  font=("Microsoft YaHei", 10),
                  command=self._preview_compare).pack(side="left", padx=(0, 6))

        tk.Button(act_frame, text="提取全部图片",
                  font=("Microsoft YaHei", 10),
                  command=self._extract_images).pack(side="left", padx=(0, 6))

        self._progress = ttk.Progressbar(act_frame, length=120,
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

    # ── 逐图管理 ──

    def _open_image_manager(self):
        if not self._files:
            messagebox.showwarning("提示", "请先添加 PDF 文件")
            return
        # 使用列表中选中的文件，没选中就用第一个
        sel = self._file_listbox.curselection()
        idx = sel[0] if sel else 0
        pdf_path = self._files[idx]

        ImageManagerWindow(
            self,
            pdf_path=pdf_path,
            default_quality=self._quality_var.get(),
            default_max_dim=self._get_max_dim(),
            suffix=self._suffix_var.get(),
            clean_meta=self._clean_meta_var.get(),
            log_func=self._log_msg,
        )

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

    # ── 压缩核心（全局统一质量）──

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
                                replace_xref_image(doc, xref, new_bytes, new_pil)

                                diff = orig_size - new_size
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
                           f"  {format_size(before_size)} → "
                           f"{format_size(after_size)}  "
                           f"压缩 {ratio:.1f}%  "
                           f"({compressed_count}/{img_count} 张图片已压缩)")
                self.after(0, self._log_msg, f"    → {out_path}")

            except Exception as e:
                self.after(0, self._log_msg, f"  {name} 失败: {e}")

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
