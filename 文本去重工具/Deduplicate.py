"""
文本去重工具 —— GUI 图形窗口版
粘贴文本，一键去除重复行
支持忽略大小写、去空白、排序等选项
无需额外依赖
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext

WINDOW_WIDTH = 700
WINDOW_HEIGHT = 600


def deduplicate(text, ignore_case=False, trim=True,
                skip_empty=True, sort_result=False, sort_reverse=False):
    """
    去重处理
    返回 (result_text, stats_dict)
    """
    lines = text.split("\n")
    total = len(lines)

    seen = set()
    result = []
    dup_count = 0

    for line in lines:
        processed = line
        if trim:
            processed = processed.strip()
        if skip_empty and processed == "":
            continue

        key = processed.lower() if ignore_case else processed

        if key in seen:
            dup_count += 1
        else:
            seen.add(key)
            result.append(processed)

    if sort_result:
        try:
            result.sort(key=str.lower, reverse=sort_reverse)
        except Exception:
            result.sort(reverse=sort_reverse)

    empty_skipped = sum(1 for line in lines
                        if (line.strip() == "" if trim else line == ""))

    stats = {
        "total": total,
        "unique": len(result),
        "duplicates": dup_count,
        "empty_skipped": empty_skipped if skip_empty else 0,
    }

    return "\n".join(result), stats


class DeduplicateApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("文本去重工具")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self._build_ui()

    def _build_ui(self):
        # 标题
        top = tk.Frame(self)
        top.pack(fill="x", padx=16, pady=(16, 8))

        tk.Label(top, text="文本去重工具",
                 font=("Microsoft YaHei", 16, "bold")).pack(side="left")
        tk.Label(top, text="粘贴文本 → 一键去除重复行",
                 font=("Microsoft YaHei", 10), fg="#888").pack(side="left", padx=12)

        # ── 主体：左右两栏 ──
        body = tk.Frame(self)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        # 左：输入
        left = tk.Frame(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 4))

        tk.Label(left, text="输入文本（每行一条）：",
                 font=("Microsoft YaHei", 10)).pack(anchor="w", pady=(0, 4))

        self._input_text = scrolledtext.ScrolledText(
            left, font=("Consolas", 10), wrap="none", bg="#fafafa")
        self._input_text.pack(fill="both", expand=True)

        self._input_count = tk.Label(left, text="0 行",
                                     font=("Microsoft YaHei", 9), fg="#888")
        self._input_count.pack(anchor="e", pady=(2, 0))

        # 绑定输入统计
        self._input_text.bind("<KeyRelease>", self._update_input_count)

        # 右：输出
        right = tk.Frame(body)
        right.pack(side="right", fill="both", expand=True, padx=(4, 0))

        tk.Label(right, text="去重结果：",
                 font=("Microsoft YaHei", 10)).pack(anchor="w", pady=(0, 4))

        self._output_text = scrolledtext.ScrolledText(
            right, font=("Consolas", 10), wrap="none", bg="#f5f5f0",
            state="disabled")
        self._output_text.pack(fill="both", expand=True)

        self._output_count = tk.Label(right, text="",
                                      font=("Microsoft YaHei", 9), fg="#888")
        self._output_count.pack(anchor="e", pady=(2, 0))

        # ── 中间：选项 + 按钮 ──
        option_row = tk.Frame(self)
        option_row.pack(fill="x", padx=16, pady=(4, 4))

        self._ignore_case_var = tk.BooleanVar(value=False)
        tk.Checkbutton(option_row, text="忽略大小写",
                       variable=self._ignore_case_var,
                       font=("Microsoft YaHei", 9)).pack(side="left", padx=(0, 8))

        self._trim_var = tk.BooleanVar(value=True)
        tk.Checkbutton(option_row, text="去除首尾空白",
                       variable=self._trim_var,
                       font=("Microsoft YaHei", 9)).pack(side="left", padx=(0, 8))

        self._skip_empty_var = tk.BooleanVar(value=True)
        tk.Checkbutton(option_row, text="跳过空行",
                       variable=self._skip_empty_var,
                       font=("Microsoft YaHei", 9)).pack(side="left", padx=(0, 8))

        self._sort_var = tk.BooleanVar(value=False)
        tk.Checkbutton(option_row, text="排序",
                       variable=self._sort_var,
                       font=("Microsoft YaHei", 9)).pack(side="left", padx=(0, 4))

        self._sort_rev_var = tk.BooleanVar(value=False)
        tk.Checkbutton(option_row, text="倒序",
                       variable=self._sort_rev_var,
                       font=("Microsoft YaHei", 9)).pack(side="left")

        # ── 底部按钮 ──
        btn_row = tk.Frame(self)
        btn_row.pack(fill="x", padx=16, pady=(4, 16))

        tk.Button(btn_row, text="去  重",
                  font=("Microsoft YaHei", 12, "bold"),
                  width=10, command=self._deduplicate).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="复制结果",
                  font=("Microsoft YaHei", 11),
                  width=10, command=self._copy_result).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="保存为文件",
                  font=("Microsoft YaHei", 11),
                  width=10, command=self._save_file).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="从文件导入",
                  font=("Microsoft YaHei", 11),
                  width=10, command=self._load_file).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="清空",
                  font=("Microsoft YaHei", 11),
                  width=6, command=self._clear).pack(side="left")

        # ── 统计栏 ──
        self._stats_label = tk.Label(self, text="",
                                     font=("Microsoft YaHei", 10), fg="#1a73e8")
        self._stats_label.pack(padx=16, pady=(0, 8), anchor="w")

    def _update_input_count(self, event=None):
        text = self._input_text.get("1.0", "end-1c")
        lines = text.split("\n")
        count = len(lines) if text.strip() else 0
        self._input_count.configure(text=f"{count} 行")

    def _deduplicate(self):
        text = self._input_text.get("1.0", "end-1c")
        if not text.strip():
            messagebox.showwarning("提示", "请先输入或粘贴文本")
            return

        result, stats = deduplicate(
            text,
            ignore_case=self._ignore_case_var.get(),
            trim=self._trim_var.get(),
            skip_empty=self._skip_empty_var.get(),
            sort_result=self._sort_var.get(),
            sort_reverse=self._sort_rev_var.get(),
        )

        self._output_text.configure(state="normal")
        self._output_text.delete("1.0", "end")
        self._output_text.insert("1.0", result)
        self._output_text.configure(state="disabled")

        self._output_count.configure(text=f"{stats['unique']} 行")

        stats_text = (f"原始 {stats['total']} 行  →  "
                      f"去重后 {stats['unique']} 行  |  "
                      f"删除 {stats['duplicates']} 个重复")
        if stats["empty_skipped"] > 0:
            stats_text += f"  |  跳过 {stats['empty_skipped']} 个空行"
        self._stats_label.configure(text=stats_text)

    def _copy_result(self):
        self._output_text.configure(state="normal")
        text = self._output_text.get("1.0", "end-1c").strip()
        self._output_text.configure(state="disabled")
        if not text:
            messagebox.showwarning("提示", "没有可复制的内容")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("已复制", "去重结果已复制到剪贴板")

    def _save_file(self):
        self._output_text.configure(state="normal")
        text = self._output_text.get("1.0", "end-1c").strip()
        self._output_text.configure(state="disabled")
        if not text:
            messagebox.showwarning("提示", "没有可保存的内容")
            return

        path = filedialog.asksaveasfilename(
            title="保存去重结果",
            defaultextension=".txt",
            initialfile="去重结果.txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if not path:
            return

        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        messagebox.showinfo("保存成功", f"已保存至：\n{path}")

    def _load_file(self):
        path = filedialog.askopenfilename(
            title="选择文本文件",
            filetypes=[("文本文件", "*.txt *.csv *.log *.md"),
                       ("所有文件", "*.*")])
        if not path:
            return

        encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312"]
        content = None
        for enc in encodings:
            try:
                with open(path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        if content is None:
            messagebox.showerror("读取失败", "无法识别文件编码")
            return

        self._input_text.delete("1.0", "end")
        self._input_text.insert("1.0", content)
        self._update_input_count()

    def _clear(self):
        self._input_text.delete("1.0", "end")
        self._output_text.configure(state="normal")
        self._output_text.delete("1.0", "end")
        self._output_text.configure(state="disabled")
        self._stats_label.configure(text="")
        self._input_count.configure(text="0 行")
        self._output_count.configure(text="")


if __name__ == "__main__":
    app = DeduplicateApp()
    app.mainloop()
