"""
HTML 图片提取器 —— GUI 图形窗口版
从 HTML 文件中一键提取所有图片/图标
支持 Base64 内嵌图、外部引用图、内联 SVG、CSS 背景图、Favicon
无需额外依赖
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import re
import base64
import shutil
import hashlib
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import urlretrieve

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 640

# 支持的图片扩展名
IMG_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp",
                  ".svg", ".ico", ".tiff", ".tif", ".avif"}

# Base64 data URI 正则
RE_DATA_URI = re.compile(
    r'data:image/([a-zA-Z0-9+.-]+);base64,([A-Za-z0-9+/=\s]+)',
    re.DOTALL)

# CSS url() 正则
RE_CSS_URL = re.compile(
    r'url\s*\(\s*["\']?\s*([^"\')\s]+)\s*["\']?\s*\)', re.IGNORECASE)

# 内联 SVG 正则（匹配完整 <svg>...</svg>）
RE_SVG = re.compile(r'(<svg[^>]*>[\s\S]*?</svg>)', re.IGNORECASE)


class ImageInfo:
    """提取到的图片信息"""
    def __init__(self, source_type, name, data=None, path=None, url=None,
                 fmt="png", tag_info=""):
        self.source_type = source_type   # base64 / file / url / svg / css
        self.name = name                 # 显示名称
        self.data = data                 # 二进制数据（base64 解码后）
        self.path = path                 # 本地文件路径
        self.url = url                   # 网络 URL
        self.fmt = fmt                   # 格式后缀
        self.tag_info = tag_info         # 来源标签信息
        self.size_str = ""               # 文件大小字符串


def extract_images_from_html(html_text, html_dir=""):
    """
    解析 HTML 文本，提取所有图片信息
    html_dir: HTML 文件所在目录，用于解析相对路径
    返回 [ImageInfo, ...]
    """
    results = []
    seen = set()  # 去重

    def _add(info):
        # 用内容哈希去重
        key = info.name + info.source_type
        if info.data:
            key = hashlib.md5(info.data[:200] if len(info.data) > 200
                              else info.data).hexdigest()
        if key not in seen:
            seen.add(key)
            results.append(info)

    # ── 1. 提取 Base64 内嵌图 ──
    for i, m in enumerate(RE_DATA_URI.finditer(html_text)):
        fmt = m.group(1).split("+")[0].split(";")[0]  # image/svg+xml → svg
        b64_data = m.group(2).replace("\n", "").replace("\r", "").replace(" ", "")
        try:
            raw = base64.b64decode(b64_data)
            ext = fmt if fmt != "jpeg" else "jpg"
            name = f"base64_{i + 1}.{ext}"
            info = ImageInfo("base64", name, data=raw, fmt=ext,
                             tag_info=f"Base64 内嵌 ({fmt})")
            info.size_str = _format_size(len(raw))
            _add(info)
        except Exception:
            pass

    # ── 2. 解析 HTML 标签 ──
    parser = _ImageHTMLParser(html_dir, results, seen)
    try:
        parser.feed(html_text)
    except Exception:
        pass

    # ── 3. 提取 CSS 中的 url() 引用 ──
    # 先取 <style> 块
    style_blocks = re.findall(r'<style[^>]*>([\s\S]*?)</style>',
                              html_text, re.IGNORECASE)
    # 加上 style="" 属性
    style_attrs = re.findall(r'style\s*=\s*["\']([^"\']*)["\']',
                             html_text, re.IGNORECASE)
    all_css = "\n".join(style_blocks + style_attrs)

    for m in RE_CSS_URL.finditer(all_css):
        url = m.group(1).strip()
        if url.startswith("data:image"):
            continue  # 已在 base64 中处理
        if url.startswith("data:"):
            continue

        ext = _guess_ext(url)
        if ext not in IMG_EXTENSIONS:
            continue

        name = _url_to_filename(url)
        abs_path = _resolve_path(url, html_dir)

        if abs_path and os.path.isfile(abs_path):
            info = ImageInfo("css", name, path=abs_path, fmt=ext.lstrip("."),
                             tag_info=f"CSS background-image")
            info.size_str = _format_size(os.path.getsize(abs_path))
            _add(info)
        elif url.startswith(("http://", "https://")):
            info = ImageInfo("css", name, url=url, fmt=ext.lstrip("."),
                             tag_info=f"CSS background-image (网络)")
            _add(info)

    # ── 4. 提取内联 SVG ──
    for i, m in enumerate(RE_SVG.finditer(html_text)):
        svg_code = m.group(1).strip()
        name = f"inline_svg_{i + 1}.svg"
        data = svg_code.encode("utf-8")
        info = ImageInfo("svg", name, data=data, fmt="svg",
                         tag_info="内联 SVG 代码")
        info.size_str = _format_size(len(data))
        _add(info)

    return results


class _ImageHTMLParser(HTMLParser):
    """解析 HTML 标签中的图片引用"""

    def __init__(self, html_dir, results, seen):
        super().__init__()
        self.html_dir = html_dir
        self.results = results
        self.seen = seen
        self._counter = {}

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        # <img src="...">
        if tag == "img":
            src = attrs_dict.get("src", "")
            if src and not src.startswith("data:"):
                self._add_ref(src, "img", f'<img src="{_shorten(src)}">')

        # <link rel="icon" href="..."> 或 <link rel="apple-touch-icon" ...>
        if tag == "link":
            rel = attrs_dict.get("rel", "").lower()
            href = attrs_dict.get("href", "")
            if href and not href.startswith("data:"):
                if "icon" in rel:
                    self._add_ref(href, "favicon",
                                  f'<link rel="{rel}" href="{_shorten(href)}">')

        # <source src="..."> (picture 元素)
        if tag == "source":
            src = attrs_dict.get("src", "") or attrs_dict.get("srcset", "")
            if src and not src.startswith("data:"):
                # srcset 可能含多个 URL
                first_url = src.split(",")[0].strip().split(" ")[0]
                self._add_ref(first_url, "source",
                              f'<source src="{_shorten(first_url)}">')

        # <input type="image" src="...">
        if tag == "input" and attrs_dict.get("type") == "image":
            src = attrs_dict.get("src", "")
            if src and not src.startswith("data:"):
                self._add_ref(src, "input", f'<input type="image">')

        # <video poster="...">
        if tag == "video":
            poster = attrs_dict.get("poster", "")
            if poster and not poster.startswith("data:"):
                self._add_ref(poster, "poster",
                              f'<video poster="{_shorten(poster)}">')

    def _add_ref(self, src, source_type, tag_info):
        ext = _guess_ext(src)
        if ext not in IMG_EXTENSIONS:
            # 没扩展名也可能是图片（如 favicon 无后缀），也加进来
            if source_type not in ("favicon",):
                return
            ext = ".ico"

        name = _url_to_filename(src)
        abs_path = _resolve_path(src, self.html_dir)

        key = name + source_type
        if key in self.seen:
            return
        self.seen.add(key)

        if abs_path and os.path.isfile(abs_path):
            info = ImageInfo(source_type, name, path=abs_path,
                             fmt=ext.lstrip("."), tag_info=tag_info)
            info.size_str = _format_size(os.path.getsize(abs_path))
            self.results.append(info)
        elif src.startswith(("http://", "https://")):
            info = ImageInfo(source_type, name, url=src,
                             fmt=ext.lstrip("."), tag_info=tag_info)
            info.size_str = "网络资源"
            self.results.append(info)


# ── 工具函数 ──

def _guess_ext(path_or_url):
    """猜测文件扩展名"""
    clean = path_or_url.split("?")[0].split("#")[0]
    ext = os.path.splitext(clean)[1].lower()
    return ext


def _url_to_filename(url):
    """从 URL/路径提取文件名"""
    clean = url.split("?")[0].split("#")[0]
    name = os.path.basename(clean)
    if not name or len(name) > 100:
        h = hashlib.md5(url.encode()).hexdigest()[:8]
        ext = _guess_ext(url) or ".png"
        name = f"image_{h}{ext}"
    return name


def _resolve_path(src, html_dir):
    """将 src 解析为本地绝对路径"""
    if src.startswith(("http://", "https://", "data:")):
        return None
    if src.startswith("//"):
        return None
    # 去掉 file:/// 前缀
    if src.startswith("file:///"):
        src = src[8:]

    if os.path.isabs(src):
        return src

    if html_dir:
        return os.path.normpath(os.path.join(html_dir, src))
    return None


def _shorten(text, max_len=40):
    """截断长文本"""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def _format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def save_image(info, output_dir, download_web=True):
    """
    保存单个图片到输出目录
    返回 (成功, 保存路径或错误信息)
    """
    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, info.name)

    # 避免重名
    base, ext = os.path.splitext(save_path)
    counter = 1
    while os.path.exists(save_path):
        save_path = f"{base}_{counter}{ext}"
        counter += 1

    try:
        if info.data:
            with open(save_path, "wb") as f:
                f.write(info.data)
            return True, save_path

        if info.path and os.path.isfile(info.path):
            shutil.copy2(info.path, save_path)
            return True, save_path

        if info.url and download_web:
            urlretrieve(info.url, save_path)
            return True, save_path

        return False, "无可用数据"
    except Exception as e:
        return False, str(e)


# ══════════════════════════════════════════════════════════
#  GUI
# ══════════════════════════════════════════════════════════

class HTMLImageExtractorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HTML 图片提取器")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self._images = []
        self._html_dir = ""
        self._build_ui()

    def _build_ui(self):
        # ── 顶部 ──
        top = tk.Frame(self)
        top.pack(fill="x", padx=16, pady=(16, 6))

        tk.Label(top, text="HTML 图片提取器",
                 font=("Microsoft YaHei", 16, "bold")).pack(side="left")
        tk.Label(top, text="从 HTML 中提取所有图片/图标",
                 font=("Microsoft YaHei", 10), fg="#888").pack(side="left", padx=12)

        # ── 文件选择 / 粘贴 ──
        mode_frame = tk.Frame(self)
        mode_frame.pack(fill="x", padx=16, pady=(0, 6))

        tk.Button(mode_frame, text="选择 HTML 文件",
                  font=("Microsoft YaHei", 10),
                  command=self._select_file).pack(side="left", padx=(0, 8))
        tk.Button(mode_frame, text="从剪贴板粘贴 HTML 代码",
                  font=("Microsoft YaHei", 10),
                  command=self._paste_html).pack(side="left", padx=(0, 8))
        tk.Button(mode_frame, text="选择文件夹（批量扫描）",
                  font=("Microsoft YaHei", 10),
                  command=self._select_folder).pack(side="left")

        self._file_label = tk.Label(self, text="",
                                    font=("Microsoft YaHei", 9), fg="#666")
        self._file_label.pack(anchor="w", padx=16)

        # ── 统计栏 ──
        self._stats_label = tk.Label(self, text="",
                                     font=("Microsoft YaHei", 10, "bold"),
                                     fg="#1a73e8")
        self._stats_label.pack(anchor="w", padx=16, pady=(4, 4))

        # ── 结果列表 ──
        list_frame = tk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        columns = ("name", "type", "source", "size", "info")
        self._tree = ttk.Treeview(list_frame, columns=columns,
                                  show="headings", selectmode="extended")

        self._tree.heading("name", text="文件名")
        self._tree.heading("type", text="格式")
        self._tree.heading("source", text="来源")
        self._tree.heading("size", text="大小")
        self._tree.heading("info", text="标签信息")

        self._tree.column("name", width=200)
        self._tree.column("type", width=60, anchor="center")
        self._tree.column("source", width=90, anchor="center")
        self._tree.column("size", width=80, anchor="center")
        self._tree.column("info", width=280)

        sb = ttk.Scrollbar(list_frame, orient="vertical",
                           command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # ── 底部按钮 ──
        btn_row = tk.Frame(self)
        btn_row.pack(fill="x", padx=16, pady=(0, 6))

        tk.Button(btn_row, text="全选",
                  font=("Microsoft YaHei", 10),
                  command=self._select_all).pack(side="left", padx=(0, 6))
        tk.Button(btn_row, text="取消全选",
                  font=("Microsoft YaHei", 10),
                  command=self._deselect_all).pack(side="left", padx=(0, 16))

        # 筛选
        tk.Label(btn_row, text="筛选：",
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self._filter_var = tk.StringVar(value="全部")
        filter_combo = ttk.Combobox(
            btn_row,
            values=["全部", "仅 PNG", "仅 JPG", "仅 SVG", "仅 ICO",
                    "仅 Base64", "仅本地文件", "仅网络资源"],
            textvariable=self._filter_var, state="readonly", width=12)
        filter_combo.pack(side="left", padx=4)
        filter_combo.bind("<<ComboboxSelected>>", self._apply_filter)

        # 下载选项
        self._download_var = tk.BooleanVar(value=True)
        tk.Checkbutton(btn_row, text="下载网络图片",
                       variable=self._download_var,
                       font=("Microsoft YaHei", 9)).pack(side="right")

        # 导出按钮
        export_row = tk.Frame(self)
        export_row.pack(fill="x", padx=16, pady=(0, 16))

        tk.Button(export_row, text="导出选中图片",
                  font=("Microsoft YaHei", 13, "bold"),
                  command=self._export_selected).pack(side="left", padx=(0, 10))
        tk.Button(export_row, text="导出全部",
                  font=("Microsoft YaHei", 12),
                  command=self._export_all).pack(side="left")

    # ── 文件操作 ──

    def _select_file(self):
        paths = filedialog.askopenfilenames(
            title="选择 HTML 文件",
            filetypes=[("HTML 文件", "*.html *.htm *.xhtml *.mhtml"),
                       ("所有文件", "*.*")])
        if not paths:
            return

        all_images = []
        for path in paths:
            html_dir = os.path.dirname(os.path.abspath(path))
            html_text = self._read_file(path)
            if html_text:
                images = extract_images_from_html(html_text, html_dir)
                all_images.extend(images)

        self._html_dir = os.path.dirname(os.path.abspath(paths[0]))
        names = ", ".join(os.path.basename(p) for p in paths)
        self._file_label.configure(text=f"文件：{names}")
        self._images = all_images
        self._populate_tree()

    def _paste_html(self):
        try:
            html_text = self.clipboard_get()
        except tk.TclError:
            messagebox.showwarning("提示", "剪贴板为空或不含文本内容")
            return

        if not html_text.strip():
            messagebox.showwarning("提示", "剪贴板为空")
            return

        self._html_dir = ""
        self._file_label.configure(text="来源：剪贴板粘贴")
        self._images = extract_images_from_html(html_text, "")
        self._populate_tree()

    def _select_folder(self):
        folder = filedialog.askdirectory(title="选择包含 HTML 文件的文件夹")
        if not folder:
            return

        all_images = []
        html_count = 0
        for root, dirs, files in os.walk(folder):
            for f in files:
                if f.lower().endswith((".html", ".htm", ".xhtml")):
                    path = os.path.join(root, f)
                    html_text = self._read_file(path)
                    if html_text:
                        html_dir = os.path.dirname(os.path.abspath(path))
                        images = extract_images_from_html(html_text, html_dir)
                        all_images.extend(images)
                        html_count += 1

        self._html_dir = folder
        self._file_label.configure(
            text=f"文件夹：{folder}（扫描了 {html_count} 个 HTML 文件）")
        self._images = all_images
        self._populate_tree()

    def _read_file(self, path):
        encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1"]
        for enc in encodings:
            try:
                with open(path, "r", encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
        return None

    # ── 列表操作 ──

    def _populate_tree(self):
        self._tree.delete(*self._tree.get_children())

        source_names = {
            "base64": "Base64 内嵌",
            "img": "img 标签",
            "favicon": "Favicon",
            "css": "CSS 背景",
            "svg": "内联 SVG",
            "source": "source 标签",
            "input": "input 标签",
            "poster": "video 封面",
        }

        for i, img in enumerate(self._images):
            source = source_names.get(img.source_type, img.source_type)
            self._tree.insert("", "end", iid=str(i),
                              values=(img.name, img.fmt.upper(), source,
                                      img.size_str, img.tag_info))

        # 统计
        n = len(self._images)
        types = {}
        for img in self._images:
            t = img.fmt.upper()
            types[t] = types.get(t, 0) + 1
        type_str = "  ".join(f"{k}:{v}" for k, v in sorted(types.items()))

        self._stats_label.configure(
            text=f"共找到 {n} 个图片/图标    {type_str}" if n else "未找到任何图片")

    def _apply_filter(self, event=None):
        f = self._filter_var.get()
        self._tree.delete(*self._tree.get_children())

        source_names = {
            "base64": "Base64 内嵌",
            "img": "img 标签",
            "favicon": "Favicon",
            "css": "CSS 背景",
            "svg": "内联 SVG",
            "source": "source 标签",
            "input": "input 标签",
            "poster": "video 封面",
        }

        for i, img in enumerate(self._images):
            show = True
            if f == "仅 PNG" and img.fmt.lower() != "png":
                show = False
            elif f == "仅 JPG" and img.fmt.lower() not in ("jpg", "jpeg"):
                show = False
            elif f == "仅 SVG" and img.fmt.lower() != "svg":
                show = False
            elif f == "仅 ICO" and img.fmt.lower() != "ico":
                show = False
            elif f == "仅 Base64" and img.source_type != "base64":
                show = False
            elif f == "仅本地文件" and not img.path:
                show = False
            elif f == "仅网络资源" and not img.url:
                show = False

            if show:
                source = source_names.get(img.source_type, img.source_type)
                self._tree.insert("", "end", iid=str(i),
                                  values=(img.name, img.fmt.upper(), source,
                                          img.size_str, img.tag_info))

    def _select_all(self):
        for item in self._tree.get_children():
            self._tree.selection_add(item)

    def _deselect_all(self):
        self._tree.selection_remove(*self._tree.selection())

    # ── 导出 ──

    def _export_selected(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选中要导出的图片（按住 Ctrl 可多选）")
            return
        indices = [int(s) for s in sel]
        self._do_export([self._images[i] for i in indices])

    def _export_all(self):
        if not self._images:
            messagebox.showwarning("提示", "没有可导出的图片")
            return
        self._do_export(self._images)

    def _do_export(self, images):
        output_dir = filedialog.askdirectory(title="选择图片保存文件夹")
        if not output_dir:
            return

        success = 0
        fail = 0
        download_web = self._download_var.get()

        for img in images:
            ok, msg = save_image(img, output_dir, download_web)
            if ok:
                success += 1
            else:
                fail += 1

        result = f"导出完成！\n\n成功：{success} 个"
        if fail > 0:
            result += f"\n失败：{fail} 个"
        result += f"\n\n保存位置：\n{output_dir}"

        messagebox.showinfo("导出完成", result)
        os.startfile(output_dir)


if __name__ == "__main__":
    app = HTMLImageExtractorApp()
    app.mainloop()
