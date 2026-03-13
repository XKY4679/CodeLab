"""
PDF 合并拆分工具 1.0 —— GUI 图形窗口版
支持：多个 PDF 合并为一个 / 从 PDF 中提取指定页
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

try:
    from PyPDF2 import PdfReader, PdfWriter
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

WINDOW_WIDTH = 750
WINDOW_HEIGHT = 560


def format_size(b):
    if b < 1024:
        return f"{b} B"
    elif b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    else:
        return f"{b / (1024 * 1024):.2f} MB"


class PDFToolApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF 合并拆分工具 1.0")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)

        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        if not HAS_PYPDF2:
            self._show_dep_error()
        else:
            self._show_start_page()

    def _clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    def _show_dep_error(self):
        self._clear()
        f = tk.Frame(self.container)
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="缺少依赖库", font=("Microsoft YaHei", 20, "bold"), fg="#c62828").pack(pady=(0, 12))
        tk.Label(f, text="请在命令行中运行：", font=("Microsoft YaHei", 11)).pack()
        tk.Label(f, text="pip install PyPDF2", font=("Consolas", 14, "bold"), fg="#1a73e8").pack(pady=12)

    # ── 开始页面 ─────────────────────────────────────

    def _show_start_page(self):
        self._clear()
        f = tk.Frame(self.container)
        f.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(f, text="PDF 合并拆分工具", font=("Microsoft YaHei", 24, "bold")).pack(pady=(0, 6))
        tk.Label(f, text="多个 PDF 合一个 / 从 PDF 里抽取指定页",
                 font=("Microsoft YaHei", 10), fg="#666").pack(pady=(0, 35))

        tk.Button(f, text="合并多个 PDF", font=("Microsoft YaHei", 13),
                  width=20, height=2, command=self._show_merge_page).pack(pady=6)
        tk.Label(f, text="选择多个 PDF 文件，按顺序合并为一个",
                 font=("Microsoft YaHei", 9), fg="#999").pack(pady=(0, 16))

        tk.Button(f, text="拆分 / 提取页面", font=("Microsoft YaHei", 13),
                  width=20, height=2, command=self._show_split_page).pack(pady=6)
        tk.Label(f, text="从一个 PDF 中提取指定页码",
                 font=("Microsoft YaHei", 9), fg="#999").pack()

    # ══════════════════════════════════════════════════
    #  合并功能
    # ══════════════════════════════════════════════════

    def _show_merge_page(self):
        self._clear()
        self._merge_files = []

        top = tk.Frame(self.container)
        top.pack(fill="x", padx=20, pady=(15, 5))
        tk.Button(top, text="← 返回", font=("Microsoft YaHei", 10), command=self._show_start_page).pack(side="left")
        tk.Label(top, text="合并 PDF", font=("Microsoft YaHei", 14, "bold")).pack(side="left", padx=15)

        body = tk.Frame(self.container)
        body.pack(fill="both", expand=True, padx=20, pady=10)

        tk.Label(body, text="添加要合并的 PDF 文件（从上到下的顺序就是合并顺序）：",
                 font=("Microsoft YaHei", 10)).pack(anchor="w", pady=(0, 5))

        # 文件列表
        list_frame = tk.Frame(body)
        list_frame.pack(fill="both", expand=True)

        self._merge_listbox = tk.Listbox(list_frame, font=("Microsoft YaHei", 10), selectmode="single")
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self._merge_listbox.yview)
        self._merge_listbox.configure(yscrollcommand=sb.set)
        self._merge_listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # 操作按钮
        btn_col = tk.Frame(body)
        btn_col.pack(fill="x", pady=8)
        tk.Button(btn_col, text="添加文件", font=("Microsoft YaHei", 10), command=self._merge_add).pack(side="left", padx=4)
        tk.Button(btn_col, text="移除选中", font=("Microsoft YaHei", 10), command=self._merge_remove).pack(side="left", padx=4)
        tk.Button(btn_col, text="上移", font=("Microsoft YaHei", 10), command=lambda: self._merge_move(-1)).pack(side="left", padx=4)
        tk.Button(btn_col, text="下移", font=("Microsoft YaHei", 10), command=lambda: self._merge_move(1)).pack(side="left", padx=4)

        self._merge_info = tk.Label(body, text="已添加 0 个文件", font=("Microsoft YaHei", 9), fg="#666")
        self._merge_info.pack(anchor="w")

        tk.Button(body, text="合并并保存", font=("Microsoft YaHei", 13, "bold"),
                  width=16, height=2, command=self._do_merge).pack(pady=(10, 0))

    def _merge_add(self):
        paths = filedialog.askopenfilenames(title="选择 PDF 文件", filetypes=[("PDF", "*.pdf")])
        for p in paths:
            if p not in self._merge_files:
                self._merge_files.append(p)
                try:
                    pages = len(PdfReader(p).pages)
                except Exception:
                    pages = "?"
                self._merge_listbox.insert("end", f"  {os.path.basename(p)}    ({pages} 页, {format_size(os.path.getsize(p))})")
        self._merge_info.config(text=f"已添加 {len(self._merge_files)} 个文件")

    def _merge_remove(self):
        sel = self._merge_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self._merge_listbox.delete(idx)
        self._merge_files.pop(idx)
        self._merge_info.config(text=f"已添加 {len(self._merge_files)} 个文件")

    def _merge_move(self, direction):
        sel = self._merge_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self._merge_files):
            return
        # 交换
        self._merge_files[idx], self._merge_files[new_idx] = self._merge_files[new_idx], self._merge_files[idx]
        # 刷新列表
        text_a = self._merge_listbox.get(idx)
        text_b = self._merge_listbox.get(new_idx)
        self._merge_listbox.delete(idx)
        self._merge_listbox.insert(idx, text_b)
        self._merge_listbox.delete(new_idx)
        self._merge_listbox.insert(new_idx, text_a)
        self._merge_listbox.selection_clear(0, "end")
        self._merge_listbox.selection_set(new_idx)

    def _do_merge(self):
        if len(self._merge_files) < 2:
            messagebox.showwarning("提示", "请至少添加 2 个 PDF 文件。")
            return

        save_path = filedialog.asksaveasfilename(
            title="保存合并后的 PDF",
            defaultextension=".pdf",
            initialfile="合并结果.pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        if not save_path:
            return

        try:
            writer = PdfWriter()
            total_pages = 0
            for pdf_path in self._merge_files:
                reader = PdfReader(pdf_path)
                for page in reader.pages:
                    writer.add_page(page)
                    total_pages += 1

            with open(save_path, "wb") as f:
                writer.write(f)

            new_size = format_size(os.path.getsize(save_path))
            self._show_merge_result(True, f"合并完成：共 {total_pages} 页，文件大小 {new_size}\n{save_path}")
        except Exception as e:
            self._show_merge_result(False, str(e))

    def _show_merge_result(self, success, info):
        self._clear()
        f = tk.Frame(self.container)
        f.place(relx=0.5, rely=0.5, anchor="center")

        if success:
            tk.Label(f, text="合并成功", font=("Microsoft YaHei", 22, "bold"), fg="#2e7d32").pack(pady=(0, 15))
        else:
            tk.Label(f, text="合并失败", font=("Microsoft YaHei", 22, "bold"), fg="#c62828").pack(pady=(0, 15))

        tk.Label(f, text=info, font=("Microsoft YaHei", 11), wraplength=500, justify="center").pack(pady=(0, 20))

        btn_row = tk.Frame(f)
        btn_row.pack()
        tk.Button(btn_row, text="继续合并", font=("Microsoft YaHei", 11), width=12,
                  command=self._show_merge_page).pack(side="left", padx=6)
        tk.Button(btn_row, text="返回首页", font=("Microsoft YaHei", 11), width=12,
                  command=self._show_start_page).pack(side="left", padx=6)

    # ══════════════════════════════════════════════════
    #  拆分 / 提取功能
    # ══════════════════════════════════════════════════

    def _show_split_page(self):
        self._clear()
        self._split_pdf = None
        self._split_total = 0

        top = tk.Frame(self.container)
        top.pack(fill="x", padx=20, pady=(15, 5))
        tk.Button(top, text="← 返回", font=("Microsoft YaHei", 10), command=self._show_start_page).pack(side="left")
        tk.Label(top, text="拆分 / 提取页面", font=("Microsoft YaHei", 14, "bold")).pack(side="left", padx=15)

        body = tk.Frame(self.container)
        body.pack(fill="both", expand=True, padx=25, pady=10)

        # 选择 PDF
        tk.Label(body, text="选择要拆分的 PDF 文件：", font=("Microsoft YaHei", 11)).pack(anchor="w", pady=(10, 5))
        file_row = tk.Frame(body)
        file_row.pack(fill="x")
        self._split_label = tk.Label(file_row, text="未选择", font=("Microsoft YaHei", 10), fg="#999")
        self._split_label.pack(side="left", fill="x", expand=True)
        tk.Button(file_row, text="选择文件", font=("Microsoft YaHei", 10), command=self._pick_split_pdf).pack(side="right")

        self._split_info = tk.Label(body, text="", font=("Microsoft YaHei", 10), fg="#555")
        self._split_info.pack(anchor="w", pady=(8, 15))

        # 提取方式
        tk.Label(body, text="提取方式：", font=("Microsoft YaHei", 11, "bold")).pack(anchor="w", pady=(0, 5))

        self._split_mode = tk.StringVar(value="range")

        r1 = tk.Frame(body)
        r1.pack(fill="x", pady=3)
        tk.Radiobutton(r1, text="按页码范围提取", variable=self._split_mode, value="range",
                       font=("Microsoft YaHei", 10)).pack(side="left")
        self._range_var = tk.StringVar(value="1-5")
        tk.Entry(r1, textvariable=self._range_var, width=20, font=("Microsoft YaHei", 10)).pack(side="left", padx=10)
        tk.Label(r1, text='如：1-5 或 1,3,5,8-10', font=("Microsoft YaHei", 9), fg="#888").pack(side="left")

        r2 = tk.Frame(body)
        r2.pack(fill="x", pady=3)
        tk.Radiobutton(r2, text="每页拆成单独 PDF", variable=self._split_mode, value="each",
                       font=("Microsoft YaHei", 10)).pack(side="left")
        tk.Label(r2, text="（每页生成一个独立 PDF 文件）", font=("Microsoft YaHei", 9), fg="#888").pack(side="left", padx=10)

        # 执行
        self._split_btn = tk.Button(
            body, text="开始提取", font=("Microsoft YaHei", 13, "bold"),
            width=16, height=2, command=self._do_split, state="disabled",
        )
        self._split_btn.pack(pady=(25, 0))

    def _pick_split_pdf(self):
        path = filedialog.askopenfilename(title="选择 PDF", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        try:
            reader = PdfReader(path)
            self._split_total = len(reader.pages)
        except Exception as e:
            messagebox.showerror("错误", f"无法读取 PDF：{e}")
            return
        self._split_pdf = path
        self._split_label.config(text=os.path.basename(path), fg="#333")
        self._split_info.config(text=f"共 {self._split_total} 页，大小 {format_size(os.path.getsize(path))}")
        self._split_btn.config(state="normal")

    def _parse_pages(self, text, total):
        """解析页码表达式，如 '1-5,8,10-12'，返回 0-based 页码列表"""
        pages = set()
        for part in text.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-", 1)
                a, b = int(a.strip()), int(b.strip())
                for p in range(a, b + 1):
                    if 1 <= p <= total:
                        pages.add(p - 1)
            elif part.isdigit():
                p = int(part)
                if 1 <= p <= total:
                    pages.add(p - 1)
        return sorted(pages)

    def _do_split(self):
        if not self._split_pdf:
            return

        mode = self._split_mode.get()
        reader = PdfReader(self._split_pdf)
        stem = os.path.splitext(os.path.basename(self._split_pdf))[0]

        if mode == "range":
            pages = self._parse_pages(self._range_var.get(), self._split_total)
            if not pages:
                messagebox.showwarning("提示", "没有有效的页码。请检查输入。")
                return

            save_path = filedialog.asksaveasfilename(
                title="保存提取结果",
                defaultextension=".pdf",
                initialfile=f"{stem}_提取.pdf",
                filetypes=[("PDF", "*.pdf")],
            )
            if not save_path:
                return

            try:
                writer = PdfWriter()
                for idx in pages:
                    writer.add_page(reader.pages[idx])
                with open(save_path, "wb") as f:
                    writer.write(f)

                size = format_size(os.path.getsize(save_path))
                self._show_split_result(True, f"提取完成：共 {len(pages)} 页，文件大小 {size}\n{save_path}")
            except Exception as e:
                self._show_split_result(False, str(e))

        elif mode == "each":
            folder = filedialog.askdirectory(title="选择保存文件夹")
            if not folder:
                return

            try:
                for i, page in enumerate(reader.pages):
                    writer = PdfWriter()
                    writer.add_page(page)
                    out = os.path.join(folder, f"{stem}_第{i+1}页.pdf")
                    with open(out, "wb") as f:
                        writer.write(f)

                self._show_split_result(True, f"拆分完成：共 {self._split_total} 页，保存在\n{folder}")
            except Exception as e:
                self._show_split_result(False, str(e))

    def _show_split_result(self, success, info):
        self._clear()
        f = tk.Frame(self.container)
        f.place(relx=0.5, rely=0.5, anchor="center")

        if success:
            tk.Label(f, text="提取成功", font=("Microsoft YaHei", 22, "bold"), fg="#2e7d32").pack(pady=(0, 15))
        else:
            tk.Label(f, text="提取失败", font=("Microsoft YaHei", 22, "bold"), fg="#c62828").pack(pady=(0, 15))

        tk.Label(f, text=info, font=("Microsoft YaHei", 11), wraplength=500, justify="center").pack(pady=(0, 20))

        btn_row = tk.Frame(f)
        btn_row.pack()
        tk.Button(btn_row, text="继续拆分", font=("Microsoft YaHei", 11), width=12,
                  command=self._show_split_page).pack(side="left", padx=6)
        tk.Button(btn_row, text="返回首页", font=("Microsoft YaHei", 11), width=12,
                  command=self._show_start_page).pack(side="left", padx=6)


if __name__ == "__main__":
    app = PDFToolApp()
    app.mainloop()
