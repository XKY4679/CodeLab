"""
答题系统 3.0 —— GUI 图形窗口版
支持 Excel (.xlsx) / Word (.docx) / TXT (.txt) 题库
tkinter 界面，错题一键导出
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import random
import os
import datetime

# ── 第三方依赖 ──────────────────────────────────────
try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

try:
    import openpyxl
except ImportError:
    openpyxl = None

# ── 配置 ────────────────────────────────────────────
MAX_QUESTIONS = 20
SCORE_PER_Q = 5
WINDOW_WIDTH = 720
WINDOW_HEIGHT = 560

# ── 题库解析 ────────────────────────────────────────


def load_from_excel(path):
    """读取 Excel 题库"""
    if pd is None or openpyxl is None:
        raise RuntimeError("缺少依赖：请先运行  pip install pandas openpyxl")
    df = pd.read_excel(path, engine="openpyxl")
    df.columns = df.columns.str.strip()
    required = ["题目", "选项A", "选项B", "选项C", "选项D", "答案"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Excel 缺少列：{missing}")
    if "解析内容" not in df.columns:
        df["解析内容"] = "暂无解析"
    df["解析内容"] = df["解析内容"].fillna("暂无解析")
    df["答案"] = df["答案"].astype(str).str.strip().str.upper()
    return df.to_dict("records")


def _parse_text_block(lines):
    """
    从文本行列表中解析 题目/选项/答案/解析 块。
    支持格式：
        题目：xxx
        选项A：xxx  (或 A：xxx / A. xxx / A、xxx)
        选项B：xxx
        选项C：xxx
        选项D：xxx
        答案：A
        解析：xxx          （可选）
    块与块之间用空行分隔。
    """
    questions = []
    current = {}
    key_map = {
        "题目": "题目",
        "选项A": "选项A", "A": "选项A",
        "选项B": "选项B", "B": "选项B",
        "选项C": "选项C", "C": "选项C",
        "选项D": "选项D", "D": "选项D",
        "答案": "答案",
        "解析": "解析内容", "解析内容": "解析内容",
    }

    def _flush():
        if "题目" in current and "答案" in current:
            current.setdefault("解析内容", "暂无解析")
            current["答案"] = current["答案"].strip().upper()
            questions.append(dict(current))

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            _flush()
            current = {}
            continue

        # 尝试匹配 "关键字：值" / "关键字:值" / "A. 值" / "A、值"
        matched = False
        for prefix, field in key_map.items():
            for sep in ("：", ":", ".", "、"):
                tag = prefix + sep
                if line.startswith(tag):
                    current[field] = line[len(tag):].strip()
                    matched = True
                    break
            if matched:
                break

        # 没匹配到关键字，尝试追加到题目（多行题目）
        if not matched and "题目" in current and "选项A" not in current:
            current["题目"] += line

    _flush()
    return questions


def load_from_txt(path):
    """读取 TXT 题库"""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    questions = _parse_text_block(lines)
    if not questions:
        raise ValueError("未能从 TXT 文件中解析出任何题目，请检查格式。")
    return questions


def load_from_docx(path):
    """读取 Word 题库"""
    if DocxDocument is None:
        raise RuntimeError("缺少依赖：请先运行  pip install python-docx")
    doc = DocxDocument(path)
    lines = [p.text for p in doc.paragraphs]
    questions = _parse_text_block(lines)
    if not questions:
        raise ValueError("未能从 Word 文件中解析出任何题目，请检查格式。")
    return questions


def load_questions(path):
    """根据扩展名自动选择解析方式"""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        return load_from_excel(path)
    elif ext == ".docx":
        return load_from_docx(path)
    elif ext == ".txt":
        return load_from_txt(path)
    else:
        raise ValueError(f"不支持的文件格式：{ext}")


# ── 错题导出 ────────────────────────────────────────


def export_wrong_questions(wrong_list):
    """将错题列表导出为 Excel"""
    if pd is None:
        messagebox.showerror("导出失败", "缺少 pandas，无法导出 Excel。")
        return
    if not wrong_list:
        messagebox.showinfo("提示", "没有错题可导出。")
        return

    save_path = filedialog.asksaveasfilename(
        title="导出错题",
        defaultextension=".xlsx",
        initialfile=f"错题本_{datetime.datetime.now():%Y%m%d_%H%M%S}.xlsx",
        filetypes=[("Excel files", "*.xlsx")],
    )
    if not save_path:
        return

    rows = []
    for q in wrong_list:
        rows.append({
            "题目": q["题目"],
            "选项A": q.get("选项A", ""),
            "选项B": q.get("选项B", ""),
            "选项C": q.get("选项C", ""),
            "选项D": q.get("选项D", ""),
            "正确答案": q["答案"],
            "你的选择": q.get("用户错选", ""),
            "解析": q.get("解析内容", ""),
        })
    df = pd.DataFrame(rows)
    df.to_excel(save_path, index=False, engine="openpyxl")
    messagebox.showinfo("导出成功", f"错题已保存至：\n{save_path}")


# ── GUI 主程序 ──────────────────────────────────────


class QuizApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("智能答题系统 3.0")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)

        # 数据
        self.questions_pool = []
        self.current_quiz = []
        self.current_index = 0
        self.score = 0
        self.wrong_questions = []
        self.selected_answer = tk.StringVar(value="")

        # 容器：用于切换页面
        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self._show_start_page()

    # ── 开始页面 ───────────────────────────────────

    def _clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    def _show_start_page(self):
        self._clear()
        frame = tk.Frame(self.container)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame, text="智能答题系统 3.0", font=("Microsoft YaHei", 24, "bold")).pack(pady=(0, 8))
        tk.Label(frame, text="支持 Excel / Word / TXT 题库", font=("Microsoft YaHei", 11), fg="#666").pack(pady=(0, 30))

        btn = tk.Button(
            frame, text="选择题库文件", font=("Microsoft YaHei", 13),
            width=18, height=2, command=self._on_select_file,
        )
        btn.pack()

        tk.Label(
            frame, text="支持格式：.xlsx  .docx  .txt",
            font=("Microsoft YaHei", 9), fg="#999",
        ).pack(pady=(12, 0))

    def _on_select_file(self):
        path = filedialog.askopenfilename(
            title="选择题库文件",
            filetypes=[
                ("所有支持格式", "*.xlsx *.xls *.docx *.txt"),
                ("Excel", "*.xlsx *.xls"),
                ("Word", "*.docx"),
                ("文本文件", "*.txt"),
            ],
        )
        if not path:
            return
        try:
            self.questions_pool = load_questions(path)
        except Exception as e:
            messagebox.showerror("加载失败", str(e))
            return

        if not self.questions_pool:
            messagebox.showwarning("提示", "题库中没有题目。")
            return

        self._start_quiz()

    # ── 答题页面 ───────────────────────────────────

    def _start_quiz(self):
        random.shuffle(self.questions_pool)
        num = min(MAX_QUESTIONS, len(self.questions_pool))
        self.current_quiz = self.questions_pool[:num]
        self.current_index = 0
        self.score = 0
        self.wrong_questions = []
        self._show_question()

    def _show_question(self):
        self._clear()
        q = self.current_quiz[self.current_index]
        total = len(self.current_quiz)
        idx = self.current_index + 1

        # 顶部信息条
        top = tk.Frame(self.container)
        top.pack(fill="x", padx=20, pady=(15, 5))
        tk.Label(top, text=f"第 {idx} / {total} 题", font=("Microsoft YaHei", 11, "bold")).pack(side="left")
        tk.Label(top, text=f"当前得分：{self.score}", font=("Microsoft YaHei", 11), fg="#1a73e8").pack(side="right")

        # 进度条
        progress = ttk.Progressbar(self.container, length=WINDOW_WIDTH - 40, maximum=total, value=idx)
        progress.pack(padx=20, pady=(0, 10))

        # 题目
        q_frame = tk.Frame(self.container)
        q_frame.pack(fill="x", padx=25, pady=(5, 10))
        tk.Label(
            q_frame, text=q["题目"], font=("Microsoft YaHei", 13),
            wraplength=WINDOW_WIDTH - 60, justify="left", anchor="w",
        ).pack(anchor="w")

        # 选项
        self.selected_answer.set("")
        opts_frame = tk.Frame(self.container)
        opts_frame.pack(fill="x", padx=40, pady=(0, 10))
        for opt in ["A", "B", "C", "D"]:
            text = f"{opt}.  {q.get(f'选项{opt}', '')}"
            rb = tk.Radiobutton(
                opts_frame, text=text, variable=self.selected_answer, value=opt,
                font=("Microsoft YaHei", 12), anchor="w", wraplength=WINDOW_WIDTH - 100,
            )
            rb.pack(anchor="w", pady=3)

        # 反馈区域（初始隐藏）
        self.feedback_frame = tk.Frame(self.container)
        self.feedback_frame.pack(fill="x", padx=25, pady=(5, 5))

        # 按钮区域
        btn_frame = tk.Frame(self.container)
        btn_frame.pack(pady=(10, 15))
        self.confirm_btn = tk.Button(
            btn_frame, text="确认答案", font=("Microsoft YaHei", 12),
            width=14, command=self._on_confirm,
        )
        self.confirm_btn.pack(side="left", padx=8)

        self.next_btn = tk.Button(
            btn_frame, text="下一题 →", font=("Microsoft YaHei", 12),
            width=14, command=self._on_next, state="disabled",
        )
        self.next_btn.pack(side="left", padx=8)

    def _on_confirm(self):
        ans = self.selected_answer.get()
        if not ans:
            messagebox.showwarning("提示", "请先选择一个答案。")
            return

        q = self.current_quiz[self.current_index]
        correct = q["答案"].strip().upper()
        explanation = q.get("解析内容", "暂无解析")

        # 清空反馈区
        for w in self.feedback_frame.winfo_children():
            w.destroy()

        if ans == correct:
            self.score += SCORE_PER_Q
            tk.Label(
                self.feedback_frame,
                text=f"  回答正确！ +{SCORE_PER_Q} 分",
                font=("Microsoft YaHei", 12, "bold"), fg="#2e7d32",
            ).pack(anchor="w")
        else:
            q["用户错选"] = ans
            self.wrong_questions.append(q)
            tk.Label(
                self.feedback_frame,
                text=f"  回答错误  你选：{ans}  正确：{correct}",
                font=("Microsoft YaHei", 12, "bold"), fg="#c62828",
            ).pack(anchor="w")

        tk.Label(
            self.feedback_frame,
            text=f"解析：{explanation}",
            font=("Microsoft YaHei", 10), fg="#555",
            wraplength=WINDOW_WIDTH - 60, justify="left",
        ).pack(anchor="w", pady=(4, 0))

        # 更新顶部得分
        for w in self.container.winfo_children():
            if isinstance(w, tk.Frame):
                for child in w.winfo_children():
                    if isinstance(child, tk.Label) and "当前得分" in str(child.cget("text")):
                        child.config(text=f"当前得分：{self.score}")
                break

        self.confirm_btn.config(state="disabled")
        # 最后一题时，按钮变为"查看结果"
        if self.current_index >= len(self.current_quiz) - 1:
            self.next_btn.config(text="查看结果", state="normal")
        else:
            self.next_btn.config(state="normal")

    def _on_next(self):
        self.current_index += 1
        if self.current_index >= len(self.current_quiz):
            self._show_result_page()
        else:
            self._show_question()

    # ── 结算页面 ───────────────────────────────────

    def _show_result_page(self):
        self._clear()
        total = len(self.current_quiz)
        full_score = total * SCORE_PER_Q
        wrong_count = len(self.wrong_questions)
        right_count = total - wrong_count

        frame = tk.Frame(self.container)
        frame.pack(expand=True)

        tk.Label(frame, text="答题结束", font=("Microsoft YaHei", 22, "bold")).pack(pady=(0, 15))

        # 分数
        color = "#2e7d32" if self.score >= full_score * 0.6 else "#c62828"
        tk.Label(
            frame, text=f"{self.score} / {full_score}",
            font=("Microsoft YaHei", 36, "bold"), fg=color,
        ).pack()
        tk.Label(
            frame, text=f"共 {total} 题 | 正确 {right_count} | 错误 {wrong_count}",
            font=("Microsoft YaHei", 12), fg="#666",
        ).pack(pady=(4, 25))

        # 按钮组
        btn_frame = tk.Frame(frame)
        btn_frame.pack()

        if wrong_count > 0:
            tk.Button(
                btn_frame, text="查看错题", font=("Microsoft YaHei", 11),
                width=12, command=self._show_wrong_detail,
            ).pack(side="left", padx=6, pady=4)

            tk.Button(
                btn_frame, text="导出错题", font=("Microsoft YaHei", 11),
                width=12, command=lambda: export_wrong_questions(self.wrong_questions),
            ).pack(side="left", padx=6, pady=4)

        tk.Button(
            btn_frame, text="再来一轮", font=("Microsoft YaHei", 11),
            width=12, command=self._start_quiz,
        ).pack(side="left", padx=6, pady=4)

        tk.Button(
            btn_frame, text="重新选题库", font=("Microsoft YaHei", 11),
            width=12, command=self._show_start_page,
        ).pack(side="left", padx=6, pady=4)

    # ── 错题详情弹窗 ──────────────────────────────

    def _show_wrong_detail(self):
        win = tk.Toplevel(self)
        win.title("错题回顾")
        win.geometry("640x460")
        win.resizable(False, False)

        canvas = tk.Canvas(win)
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas)

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for i, q in enumerate(self.wrong_questions, 1):
            tk.Label(inner, text=f"—— 第 {i} 题 ——", font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
            tk.Label(inner, text=f"题目：{q['题目']}", font=("Microsoft YaHei", 10), wraplength=590, justify="left").pack(anchor="w", padx=10)
            for opt in ["A", "B", "C", "D"]:
                tk.Label(inner, text=f"  {opt}. {q.get(f'选项{opt}', '')}", font=("Microsoft YaHei", 10)).pack(anchor="w", padx=10)
            tk.Label(inner, text=f"你的选择：{q.get('用户错选', '')}  |  正确答案：{q['答案']}", font=("Microsoft YaHei", 10, "bold"), fg="#c62828").pack(anchor="w", padx=10, pady=(2, 0))
            tk.Label(inner, text=f"解析：{q.get('解析内容', '暂无解析')}", font=("Microsoft YaHei", 9), fg="#555", wraplength=590, justify="left").pack(anchor="w", padx=10, pady=(0, 5))

        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        win.protocol("WM_DELETE_WINDOW", lambda: (canvas.unbind_all("<MouseWheel>"), win.destroy()))


# ── 入口 ────────────────────────────────────────────

if __name__ == "__main__":
    app = QuizApp()
    app.mainloop()
