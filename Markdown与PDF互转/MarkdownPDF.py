"""
Markdown 与 PDF 互转工具 —— GUI 图形窗口版
支持 Markdown → PDF（中文排版）和 PDF → Markdown
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import re

DEP_MISSING = []
try:
    from fpdf import FPDF
except ImportError:
    DEP_MISSING.append("fpdf2")
try:
    import pdfplumber
except ImportError:
    DEP_MISSING.append("pdfplumber")

WINDOW_WIDTH = 780
WINDOW_HEIGHT = 620

# ── 字体路径 ──
WIN_DIR = os.environ.get("WINDIR", "C:\\Windows")
FONT_REGULAR = os.path.join(WIN_DIR, "Fonts", "msyh.ttc")
FONT_BOLD = os.path.join(WIN_DIR, "Fonts", "msyhbd.ttc")
FONT_MONO = os.path.join(WIN_DIR, "Fonts", "consola.ttf")


# ══════════════════════════════════════════════════════════
#  Markdown → PDF 转换核心
# ══════════════════════════════════════════════════════════

class MarkdownRenderer(FPDF):
    """解析 Markdown 并渲染为 PDF（支持中文）"""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(True, margin=20)

        # 注册中文字体
        if os.path.isfile(FONT_REGULAR):
            self.add_font("zh", "", FONT_REGULAR)
        if os.path.isfile(FONT_BOLD):
            self.add_font("zh", "B", FONT_BOLD)

        self._has_zh = os.path.isfile(FONT_REGULAR)
        self._base_font = "zh" if self._has_zh else "Helvetica"

    # ── 渲染入口 ──

    def render_markdown(self, md_text):
        self.add_page()
        self.set_font(self._base_font, "", 11)

        lines = md_text.replace("\r\n", "\n").split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]

            # 代码块 ```
            if line.strip().startswith("```"):
                i += 1
                code_lines = []
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                i += 1  # 跳过结尾 ```
                self._render_code_block("\n".join(code_lines))
                continue

            # 标题 # ~ ####
            m = re.match(r"^(#{1,4})\s+(.+)$", line)
            if m:
                self._render_heading(m.group(2).strip(), len(m.group(1)))
                i += 1
                continue

            # 分割线
            if re.match(r"^\s*[-*_]{3,}\s*$", line):
                self._render_hr()
                i += 1
                continue

            # 无序列表
            m = re.match(r"^(\s*)([-*+])\s+(.+)$", line)
            if m:
                indent = len(m.group(1)) // 2
                self._render_list_item(m.group(3), indent, ordered=False)
                i += 1
                continue

            # 有序列表
            m = re.match(r"^(\s*)(\d+)\.\s+(.+)$", line)
            if m:
                indent = len(m.group(1)) // 2
                self._render_list_item(m.group(3), indent,
                                       ordered=True, num=m.group(2))
                i += 1
                continue

            # 引用 >
            m = re.match(r"^>\s?(.*)", line)
            if m:
                self._render_blockquote(m.group(1))
                i += 1
                continue

            # 空行
            if line.strip() == "":
                self.ln(3)
                i += 1
                continue

            # 普通段落
            self._render_paragraph(line)
            i += 1

    # ── 渲染各元素 ──

    def _render_heading(self, text, level):
        sizes = {1: 22, 2: 18, 3: 15, 4: 13}
        size = sizes.get(level, 11)
        self.ln(3)
        style = "B" if self._has_zh else "B"
        self.set_font(self._base_font, style, size)
        self.multi_cell(w=0, h=size * 0.55, text=self._strip_inline(text))
        self.ln(3)
        if level <= 2:
            y = self.get_y()
            self.set_draw_color(200, 200, 200)
            self.line(self.l_margin, y, self.w - self.r_margin, y)
            self.ln(2)
            self.set_draw_color(0, 0, 0)
        self.set_font(self._base_font, "", 11)

    def _render_paragraph(self, text):
        self.set_font(self._base_font, "", 11)
        self.multi_cell(w=0, h=6, text=self._strip_inline(text))
        self.ln(2)

    def _render_list_item(self, text, indent=0, ordered=False, num="1"):
        self.set_font(self._base_font, "", 11)
        x = self.l_margin + 6 + indent * 8
        prefix = f"{num}. " if ordered else "\u2022 "
        self.set_x(x)
        self.multi_cell(w=self.w - x - self.r_margin, h=6,
                        text=prefix + self._strip_inline(text))
        self.ln(1)

    def _render_blockquote(self, text):
        self.set_font(self._base_font, "", 11)
        x = self.l_margin + 8
        # 左侧竖线
        y_top = self.get_y()
        self.set_x(x + 4)
        self.set_text_color(100, 100, 100)
        self.multi_cell(w=self.w - x - 4 - self.r_margin, h=6,
                        text=self._strip_inline(text))
        y_bot = self.get_y()
        self.set_draw_color(180, 180, 180)
        self.set_line_width(0.8)
        self.line(x, y_top, x, y_bot)
        self.set_line_width(0.2)
        self.set_draw_color(0, 0, 0)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def _render_code_block(self, code):
        self.ln(2)
        self.set_fill_color(245, 245, 245)
        self.set_font(self._base_font, "", 9)
        for line in code.split("\n"):
            self.set_x(self.l_margin + 4)
            self.cell(w=self.w - self.l_margin - self.r_margin - 8,
                      h=5, text="  " + line, fill=True,
                      new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_font(self._base_font, "", 11)

    def _render_hr(self):
        self.ln(4)
        y = self.get_y()
        self.set_draw_color(180, 180, 180)
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.set_draw_color(0, 0, 0)
        self.ln(4)

    @staticmethod
    def _strip_inline(text):
        """去除 Markdown 行内标记，保留纯文本"""
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"__(.+?)__", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"_(.+?)_", r"\1", text)
        text = re.sub(r"~~(.+?)~~", r"\1", text)
        text = re.sub(r"`(.+?)`", r"\1", text)
        text = re.sub(r"!\[.*?\]\(.*?\)", "[图片]", text)
        text = re.sub(r"\[(.+?)\]\(.*?\)", r"\1", text)
        return text


def md_to_pdf(md_path, pdf_path):
    """Markdown 文件转 PDF"""
    encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312"]
    md_text = None
    for enc in encodings:
        try:
            with open(md_path, "r", encoding=enc) as f:
                md_text = f.read()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if md_text is None:
        raise ValueError("无法读取文件，编码不支持")

    pdf = MarkdownRenderer()
    pdf.render_markdown(md_text)
    pdf.output(pdf_path)


# ══════════════════════════════════════════════════════════
#  PDF → Markdown 转换核心
# ══════════════════════════════════════════════════════════

def pdf_to_md(pdf_path):
    """PDF 提取文本并转为 Markdown 格式"""
    md_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            lines = []

            # 尝试用字符级信息检测标题
            chars = page.chars
            if chars:
                lines = _extract_with_font_info(chars, page)
            else:
                text = page.extract_text()
                if text:
                    lines = text.split("\n")

            if lines:
                md_pages.append("\n".join(lines))

    return ("\n\n---\n\n".join(md_pages)).strip()


def _extract_with_font_info(chars, page):
    """利用字符的字号信息做简单的标题检测"""
    if not chars:
        text = page.extract_text()
        return text.split("\n") if text else []

    # 按行分组（top 坐标接近的归为同一行）
    line_groups = []
    current_line = [chars[0]]
    for ch in chars[1:]:
        if abs(ch["top"] - current_line[-1]["top"]) < 3:
            current_line.append(ch)
        else:
            line_groups.append(current_line)
            current_line = [ch]
    if current_line:
        line_groups.append(current_line)

    # 计算常见字号（正文字号）
    all_sizes = [ch["size"] for ch in chars if ch["text"].strip()]
    if not all_sizes:
        text = page.extract_text()
        return text.split("\n") if text else []

    from collections import Counter
    size_counts = Counter(round(s, 1) for s in all_sizes)
    body_size = size_counts.most_common(1)[0][0]

    results = []
    for group in line_groups:
        text = "".join(ch["text"] for ch in group).strip()
        if not text:
            results.append("")
            continue

        avg_size = sum(ch["size"] for ch in group if ch["text"].strip())
        count = sum(1 for ch in group if ch["text"].strip())
        avg_size = avg_size / count if count else body_size

        # 根据字号判断标题级别
        ratio = avg_size / body_size
        if ratio > 1.6:
            results.append(f"# {text}")
        elif ratio > 1.3:
            results.append(f"## {text}")
        elif ratio > 1.1:
            results.append(f"### {text}")
        else:
            results.append(text)

    return results


# ══════════════════════════════════════════════════════════
#  GUI 界面
# ══════════════════════════════════════════════════════════

class MarkdownPDFApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Markdown 与 PDF 互转")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)

        if DEP_MISSING:
            self._dep_error()
        else:
            self._build_ui()

    def _dep_error(self):
        f = tk.Frame(self)
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="缺少依赖库", font=("Microsoft YaHei", 20, "bold"),
                 fg="#c62828").pack(pady=(0, 12))
        libs = " ".join(DEP_MISSING)
        tk.Label(f, text=f"pip install {libs}",
                 font=("Consolas", 14, "bold"), fg="#1a73e8").pack(pady=12)

    def _build_ui(self):
        # 标签页
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=12)

        self._tab_md2pdf = tk.Frame(nb)
        self._tab_pdf2md = tk.Frame(nb)
        nb.add(self._tab_md2pdf, text="  Markdown → PDF  ")
        nb.add(self._tab_pdf2md, text="  PDF → Markdown  ")

        self._build_md2pdf_tab()
        self._build_pdf2md_tab()

    # ── MD → PDF 标签页 ──

    def _build_md2pdf_tab(self):
        tab = self._tab_md2pdf

        # 标题
        tk.Label(tab, text="Markdown 转 PDF",
                 font=("Microsoft YaHei", 16, "bold")).pack(anchor="w",
                                                             padx=12, pady=(12, 6))
        tk.Label(tab, text="选择 .md 文件，转换为排版好的 PDF（支持中文）",
                 font=("Microsoft YaHei", 10), fg="#666").pack(anchor="w", padx=12)

        # 文件选择
        file_row = tk.Frame(tab)
        file_row.pack(fill="x", padx=12, pady=(12, 6))
        self._md_path_var = tk.StringVar()
        tk.Entry(file_row, textvariable=self._md_path_var,
                 font=("Microsoft YaHei", 10), state="readonly").pack(
            side="left", fill="x", expand=True, padx=(0, 8))
        tk.Button(file_row, text="选择 .md 文件",
                  font=("Microsoft YaHei", 10),
                  command=self._select_md).pack(side="right")

        # 预览
        tk.Label(tab, text="文件预览：", font=("Microsoft YaHei", 10)).pack(
            anchor="w", padx=12, pady=(8, 2))
        self._md_preview = scrolledtext.ScrolledText(
            tab, font=("Consolas", 10), height=16, wrap="word", state="disabled",
            bg="#fafafa")
        self._md_preview.pack(fill="both", expand=True, padx=12)

        # 按钮
        btn_row = tk.Frame(tab)
        btn_row.pack(fill="x", padx=12, pady=12)
        tk.Button(btn_row, text="转换为 PDF",
                  font=("Microsoft YaHei", 12, "bold"),
                  width=20, command=self._convert_md2pdf).pack()

    def _select_md(self):
        path = filedialog.askopenfilename(
            title="选择 Markdown 文件",
            filetypes=[("Markdown", "*.md *.markdown *.txt")])
        if not path:
            return
        self._md_path_var.set(path)

        # 读取预览
        encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312"]
        content = ""
        for enc in encodings:
            try:
                with open(path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        self._md_preview.configure(state="normal")
        self._md_preview.delete("1.0", "end")
        self._md_preview.insert("1.0", content)
        self._md_preview.configure(state="disabled")

    def _convert_md2pdf(self):
        md_path = self._md_path_var.get()
        if not md_path:
            messagebox.showwarning("提示", "请先选择 Markdown 文件")
            return

        # 默认保存路径
        base = os.path.splitext(md_path)[0]
        save_path = filedialog.asksaveasfilename(
            title="保存 PDF",
            initialfile=os.path.basename(base) + ".pdf",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")])
        if not save_path:
            return

        try:
            md_to_pdf(md_path, save_path)
            messagebox.showinfo("转换成功",
                                f"PDF 已保存至：\n{save_path}")
        except Exception as e:
            messagebox.showerror("转换失败", str(e))

    # ── PDF → MD 标签页 ──

    def _build_pdf2md_tab(self):
        tab = self._tab_pdf2md

        tk.Label(tab, text="PDF 转 Markdown",
                 font=("Microsoft YaHei", 16, "bold")).pack(anchor="w",
                                                             padx=12, pady=(12, 6))
        tk.Label(tab, text="从 PDF 中提取文本并转换为 Markdown 格式",
                 font=("Microsoft YaHei", 10), fg="#666").pack(anchor="w", padx=12)

        # 文件选择
        file_row = tk.Frame(tab)
        file_row.pack(fill="x", padx=12, pady=(12, 6))
        self._pdf_path_var = tk.StringVar()
        tk.Entry(file_row, textvariable=self._pdf_path_var,
                 font=("Microsoft YaHei", 10), state="readonly").pack(
            side="left", fill="x", expand=True, padx=(0, 8))
        tk.Button(file_row, text="选择 PDF 文件",
                  font=("Microsoft YaHei", 10),
                  command=self._select_pdf).pack(side="right")

        # 提取结果
        tk.Label(tab, text="提取结果（可编辑后保存）：",
                 font=("Microsoft YaHei", 10)).pack(anchor="w", padx=12, pady=(8, 2))
        self._pdf_result = scrolledtext.ScrolledText(
            tab, font=("Consolas", 10), height=16, wrap="word", bg="#fafafa")
        self._pdf_result.pack(fill="both", expand=True, padx=12)

        # 按钮
        btn_row = tk.Frame(tab)
        btn_row.pack(fill="x", padx=12, pady=12)
        tk.Button(btn_row, text="提取文本",
                  font=("Microsoft YaHei", 11),
                  command=self._extract_pdf).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="保存为 .md",
                  font=("Microsoft YaHei", 11, "bold"),
                  command=self._save_md).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="复制全部",
                  font=("Microsoft YaHei", 11),
                  command=self._copy_all).pack(side="left")

    def _select_pdf(self):
        path = filedialog.askopenfilename(
            title="选择 PDF 文件",
            filetypes=[("PDF", "*.pdf")])
        if path:
            self._pdf_path_var.set(path)

    def _extract_pdf(self):
        pdf_path = self._pdf_path_var.get()
        if not pdf_path:
            messagebox.showwarning("提示", "请先选择 PDF 文件")
            return
        try:
            md_text = pdf_to_md(pdf_path)
            self._pdf_result.delete("1.0", "end")
            self._pdf_result.insert("1.0", md_text)
            messagebox.showinfo("提取完成",
                                f"已提取 PDF 文本，可编辑后保存为 .md 文件")
        except Exception as e:
            messagebox.showerror("提取失败", str(e))

    def _save_md(self):
        content = self._pdf_result.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showwarning("提示", "没有可保存的内容，请先提取文本")
            return

        pdf_path = self._pdf_path_var.get()
        base = os.path.splitext(pdf_path)[0] if pdf_path else "output"
        save_path = filedialog.asksaveasfilename(
            title="保存 Markdown",
            initialfile=os.path.basename(base) + ".md",
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("文本文件", "*.txt")])
        if not save_path:
            return

        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("保存成功", f"已保存至：\n{save_path}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def _copy_all(self):
        content = self._pdf_result.get("1.0", "end-1c").strip()
        if not content:
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        messagebox.showinfo("已复制", "全部内容已复制到剪贴板")


if __name__ == "__main__":
    app = MarkdownPDFApp()
    app.mainloop()
