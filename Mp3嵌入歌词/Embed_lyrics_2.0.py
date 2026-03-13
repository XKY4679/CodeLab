"""
Mp3 歌词嵌入工具 2.0 —— GUI 图形窗口版
支持单曲嵌入 / 批量文件夹自动匹配
支持 .lrc / .txt 歌词文件
tkinter 界面，与答题系统 3.0 风格统一
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import re

# ── 第三方依赖 ──────────────────────────────────────
try:
    from mutagen.id3 import ID3, USLT, ID3NoHeaderError
    from mutagen.mp3 import MP3
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

# ── 配置 ────────────────────────────────────────────
WINDOW_WIDTH = 750
WINDOW_HEIGHT = 580
LYRICS_LANG = "zho"  # 中文歌词语言代码

# ── 歌词读取 ────────────────────────────────────────


def read_lyrics(lrc_path):
    """读取 .lrc 或 .txt 歌词文件，返回原始文本"""
    encodings = ["utf-8", "gbk", "utf-8-sig", "gb2312"]
    for enc in encodings:
        try:
            with open(lrc_path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"无法识别歌词文件编码：{lrc_path}")


def strip_timestamps(text):
    """去除 LRC 时间戳，返回纯文本歌词"""
    return re.sub(r"\[\d{2}:\d{2}[.:]\d{2,3}\]", "", text)


def preview_text(text, max_lines=12):
    """截取前 N 行用于预览"""
    lines = [l for l in text.splitlines() if l.strip()]
    shown = lines[:max_lines]
    suffix = f"\n... 共 {len(lines)} 行" if len(lines) > max_lines else ""
    return "\n".join(shown) + suffix


# ── 嵌入核心 ────────────────────────────────────────


def embed_lyrics_to_mp3(mp3_path, lyrics_text, output_path):
    """
    将歌词嵌入 MP3 的 ID3 USLT 标签。
    output_path 可以与 mp3_path 相同（原地写入）或不同（生成新文件）。
    """
    if output_path != mp3_path:
        shutil.copy2(mp3_path, output_path)

    target = output_path

    try:
        tags = ID3(target)
    except ID3NoHeaderError:
        tags = ID3()

    # 移除已有的 USLT 帧，防止重复
    tags.delall("USLT")

    tags.add(USLT(
        encoding=3,          # UTF-8
        lang=LYRICS_LANG,
        desc="Lyrics",
        text=lyrics_text,
    ))
    tags.save(target, v2_version=3)


# ── 批量匹配 ────────────────────────────────────────


def scan_folder(folder_path):
    """
    扫描文件夹，按文件名自动匹配 mp3 ↔ lrc/txt。
    返回 list of dict: {mp3, lyrics, name, status}
    """
    mp3_map = {}   # stem -> full path
    lrc_map = {}   # stem -> full path

    for fname in os.listdir(folder_path):
        full = os.path.join(folder_path, fname)
        if not os.path.isfile(full):
            continue
        stem, ext = os.path.splitext(fname)
        ext = ext.lower()
        if ext == ".mp3":
            mp3_map[stem] = full
        elif ext in (".lrc", ".txt"):
            lrc_map[stem] = full

    results = []
    for stem, mp3_path in sorted(mp3_map.items()):
        entry = {"name": stem, "mp3": mp3_path, "lyrics": None, "status": "未匹配"}
        if stem in lrc_map:
            entry["lyrics"] = lrc_map[stem]
            entry["status"] = "已匹配"
        results.append(entry)
    return results


# ── GUI 主程序 ──────────────────────────────────────


class LyricsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mp3 歌词嵌入工具 2.0")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)

        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        # 检查依赖
        if not HAS_MUTAGEN:
            self._show_dependency_error()
        else:
            self._show_start_page()

    def _clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    # ── 依赖缺失提示 ────────────────────────────────

    def _show_dependency_error(self):
        self._clear()
        frame = tk.Frame(self.container)
        frame.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(frame, text="缺少依赖库", font=("Microsoft YaHei", 20, "bold"), fg="#c62828").pack(pady=(0, 15))
        tk.Label(frame, text="请在命令行中运行以下命令后重新打开程序：", font=("Microsoft YaHei", 11)).pack()
        tk.Label(frame, text="pip install mutagen", font=("Consolas", 14, "bold"), fg="#1a73e8").pack(pady=15)

    # ── 开始页面 ─────────────────────────────────────

    def _show_start_page(self):
        self._clear()
        frame = tk.Frame(self.container)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame, text="Mp3 歌词嵌入工具 2.0", font=("Microsoft YaHei", 24, "bold")).pack(pady=(0, 6))
        tk.Label(frame, text="给你的音乐嵌入歌词，本地播放器/车载蓝牙可显示滚动歌词",
                 font=("Microsoft YaHei", 10), fg="#666").pack(pady=(0, 35))

        btn_single = tk.Button(
            frame, text="单曲嵌入", font=("Microsoft YaHei", 13),
            width=20, height=2, command=self._show_single_page,
        )
        btn_single.pack(pady=6)
        tk.Label(frame, text="选择一个 MP3 + 一个歌词文件", font=("Microsoft YaHei", 9), fg="#999").pack(pady=(0, 16))

        btn_batch = tk.Button(
            frame, text="批量嵌入（文件夹匹配）", font=("Microsoft YaHei", 13),
            width=20, height=2, command=self._show_batch_page,
        )
        btn_batch.pack(pady=6)
        tk.Label(frame, text="选一个文件夹，自动按文件名匹配 MP3 和歌词", font=("Microsoft YaHei", 9), fg="#999").pack()

    # ── 单曲嵌入页面 ─────────────────────────────────

    def _show_single_page(self):
        self._clear()
        self._single_mp3 = None
        self._single_lrc = None
        self._single_overwrite = tk.BooleanVar(value=False)

        # 顶部返回
        top = tk.Frame(self.container)
        top.pack(fill="x", padx=20, pady=(15, 5))
        tk.Button(top, text="← 返回", font=("Microsoft YaHei", 10), command=self._show_start_page).pack(side="left")
        tk.Label(top, text="单曲嵌入", font=("Microsoft YaHei", 14, "bold")).pack(side="left", padx=15)

        body = tk.Frame(self.container)
        body.pack(fill="both", expand=True, padx=25, pady=10)

        # MP3 选择
        tk.Label(body, text="MP3 文件：", font=("Microsoft YaHei", 11)).pack(anchor="w", pady=(10, 3))
        mp3_row = tk.Frame(body)
        mp3_row.pack(fill="x")
        self._single_mp3_label = tk.Label(mp3_row, text="未选择", font=("Microsoft YaHei", 10), fg="#999", anchor="w")
        self._single_mp3_label.pack(side="left", fill="x", expand=True)
        tk.Button(mp3_row, text="选择文件", font=("Microsoft YaHei", 10), command=self._pick_single_mp3).pack(side="right")

        # 歌词选择
        tk.Label(body, text="歌词文件（.lrc / .txt）：", font=("Microsoft YaHei", 11)).pack(anchor="w", pady=(15, 3))
        lrc_row = tk.Frame(body)
        lrc_row.pack(fill="x")
        self._single_lrc_label = tk.Label(lrc_row, text="未选择", font=("Microsoft YaHei", 10), fg="#999", anchor="w")
        self._single_lrc_label.pack(side="left", fill="x", expand=True)
        tk.Button(lrc_row, text="选择文件", font=("Microsoft YaHei", 10), command=self._pick_single_lrc).pack(side="right")

        # 歌词预览
        tk.Label(body, text="歌词预览：", font=("Microsoft YaHei", 11)).pack(anchor="w", pady=(15, 3))
        self._single_preview = tk.Text(body, height=8, font=("Microsoft YaHei", 9), state="disabled", bg="#f5f5f5", wrap="word")
        self._single_preview.pack(fill="x")

        # 写入方式
        tk.Checkbutton(
            body, text='直接写入原文件（不勾选则生成"原名_歌词版.mp3"新文件）',
            variable=self._single_overwrite, font=("Microsoft YaHei", 10),
        ).pack(anchor="w", pady=(15, 5))

        # 嵌入按钮
        self._single_embed_btn = tk.Button(
            body, text="嵌入歌词", font=("Microsoft YaHei", 12, "bold"),
            width=16, height=2, command=self._do_single_embed, state="disabled",
        )
        self._single_embed_btn.pack(pady=10)

    def _pick_single_mp3(self):
        path = filedialog.askopenfilename(title="选择 MP3 文件", filetypes=[("MP3", "*.mp3")])
        if path:
            self._single_mp3 = path
            self._single_mp3_label.config(text=os.path.basename(path), fg="#333")
            self._check_single_ready()

    def _pick_single_lrc(self):
        path = filedialog.askopenfilename(
            title="选择歌词文件",
            filetypes=[("歌词文件", "*.lrc *.txt"), ("LRC", "*.lrc"), ("TXT", "*.txt")],
        )
        if path:
            self._single_lrc = path
            self._single_lrc_label.config(text=os.path.basename(path), fg="#333")
            # 预览
            try:
                raw = read_lyrics(path)
                self._single_preview.config(state="normal")
                self._single_preview.delete("1.0", "end")
                self._single_preview.insert("1.0", preview_text(raw, 10))
                self._single_preview.config(state="disabled")
            except Exception as e:
                self._single_preview.config(state="normal")
                self._single_preview.delete("1.0", "end")
                self._single_preview.insert("1.0", f"读取失败：{e}")
                self._single_preview.config(state="disabled")
            self._check_single_ready()

    def _check_single_ready(self):
        if self._single_mp3 and self._single_lrc:
            self._single_embed_btn.config(state="normal")

    def _do_single_embed(self):
        try:
            lyrics = read_lyrics(self._single_lrc)

            if self._single_overwrite.get():
                output = self._single_mp3
            else:
                stem, ext = os.path.splitext(self._single_mp3)
                output = f"{stem}_歌词版{ext}"

            embed_lyrics_to_mp3(self._single_mp3, lyrics, output)
            self._show_single_result(True, output)
        except Exception as e:
            self._show_single_result(False, str(e))

    def _show_single_result(self, success, info):
        self._clear()
        frame = tk.Frame(self.container)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        if success:
            tk.Label(frame, text="嵌入成功", font=("Microsoft YaHei", 22, "bold"), fg="#2e7d32").pack(pady=(0, 12))
            tk.Label(frame, text=f"输出文件：", font=("Microsoft YaHei", 11)).pack()
            tk.Label(frame, text=os.path.basename(info), font=("Microsoft YaHei", 12, "bold"), fg="#1a73e8").pack(pady=(2, 5))
            tk.Label(frame, text=os.path.dirname(info), font=("Microsoft YaHei", 9), fg="#999").pack(pady=(0, 20))
        else:
            tk.Label(frame, text="嵌入失败", font=("Microsoft YaHei", 22, "bold"), fg="#c62828").pack(pady=(0, 12))
            tk.Label(frame, text=info, font=("Microsoft YaHei", 10), fg="#c62828", wraplength=500).pack(pady=(0, 20))

        btn_row = tk.Frame(frame)
        btn_row.pack()
        tk.Button(btn_row, text="继续嵌入", font=("Microsoft YaHei", 11), width=12, command=self._show_single_page).pack(side="left", padx=6)
        tk.Button(btn_row, text="返回首页", font=("Microsoft YaHei", 11), width=12, command=self._show_start_page).pack(side="left", padx=6)

    # ── 批量嵌入页面 ─────────────────────────────────

    def _show_batch_page(self):
        self._clear()
        self._batch_folder = None
        self._batch_matches = []
        self._batch_overwrite = tk.BooleanVar(value=False)

        # 顶部
        top = tk.Frame(self.container)
        top.pack(fill="x", padx=20, pady=(15, 5))
        tk.Button(top, text="← 返回", font=("Microsoft YaHei", 10), command=self._show_start_page).pack(side="left")
        tk.Label(top, text="批量嵌入", font=("Microsoft YaHei", 14, "bold")).pack(side="left", padx=15)

        body = tk.Frame(self.container)
        body.pack(fill="both", expand=True, padx=25, pady=10)

        # 文件夹选择
        tk.Label(body, text="选择包含 MP3 和歌词文件的文件夹：", font=("Microsoft YaHei", 11)).pack(anchor="w", pady=(5, 3))
        folder_row = tk.Frame(body)
        folder_row.pack(fill="x")
        self._batch_folder_label = tk.Label(folder_row, text="未选择", font=("Microsoft YaHei", 10), fg="#999", anchor="w")
        self._batch_folder_label.pack(side="left", fill="x", expand=True)
        tk.Button(folder_row, text="选择文件夹", font=("Microsoft YaHei", 10), command=self._pick_batch_folder).pack(side="right")

        # 匹配说明
        tk.Label(body, text="匹配规则：MP3 和歌词文件同名即配对（如 歌曲.mp3 + 歌曲.lrc）",
                 font=("Microsoft YaHei", 9), fg="#888").pack(anchor="w", pady=(8, 5))

        # 匹配结果列表
        list_frame = tk.Frame(body)
        list_frame.pack(fill="both", expand=True)

        columns = ("name", "mp3", "lyrics", "status")
        self._batch_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        self._batch_tree.heading("name", text="文件名")
        self._batch_tree.heading("mp3", text="MP3")
        self._batch_tree.heading("lyrics", text="歌词")
        self._batch_tree.heading("status", text="状态")
        self._batch_tree.column("name", width=200)
        self._batch_tree.column("mp3", width=60, anchor="center")
        self._batch_tree.column("lyrics", width=60, anchor="center")
        self._batch_tree.column("status", width=100, anchor="center")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self._batch_tree.yview)
        self._batch_tree.configure(yscrollcommand=scrollbar.set)
        self._batch_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 底部
        bottom = tk.Frame(body)
        bottom.pack(fill="x", pady=(8, 0))

        self._batch_info_label = tk.Label(bottom, text="请先选择文件夹", font=("Microsoft YaHei", 10), fg="#666")
        self._batch_info_label.pack(side="left")

        tk.Checkbutton(
            bottom, text="写入原文件",
            variable=self._batch_overwrite, font=("Microsoft YaHei", 9),
        ).pack(side="left", padx=(20, 0))

        self._batch_embed_btn = tk.Button(
            bottom, text="开始批量嵌入", font=("Microsoft YaHei", 11, "bold"),
            command=self._do_batch_embed, state="disabled",
        )
        self._batch_embed_btn.pack(side="right")

    def _pick_batch_folder(self):
        folder = filedialog.askdirectory(title="选择音乐文件夹")
        if not folder:
            return
        self._batch_folder = folder
        self._batch_folder_label.config(text=folder, fg="#333")

        # 扫描匹配
        self._batch_matches = scan_folder(folder)

        # 填充列表
        for item in self._batch_tree.get_children():
            self._batch_tree.delete(item)

        matched_count = 0
        for entry in self._batch_matches:
            has_lrc = "有" if entry["lyrics"] else "—"
            self._batch_tree.insert("", "end", values=(
                entry["name"], "有", has_lrc, entry["status"],
            ))
            if entry["lyrics"]:
                matched_count += 1

        total = len(self._batch_matches)
        self._batch_info_label.config(
            text=f"共 {total} 个 MP3，已匹配歌词 {matched_count} 个，未匹配 {total - matched_count} 个"
        )

        if matched_count > 0:
            self._batch_embed_btn.config(state="normal")
        else:
            self._batch_embed_btn.config(state="disabled")

    def _do_batch_embed(self):
        overwrite = self._batch_overwrite.get()
        success_list = []
        fail_list = []

        for entry in self._batch_matches:
            if not entry["lyrics"]:
                continue
            try:
                lyrics = read_lyrics(entry["lyrics"])
                if overwrite:
                    output = entry["mp3"]
                else:
                    stem, ext = os.path.splitext(entry["mp3"])
                    output = f"{stem}_歌词版{ext}"
                embed_lyrics_to_mp3(entry["mp3"], lyrics, output)
                success_list.append(entry["name"])
            except Exception as e:
                fail_list.append((entry["name"], str(e)))

        self._show_batch_result(success_list, fail_list)

    def _show_batch_result(self, success_list, fail_list):
        self._clear()
        frame = tk.Frame(self.container)
        frame.pack(fill="both", expand=True, padx=30, pady=20)

        tk.Label(frame, text="批量嵌入完成", font=("Microsoft YaHei", 22, "bold")).pack(pady=(10, 15))

        # 统计
        total = len(success_list) + len(fail_list)
        color = "#2e7d32" if not fail_list else "#e65100"
        tk.Label(
            frame,
            text=f"成功 {len(success_list)} / {total}",
            font=("Microsoft YaHei", 18, "bold"), fg=color,
        ).pack(pady=(0, 15))

        # 详情
        detail_frame = tk.Frame(frame)
        detail_frame.pack(fill="both", expand=True)

        detail_text = tk.Text(detail_frame, font=("Microsoft YaHei", 10), state="normal", wrap="word", bg="#f9f9f9")
        detail_scroll = ttk.Scrollbar(detail_frame, orient="vertical", command=detail_text.yview)
        detail_text.configure(yscrollcommand=detail_scroll.set)
        detail_text.pack(side="left", fill="both", expand=True)
        detail_scroll.pack(side="right", fill="y")

        if success_list:
            detail_text.insert("end", "── 成功 ──\n")
            for name in success_list:
                detail_text.insert("end", f"  {name}\n")
            detail_text.insert("end", "\n")

        if fail_list:
            detail_text.insert("end", "── 失败 ──\n")
            for name, err in fail_list:
                detail_text.insert("end", f"  {name}：{err}\n")

        detail_text.config(state="disabled")

        # 按钮
        btn_row = tk.Frame(frame)
        btn_row.pack(pady=(12, 0))
        tk.Button(btn_row, text="继续批量", font=("Microsoft YaHei", 11), width=12, command=self._show_batch_page).pack(side="left", padx=6)
        tk.Button(btn_row, text="返回首页", font=("Microsoft YaHei", 11), width=12, command=self._show_start_page).pack(side="left", padx=6)


# ── 入口 ────────────────────────────────────────────

if __name__ == "__main__":
    app = LyricsApp()
    app.mainloop()
