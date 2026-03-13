"""
批量重命名工具 1.0 —— GUI 图形窗口版
支持：加前缀 / 加后缀 / 加序号 / 查找替换
实时预览重命名效果，确认后一键执行
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

WINDOW_WIDTH = 780
WINDOW_HEIGHT = 600


def scan_files(folder):
    """列出文件夹中的所有文件（不含子文件夹、不含隐藏文件）"""
    items = []
    for f in sorted(os.listdir(folder)):
        full = os.path.join(folder, f)
        if os.path.isfile(full) and not f.startswith("."):
            items.append(f)
    return items


def generate_preview(files, mode, prefix, suffix, seq_start, seq_digits, find_str, replace_str):
    """根据规则生成新文件名预览列表，返回 [(旧名, 新名), ...]"""
    results = []
    for i, old_name in enumerate(files):
        stem, ext = os.path.splitext(old_name)

        if mode == "prefix":
            new_name = prefix + old_name
        elif mode == "suffix":
            new_name = stem + suffix + ext
        elif mode == "sequence":
            num = str(seq_start + i).zfill(seq_digits)
            new_name = f"{num}_{old_name}"
        elif mode == "replace":
            new_name = old_name.replace(find_str, replace_str)
        else:
            new_name = old_name

        results.append((old_name, new_name))
    return results


class BatchRenameApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("批量重命名工具 1.0")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)

        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)
        self._show_start_page()

    def _clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    # ── 开始页面 ─────────────────────────────────────

    def _show_start_page(self):
        self._clear()
        f = tk.Frame(self.container)
        f.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(f, text="批量重命名工具", font=("Microsoft YaHei", 24, "bold")).pack(pady=(0, 6))
        tk.Label(f, text="加前缀 / 加后缀 / 加序号 / 查找替换",
                 font=("Microsoft YaHei", 10), fg="#666").pack(pady=(0, 30))

        tk.Button(f, text="选择文件夹", font=("Microsoft YaHei", 13),
                  width=20, height=2, command=self._on_select).pack(pady=6)

        tk.Label(f, text="直接重命名原文件，操作前会显示预览供确认",
                 font=("Microsoft YaHei", 9), fg="#999").pack(pady=(10, 0))

    def _on_select(self):
        folder = filedialog.askdirectory(title="选择要重命名的文件夹")
        if not folder:
            return
        files = scan_files(folder)
        if not files:
            messagebox.showwarning("提示", "文件夹中没有文件。")
            return
        self._folder = folder
        self._files = files
        self._show_settings()

    # ── 设置 + 预览页面 ──────────────────────────────

    def _show_settings(self):
        self._clear()

        top = tk.Frame(self.container)
        top.pack(fill="x", padx=20, pady=(15, 5))
        tk.Button(top, text="← 返回", font=("Microsoft YaHei", 10), command=self._show_start_page).pack(side="left")
        tk.Label(top, text=f"共 {len(self._files)} 个文件", font=("Microsoft YaHei", 12, "bold")).pack(side="left", padx=15)

        body = tk.Frame(self.container)
        body.pack(fill="both", expand=True, padx=20, pady=5)

        # 模式选择
        mode_frame = tk.LabelFrame(body, text="重命名规则", font=("Microsoft YaHei", 10, "bold"))
        mode_frame.pack(fill="x", pady=(0, 8))

        self._mode = tk.StringVar(value="prefix")

        # 加前缀
        r1 = tk.Frame(mode_frame)
        r1.pack(fill="x", padx=10, pady=3)
        tk.Radiobutton(r1, text="加前缀", variable=self._mode, value="prefix",
                       font=("Microsoft YaHei", 10), command=self._refresh).pack(side="left")
        self._prefix_var = tk.StringVar(value="项目A_")
        self._prefix_entry = tk.Entry(r1, textvariable=self._prefix_var, width=20, font=("Microsoft YaHei", 10))
        self._prefix_entry.pack(side="left", padx=10)
        self._prefix_var.trace_add("write", lambda *_: self._refresh())

        # 加后缀
        r2 = tk.Frame(mode_frame)
        r2.pack(fill="x", padx=10, pady=3)
        tk.Radiobutton(r2, text="加后缀", variable=self._mode, value="suffix",
                       font=("Microsoft YaHei", 10), command=self._refresh).pack(side="left")
        self._suffix_var = tk.StringVar(value="_final")
        self._suffix_entry = tk.Entry(r2, textvariable=self._suffix_var, width=20, font=("Microsoft YaHei", 10))
        self._suffix_entry.pack(side="left", padx=10)
        tk.Label(r2, text="（加在扩展名前）", font=("Microsoft YaHei", 9), fg="#888").pack(side="left")
        self._suffix_var.trace_add("write", lambda *_: self._refresh())

        # 加序号
        r3 = tk.Frame(mode_frame)
        r3.pack(fill="x", padx=10, pady=3)
        tk.Radiobutton(r3, text="加序号", variable=self._mode, value="sequence",
                       font=("Microsoft YaHei", 10), command=self._refresh).pack(side="left")
        tk.Label(r3, text="起始", font=("Microsoft YaHei", 9)).pack(side="left", padx=(10, 2))
        self._seq_start = tk.StringVar(value="1")
        tk.Entry(r3, textvariable=self._seq_start, width=5, font=("Microsoft YaHei", 10)).pack(side="left")
        tk.Label(r3, text="位数", font=("Microsoft YaHei", 9)).pack(side="left", padx=(10, 2))
        self._seq_digits = tk.StringVar(value="3")
        tk.Entry(r3, textvariable=self._seq_digits, width=3, font=("Microsoft YaHei", 10)).pack(side="left")
        tk.Label(r3, text="（如 001_文件名.jpg）", font=("Microsoft YaHei", 9), fg="#888").pack(side="left", padx=5)
        self._seq_start.trace_add("write", lambda *_: self._refresh())
        self._seq_digits.trace_add("write", lambda *_: self._refresh())

        # 查找替换
        r4 = tk.Frame(mode_frame)
        r4.pack(fill="x", padx=10, pady=3)
        tk.Radiobutton(r4, text="查找替换", variable=self._mode, value="replace",
                       font=("Microsoft YaHei", 10), command=self._refresh).pack(side="left")
        tk.Label(r4, text="查找", font=("Microsoft YaHei", 9)).pack(side="left", padx=(10, 2))
        self._find_var = tk.StringVar()
        tk.Entry(r4, textvariable=self._find_var, width=14, font=("Microsoft YaHei", 10)).pack(side="left")
        tk.Label(r4, text="→ 替换为", font=("Microsoft YaHei", 9)).pack(side="left", padx=(8, 2))
        self._repl_var = tk.StringVar()
        tk.Entry(r4, textvariable=self._repl_var, width=14, font=("Microsoft YaHei", 10)).pack(side="left")
        self._find_var.trace_add("write", lambda *_: self._refresh())
        self._repl_var.trace_add("write", lambda *_: self._refresh())

        # 预览列表
        tk.Label(body, text="重命名预览：", font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", pady=(5, 3))

        cols = ("old", "arrow", "new")
        self._tree = ttk.Treeview(body, columns=cols, show="headings", height=10)
        self._tree.heading("old", text="原文件名")
        self._tree.heading("arrow", text="")
        self._tree.heading("new", text="新文件名")
        self._tree.column("old", width=300)
        self._tree.column("arrow", width=40, anchor="center")
        self._tree.column("new", width=300)
        sb = ttk.Scrollbar(body, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # 底部按钮
        btn_bar = tk.Frame(self.container)
        btn_bar.pack(fill="x", padx=20, pady=(8, 15))
        self._change_label = tk.Label(btn_bar, text="", font=("Microsoft YaHei", 9), fg="#666")
        self._change_label.pack(side="left")
        tk.Button(btn_bar, text="执行重命名", font=("Microsoft YaHei", 12, "bold"),
                  width=14, command=self._do_rename).pack(side="right")

        self._refresh()

    def _refresh(self):
        mode = self._mode.get()
        try:
            seq_start = int(self._seq_start.get()) if self._seq_start.get() else 1
            seq_digits = int(self._seq_digits.get()) if self._seq_digits.get() else 3
        except ValueError:
            seq_start, seq_digits = 1, 3

        preview = generate_preview(
            self._files, mode,
            prefix=self._prefix_var.get(),
            suffix=self._suffix_var.get(),
            seq_start=seq_start, seq_digits=seq_digits,
            find_str=self._find_var.get(),
            replace_str=self._repl_var.get(),
        )
        self._preview = preview

        # 更新列表
        for item in self._tree.get_children():
            self._tree.delete(item)

        changed = 0
        for old, new in preview:
            marker = "→" if old != new else "="
            self._tree.insert("", "end", values=(old, marker, new))
            if old != new:
                changed += 1

        self._change_label.config(text=f"将变更 {changed} / {len(preview)} 个文件名")

    def _do_rename(self):
        changes = [(old, new) for old, new in self._preview if old != new]
        if not changes:
            messagebox.showinfo("提示", "没有文件名需要变更。")
            return

        # 检查新文件名冲突
        new_names = [new for _, new in self._preview]
        if len(new_names) != len(set(new_names)):
            messagebox.showerror("错误", "存在重复的新文件名，请调整规则。")
            return

        ok = messagebox.askyesno("确认", f"即将重命名 {len(changes)} 个文件，确定执行？")
        if not ok:
            return

        success = 0
        errors = []
        # 先全部重命名为临时名（防止 A→B、B→A 冲突）
        temp_map = {}
        for old, new in changes:
            old_path = os.path.join(self._folder, old)
            tmp_path = os.path.join(self._folder, f"__rename_tmp_{id(old)}_{old}")
            try:
                os.rename(old_path, tmp_path)
                temp_map[tmp_path] = os.path.join(self._folder, new)
            except Exception as e:
                errors.append((old, str(e)))

        for tmp_path, new_path in temp_map.items():
            try:
                os.rename(tmp_path, new_path)
                success += 1
            except Exception as e:
                errors.append((os.path.basename(new_path), str(e)))

        self._show_result(success, errors)

    def _show_result(self, success, errors):
        self._clear()
        f = tk.Frame(self.container)
        f.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(f, text="重命名完成", font=("Microsoft YaHei", 22, "bold")).pack(pady=(0, 15))

        color = "#2e7d32" if not errors else "#e65100"
        tk.Label(f, text=f"成功 {success} 个", font=("Microsoft YaHei", 16, "bold"), fg=color).pack()

        if errors:
            tk.Label(f, text=f"失败 {len(errors)} 个", font=("Microsoft YaHei", 12), fg="#c62828").pack(pady=(5, 0))
            for name, err in errors[:5]:
                tk.Label(f, text=f"  {name}：{err}", font=("Microsoft YaHei", 9), fg="#c62828").pack(anchor="w", padx=20)

        btn_row = tk.Frame(f)
        btn_row.pack(pady=20)
        tk.Button(btn_row, text="打开文件夹", font=("Microsoft YaHei", 11), width=12,
                  command=lambda: os.startfile(self._folder)).pack(side="left", padx=6)
        tk.Button(btn_row, text="返回首页", font=("Microsoft YaHei", 11), width=12,
                  command=self._show_start_page).pack(side="left", padx=6)


if __name__ == "__main__":
    app = BatchRenameApp()
    app.mainloop()
