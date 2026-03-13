"""
字体预览工具 1.0 —— GUI 图形窗口版
输入一段文字，预览电脑上安装的所有字体效果
支持搜索、调整字号、导出预览图
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont
import os

WINDOW_WIDTH = 820
WINDOW_HEIGHT = 640


class FontPreviewApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("字体预览工具 1.0")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)

        # 获取所有字体
        self._all_fonts = sorted(set(tkfont.families()), key=str.lower)
        self._filtered = list(self._all_fonts)

        self._build_ui()

    def _build_ui(self):
        # ── 顶部控制栏 ──────────────────────────────
        top = tk.Frame(self)
        top.pack(fill="x", padx=15, pady=(12, 5))

        tk.Label(top, text="预览文字：", font=("Microsoft YaHei", 10)).pack(side="left")
        self._text_var = tk.StringVar(value="你好世界 Hello World 1234")
        text_entry = tk.Entry(top, textvariable=self._text_var, font=("Microsoft YaHei", 11), width=30)
        text_entry.pack(side="left", padx=(0, 15))
        self._text_var.trace_add("write", lambda *_: self._refresh_preview())

        tk.Label(top, text="字号：", font=("Microsoft YaHei", 10)).pack(side="left")
        self._size_var = tk.IntVar(value=28)
        size_spin = tk.Spinbox(top, from_=10, to=80, textvariable=self._size_var, width=4,
                               font=("Microsoft YaHei", 10), command=self._refresh_preview)
        size_spin.pack(side="left", padx=(0, 15))

        tk.Label(top, text="搜索：", font=("Microsoft YaHei", 10)).pack(side="left")
        self._search_var = tk.StringVar()
        search_entry = tk.Entry(top, textvariable=self._search_var, font=("Microsoft YaHei", 10), width=16)
        search_entry.pack(side="left")
        self._search_var.trace_add("write", lambda *_: self._do_search())

        # 字体计数
        self._count_label = tk.Label(top, text="", font=("Microsoft YaHei", 9), fg="#888")
        self._count_label.pack(side="right")

        # ── 分割：左侧字体列表 + 右侧预览 ────────────
        paned = tk.Frame(self)
        paned.pack(fill="both", expand=True, padx=15, pady=5)

        # 左侧字体列表
        left = tk.Frame(paned, width=240)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        tk.Label(left, text="字体列表", font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", pady=(0, 3))

        list_frame = tk.Frame(left)
        list_frame.pack(fill="both", expand=True)

        self._font_listbox = tk.Listbox(list_frame, font=("Microsoft YaHei", 10),
                                        selectmode="single", exportselection=False)
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self._font_listbox.yview)
        self._font_listbox.configure(yscrollcommand=sb.set)
        self._font_listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._font_listbox.bind("<<ListboxSelect>>", lambda e: self._on_font_select())

        # 填充
        for f in self._filtered:
            self._font_listbox.insert("end", f)

        # 右侧预览区
        right = tk.Frame(paned)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))

        tk.Label(right, text="预览效果", font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", pady=(0, 3))

        # 单个字体大预览
        self._single_frame = tk.LabelFrame(right, text="选中字体", font=("Microsoft YaHei", 9))
        self._single_frame.pack(fill="x", pady=(0, 8))

        self._single_name = tk.Label(self._single_frame, text="（点击左侧字体查看）",
                                     font=("Microsoft YaHei", 10), fg="#888")
        self._single_name.pack(anchor="w", padx=10, pady=(5, 0))

        self._single_preview = tk.Label(self._single_frame, text="",
                                        font=("Microsoft YaHei", 28), wraplength=500, justify="left")
        self._single_preview.pack(anchor="w", padx=10, pady=(5, 10))

        # 批量预览（滚动）
        tk.Label(right, text="批量预览", font=("Microsoft YaHei", 9, "bold")).pack(anchor="w", pady=(5, 3))

        scroll_frame = tk.Frame(right)
        scroll_frame.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(scroll_frame, bg="white")
        self._scroll = ttk.Scrollbar(scroll_frame, orient="vertical", command=self._canvas.yview)
        self._inner = tk.Frame(self._canvas, bg="white")

        self._inner.bind("<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas_window = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._canvas.configure(yscrollcommand=self._scroll.set)

        self._canvas.pack(side="left", fill="both", expand=True)
        self._scroll.pack(side="right", fill="y")

        # 鼠标滚轮
        self._canvas.bind_all("<MouseWheel>", lambda e: self._canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        # 底部按钮
        bottom = tk.Frame(self)
        bottom.pack(fill="x", padx=15, pady=(5, 12))

        tk.Button(bottom, text="复制字体名", font=("Microsoft YaHei", 10),
                  command=self._copy_font_name).pack(side="left", padx=4)

        self._update_count()
        self._refresh_preview()

    def _update_count(self):
        self._count_label.config(text=f"共 {len(self._filtered)} 个字体")

    def _do_search(self):
        keyword = self._search_var.get().strip().lower()
        if keyword:
            self._filtered = [f for f in self._all_fonts if keyword in f.lower()]
        else:
            self._filtered = list(self._all_fonts)

        self._font_listbox.delete(0, "end")
        for f in self._filtered:
            self._font_listbox.insert("end", f)
        self._update_count()
        self._refresh_preview()

    def _on_font_select(self):
        sel = self._font_listbox.curselection()
        if not sel:
            return
        font_name = self._filtered[sel[0]]
        size = self._size_var.get()
        text = self._text_var.get() or "预览文字"

        self._single_name.config(text=font_name, fg="#1a73e8")
        try:
            self._single_preview.config(text=text, font=(font_name, size))
        except Exception:
            self._single_preview.config(text="(该字体无法预览)", font=("Microsoft YaHei", 14))

    def _refresh_preview(self):
        """刷新批量预览区"""
        for w in self._inner.winfo_children():
            w.destroy()

        text = self._text_var.get() or "预览文字"
        size = self._size_var.get()

        # 最多显示 50 个（太多会卡）
        show_list = self._filtered[:50]

        for font_name in show_list:
            row = tk.Frame(self._inner, bg="white")
            row.pack(fill="x", padx=5, pady=2)

            tk.Label(row, text=font_name, font=("Microsoft YaHei", 9), fg="#888",
                     bg="white", width=24, anchor="w").pack(side="left")
            try:
                tk.Label(row, text=text, font=(font_name, min(size, 24)),
                         bg="white", anchor="w").pack(side="left", padx=(10, 0))
            except Exception:
                tk.Label(row, text="(无法预览)", font=("Microsoft YaHei", 10),
                         fg="#ccc", bg="white").pack(side="left", padx=(10, 0))

        if len(self._filtered) > 50:
            tk.Label(self._inner, text=f"... 还有 {len(self._filtered) - 50} 个字体，请使用搜索缩小范围",
                     font=("Microsoft YaHei", 9), fg="#999", bg="white").pack(pady=5)

    def _copy_font_name(self):
        sel = self._font_listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一个字体。")
            return
        name = self._filtered[sel[0]]
        self.clipboard_clear()
        self.clipboard_append(name)
        messagebox.showinfo("已复制", f"已复制字体名：{name}")


if __name__ == "__main__":
    app = FontPreviewApp()
    app.mainloop()
