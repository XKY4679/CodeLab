"""
CodeLab 工具箱启动器
统一入口，分类展示所有工具，点击即可启动
新增工具只需在 TOOLS 列表中添加一行即可
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import sys

WINDOW_WIDTH = 680
WINDOW_HEIGHT = 640

# ── 工具注册表 ──────────────────────────────────────
# 新增工具只需在对应分类下添加一行：(工具名, 子文件夹, 脚本文件名, 依赖说明)
# 依赖说明填 "" 表示无需额外安装

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TOOLS = {
    "图片工具": [
        ("批量图片压缩",   "批量图片压缩",   "ImageCompress.py",     "Pillow"),
        ("图片格式转换",   "图片格式转换",   "FormatConverter.py",   "Pillow"),
        ("批量加水印",     "批量加水印",     "Watermark.py",         "Pillow"),
        ("GIF 制作工具",   "GIF制作工具",    "GifMaker.py",          "Pillow"),
        ("色卡提取器",     "色卡提取器",     "ColorExtractor.py",    "Pillow"),
        ("波普效果生成器", "波普效果生成器", "PopArt.py",            "Pillow"),
        ("图片拼接工具",   "图片拼接工具",   "ImageStitcher.py",     "Pillow"),
        ("App 图标生成器", "App图标生成器",  "IconGenerator.py",     "Pillow"),
    ],
    "音视频工具": [
        ("批量压缩视频",   "批量压缩视频",   "VideoCompression_2.0.py", "ffmpeg（系统）"),
        ("Mp3 歌词嵌入",   "Mp3嵌入歌词",    "Embed_lyrics_2.0.py",    "mutagen"),
        ("音频波形图",     "音频波形图",     "Waveform.py",             "pydub Pillow"),
    ],
    "文档工具": [
        ("PDF 合并拆分",   "PDF合并拆分",    "PDFTool.py",           "PyPDF2"),
        ("PDF 压缩工具",   "PDF压缩工具",    "PDFCompressor.py",     "PyMuPDF Pillow"),
        ("刷题程序 3.0",   "刷题程序",       "答题系统_3.0.py",       "pandas openpyxl"),
        ("MD 与 PDF 互转", "Markdown与PDF互转", "MarkdownPDF.py",   "fpdf2 pdfplumber"),
    ],
    "实用工具": [
        ("批量重命名",     "批量重命名",     "BatchRename.py",       ""),
        ("局域网传文件",   "局域网传文件",   "LANShare.py",          ""),
        ("字体预览工具",   "字体预览工具",   "FontPreview.py",       ""),
        ("二维码生成器",   "二维码生成器",   "QRCode.py",            "qrcode Pillow"),
        ("调色板生成器",   "调色板生成器",   "PaletteGenerator.py",  "Pillow"),
        ("文本去重工具",   "文本去重工具",   "Deduplicate.py",       ""),
        ("HTML图片提取器", "HTML图片提取器", "HTMLImageExtractor.py", ""),
        ("网页截图工具",   "网页截图工具",   "WebCapture.py",        "playwright Pillow"),
        ("屏幕取色器",     "屏幕取色器",     "ColorPicker.py",       "Pillow"),
        ("代码截图美化",   "代码截图美化",   "CodeScreenshot.py",    "Pillow pygments"),
        ("ASCII艺术生成器","ASCII艺术生成器","ASCIIArt.py",          "Pillow"),
    ],
}

# 分类图标用纯文字代替（避免依赖图片资源）
CATEGORY_ICONS = {
    "图片工具":   "[图]",
    "音视频工具": "[媒]",
    "文档工具":   "[文]",
    "实用工具":   "[用]",
}


def launch_tool(folder, script):
    """启动工具脚本（独立进程）"""
    script_path = os.path.join(BASE_DIR, folder, script)
    if not os.path.isfile(script_path):
        messagebox.showerror("启动失败", f"找不到文件：\n{script_path}")
        return
    try:
        subprocess.Popen(
            [sys.executable, script_path],
            cwd=os.path.join(BASE_DIR, folder),
        )
    except Exception as e:
        messagebox.showerror("启动失败", str(e))


class LauncherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("業的工具箱")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self.configure(bg="#f5f5f5")

        self._build_ui()

    def _build_ui(self):
        # ── 顶部标题 ────────────────────────────────
        header = tk.Frame(self, bg="#1a73e8", height=70)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="業的工具箱",
                 font=("Microsoft YaHei", 22, "bold"), fg="white", bg="#1a73e8").pack(side="left", padx=25, pady=15)

        tool_count = sum(len(v) for v in TOOLS.values())
        tk.Label(header, text=f"{tool_count} 个工具",
                 font=("Microsoft YaHei", 11), fg="#bbdefb", bg="#1a73e8").pack(side="right", padx=25)

        # ── 搜索栏 ──────────────────────────────────
        search_bar = tk.Frame(self, bg="#f5f5f5")
        search_bar.pack(fill="x", padx=20, pady=(12, 5))

        tk.Label(search_bar, text="搜索：", font=("Microsoft YaHei", 10), bg="#f5f5f5").pack(side="left")
        self._search_var = tk.StringVar()
        self._search_entry = tk.Entry(search_bar, textvariable=self._search_var,
                                       font=("Microsoft YaHei", 11), width=25)
        self._search_entry.pack(side="left", padx=(0, 10))
        self._search_var.trace_add("write", lambda *_: self._refresh())

        self._result_label = tk.Label(search_bar, text="", font=("Microsoft YaHei", 9), fg="#888", bg="#f5f5f5")
        self._result_label.pack(side="right")

        # ── 滚动区域 ────────────────────────────────
        outer = tk.Frame(self, bg="#f5f5f5")
        outer.pack(fill="both", expand=True, padx=15, pady=5)

        self._canvas = tk.Canvas(outer, bg="#f5f5f5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=self._canvas.yview)
        self._inner = tk.Frame(self._canvas, bg="#f5f5f5")

        self._inner.bind("<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.create_window((0, 0), window=self._inner, anchor="nw",
                                   width=WINDOW_WIDTH - 50)
        self._canvas.configure(yscrollcommand=scrollbar.set)

        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._canvas.bind_all("<MouseWheel>",
                              lambda e: self._canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        # ── 底部 ─────────────────────────────────────
        footer = tk.Frame(self, bg="#f5f5f5")
        footer.pack(fill="x", padx=20, pady=(0, 10))

        tk.Label(footer, text="一键安装全部依赖：pip install pandas openpyxl python-docx mutagen Pillow PyPDF2",
                 font=("Consolas", 8), fg="#aaa", bg="#f5f5f5").pack()

        self._refresh()

    def _refresh(self):
        """根据搜索关键字刷新工具列表"""
        for w in self._inner.winfo_children():
            w.destroy()

        keyword = self._search_var.get().strip().lower()
        shown = 0

        for category, tools in TOOLS.items():
            # 过滤
            filtered = [t for t in tools if not keyword or keyword in t[0].lower()]
            if not filtered:
                continue

            icon = CATEGORY_ICONS.get(category, "")

            # 分类标题
            cat_frame = tk.Frame(self._inner, bg="#f5f5f5")
            cat_frame.pack(fill="x", pady=(12, 4), padx=5)
            tk.Label(cat_frame, text=f" {icon}  {category}",
                     font=("Microsoft YaHei", 12, "bold"), bg="#f5f5f5", fg="#333").pack(side="left")
            tk.Frame(cat_frame, bg="#ddd", height=1).pack(side="left", fill="x", expand=True, padx=(10, 0), pady=8)

            # 工具卡片
            for name, folder, script, deps in filtered:
                self._make_card(name, folder, script, deps)
                shown += 1

        self._result_label.config(text=f"显示 {shown} 个工具" if keyword else "")

    def _make_card(self, name, folder, script, deps):
        """创建一个工具卡片"""
        card = tk.Frame(self._inner, bg="white", relief="groove", bd=1, cursor="hand2")
        card.pack(fill="x", padx=8, pady=3)

        inner = tk.Frame(card, bg="white")
        inner.pack(fill="x", padx=12, pady=10)

        # 左侧信息
        tk.Label(inner, text=name, font=("Microsoft YaHei", 12, "bold"),
                 bg="white", fg="#333").pack(side="left")

        # 依赖标签
        if deps:
            tk.Label(inner, text=f"依赖: {deps}", font=("Microsoft YaHei", 8),
                     bg="#fff3e0", fg="#e65100", padx=6, pady=1).pack(side="left", padx=(10, 0))
        else:
            tk.Label(inner, text="无需安装", font=("Microsoft YaHei", 8),
                     bg="#e8f5e9", fg="#2e7d32", padx=6, pady=1).pack(side="left", padx=(10, 0))

        # 启动按钮
        btn = tk.Button(inner, text="启动", font=("Microsoft YaHei", 10, "bold"),
                        bg="#1a73e8", fg="white", activebackground="#1557b0", activeforeground="white",
                        relief="flat", padx=14, pady=2,
                        command=lambda f=folder, s=script: launch_tool(f, s))
        btn.pack(side="right")

        # 整行点击也能启动
        for widget in (card, inner):
            widget.bind("<Button-1>", lambda e, f=folder, s=script: launch_tool(f, s))


if __name__ == "__main__":
    app = LauncherApp()
    app.mainloop()
