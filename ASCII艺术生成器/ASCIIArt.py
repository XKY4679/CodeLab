"""
ASCII 艺术生成器 —— GUI 图形窗口版
将图片转为字符画 / 将文字转为大字 ASCII
支持多种字符集、宽度调节、导出
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os

try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

WINDOW_W = 820
WINDOW_H = 660

# 字符集（从暗到亮）
CHARSETS = {
    "标准":    " .:-=+*#%@",
    "详细":    " .'`^\",:;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
    "方块":    " ░▒▓█",
    "简约":    " .oO@#",
    "数字":    " 0123456789",
    "自定义":  "",
}

# 大字字母模板（5x5 简易字体，覆盖 A-Z 和 0-9）
BANNER_FONT = {
    "A": ["  #  ", " # # ", "#####", "#   #", "#   #"],
    "B": ["#### ", "#   #", "#### ", "#   #", "#### "],
    "C": [" ####", "#    ", "#    ", "#    ", " ####"],
    "D": ["#### ", "#   #", "#   #", "#   #", "#### "],
    "E": ["#####", "#    ", "#### ", "#    ", "#####"],
    "F": ["#####", "#    ", "#### ", "#    ", "#    "],
    "G": [" ####", "#    ", "# ###", "#   #", " ### "],
    "H": ["#   #", "#   #", "#####", "#   #", "#   #"],
    "I": ["#####", "  #  ", "  #  ", "  #  ", "#####"],
    "J": ["#####", "    #", "    #", "#   #", " ### "],
    "K": ["#   #", "#  # ", "###  ", "#  # ", "#   #"],
    "L": ["#    ", "#    ", "#    ", "#    ", "#####"],
    "M": ["#   #", "## ##", "# # #", "#   #", "#   #"],
    "N": ["#   #", "##  #", "# # #", "#  ##", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", " ### "],
    "P": ["#### ", "#   #", "#### ", "#    ", "#    "],
    "Q": [" ### ", "#   #", "# # #", "#  ##", " ####"],
    "R": ["#### ", "#   #", "#### ", "#  # ", "#   #"],
    "S": [" ####", "#    ", " ### ", "    #", "#### "],
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  "],
    "U": ["#   #", "#   #", "#   #", "#   #", " ### "],
    "V": ["#   #", "#   #", " # # ", " # # ", "  #  "],
    "W": ["#   #", "#   #", "# # #", "## ##", "#   #"],
    "X": ["#   #", " # # ", "  #  ", " # # ", "#   #"],
    "Y": ["#   #", " # # ", "  #  ", "  #  ", "  #  "],
    "Z": ["#####", "   # ", "  #  ", " #   ", "#####"],
    "0": [" ### ", "#  ##", "# # #", "##  #", " ### "],
    "1": ["  #  ", " ##  ", "  #  ", "  #  ", "#####"],
    "2": [" ### ", "#   #", "  ## ", " #   ", "#####"],
    "3": [" ### ", "#   #", "  ## ", "#   #", " ### "],
    "4": ["#   #", "#   #", "#####", "    #", "    #"],
    "5": ["#####", "#    ", "#### ", "    #", "#### "],
    "6": [" ### ", "#    ", "#### ", "#   #", " ### "],
    "7": ["#####", "   # ", "  #  ", " #   ", "#    "],
    "8": [" ### ", "#   #", " ### ", "#   #", " ### "],
    "9": [" ### ", "#   #", " ####", "    #", " ### "],
    " ": ["     ", "     ", "     ", "     ", "     "],
    "!": ["  #  ", "  #  ", "  #  ", "     ", "  #  "],
    ".": ["     ", "     ", "     ", "     ", "  #  "],
    "-": ["     ", "     ", "#####", "     ", "     "],
    "?": [" ### ", "#   #", "  ## ", "     ", "  #  "],
}


class ASCIIArtApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ASCII 艺术生成器")
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.resizable(False, False)
        self._preview_photo = None

        if not HAS_PIL:
            f = tk.Frame(self)
            f.place(relx=0.5, rely=0.5, anchor="center")
            tk.Label(f, text="pip install Pillow",
                     font=("Consolas", 14, "bold"), fg="#1a73e8").pack()
            return

        self._build_ui()

    def _build_ui(self):
        # ── 标题 ──
        top = tk.Frame(self)
        top.pack(fill="x", padx=14, pady=(10, 4))
        tk.Label(top, text="ASCII 艺术生成器",
                 font=("Microsoft YaHei", 15, "bold")).pack(side="left")

        # ── 标签页 ──
        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill="both", expand=True, padx=14, pady=(0, 6))

        self._build_image_tab()
        self._build_text_tab()

        # ── 输出区 ──
        out_frame = tk.LabelFrame(self, text=" 输出 ",
                                   font=("Microsoft YaHei", 10, "bold"))
        out_frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        btn_row = tk.Frame(out_frame)
        btn_row.pack(fill="x", padx=8, pady=(6, 2))
        tk.Button(btn_row, text="复制到剪贴板",
                  font=("Microsoft YaHei", 9),
                  command=self._copy_result).pack(side="left")
        tk.Button(btn_row, text="保存为 TXT",
                  font=("Microsoft YaHei", 9),
                  command=self._save_txt).pack(side="left", padx=6)
        tk.Button(btn_row, text="保存为图片",
                  font=("Microsoft YaHei", 9),
                  command=self._save_image).pack(side="left")

        self._output_text = scrolledtext.ScrolledText(
            out_frame, font=("Consolas", 7), wrap="none",
            bg="#1e1e1e", fg="#00ff00")
        self._output_text.pack(fill="both", expand=True, padx=8, pady=(2, 8))

    # ── 图片转 ASCII 标签页 ──
    def _build_image_tab(self):
        tab = tk.Frame(self._notebook)
        self._notebook.add(tab, text="  图片 → ASCII  ")

        r1 = tk.Frame(tab)
        r1.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(r1, text="图片：",
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self._img_path_var = tk.StringVar()
        tk.Entry(r1, textvariable=self._img_path_var,
                 font=("Microsoft YaHei", 9), width=40).pack(side="left", padx=4)
        tk.Button(r1, text="选择图片", font=("Microsoft YaHei", 9),
                  command=self._select_image).pack(side="left")

        r2 = tk.Frame(tab)
        r2.pack(fill="x", padx=8, pady=4)

        tk.Label(r2, text="输出宽度：",
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self._width_var = tk.IntVar(value=100)
        tk.Spinbox(r2, from_=30, to=300, textvariable=self._width_var,
                   font=("Microsoft YaHei", 9), width=5).pack(side="left", padx=4)
        tk.Label(r2, text="字符",
                 font=("Microsoft YaHei", 8), fg="#888").pack(side="left")

        tk.Label(r2, text="字符集：",
                 font=("Microsoft YaHei", 9)).pack(side="left", padx=(16, 0))
        self._charset_var = tk.StringVar(value="标准")
        ttk.Combobox(r2, values=list(CHARSETS.keys()),
                     textvariable=self._charset_var,
                     font=("Microsoft YaHei", 9), width=8).pack(side="left", padx=4)

        self._invert_var = tk.BooleanVar(value=False)
        tk.Checkbutton(r2, text="反转（亮底暗字）",
                       variable=self._invert_var,
                       font=("Microsoft YaHei", 9)).pack(side="left", padx=8)

        r2b = tk.Frame(tab)
        r2b.pack(fill="x", padx=8, pady=(0, 4))
        tk.Label(r2b, text="自定义字符：",
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self._custom_chars_var = tk.StringVar(value=" .:-=+*#%@")
        tk.Entry(r2b, textvariable=self._custom_chars_var,
                 font=("Consolas", 10), width=35).pack(side="left", padx=4)

        tk.Button(tab, text="生成 ASCII 艺术",
                  font=("Microsoft YaHei", 11, "bold"),
                  command=self._generate_from_image
                  ).pack(padx=8, pady=(4, 8), anchor="w")

    # ── 文字转大字 标签页 ──
    def _build_text_tab(self):
        tab = tk.Frame(self._notebook)
        self._notebook.add(tab, text="  文字 → 大字  ")

        r1 = tk.Frame(tab)
        r1.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(r1, text="输入文字：",
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self._banner_var = tk.StringVar(value="HELLO")
        tk.Entry(r1, textvariable=self._banner_var,
                 font=("Consolas", 14), width=25).pack(side="left", padx=4)

        r2 = tk.Frame(tab)
        r2.pack(fill="x", padx=8, pady=4)
        tk.Label(r2, text="填充字符：",
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self._fill_char_var = tk.StringVar(value="#")
        tk.Entry(r2, textvariable=self._fill_char_var,
                 font=("Consolas", 12), width=3).pack(side="left", padx=4)

        tk.Label(r2, text="间距：",
                 font=("Microsoft YaHei", 9)).pack(side="left", padx=(16, 0))
        self._spacing_var = tk.IntVar(value=2)
        tk.Spinbox(r2, from_=0, to=5, textvariable=self._spacing_var,
                   font=("Microsoft YaHei", 9), width=3).pack(side="left", padx=4)

        tk.Button(tab, text="生成大字",
                  font=("Microsoft YaHei", 11, "bold"),
                  command=self._generate_banner
                  ).pack(padx=8, pady=(4, 8), anchor="w")

    # ── 图片选择 ──
    def _select_image(self):
        path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"),
                       ("所有文件", "*.*")])
        if path:
            self._img_path_var.set(path)

    # ── 图片 → ASCII ──
    def _generate_from_image(self):
        path = self._img_path_var.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showwarning("提示", "请先选择一张图片")
            return

        try:
            img = Image.open(path)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开图片：{e}")
            return

        width = self._width_var.get()

        # 选择字符集
        charset_name = self._charset_var.get()
        if charset_name == "自定义":
            chars = self._custom_chars_var.get()
        else:
            chars = CHARSETS.get(charset_name, CHARSETS["标准"])

        if not chars:
            chars = CHARSETS["标准"]

        if self._invert_var.get():
            chars = chars[::-1]

        # 缩放图片（字符高宽比约 2:1）
        aspect = img.height / img.width
        height = int(width * aspect * 0.5)
        img_resized = img.resize((width, height), Image.LANCZOS)
        img_gray = img_resized.convert("L")

        # 映射像素到字符
        result_lines = []
        pixels = img_gray.load()
        for y in range(height):
            line = ""
            for x in range(width):
                brightness = pixels[x, y]
                idx = int(brightness / 256 * len(chars))
                idx = min(idx, len(chars) - 1)
                line += chars[idx]
            result_lines.append(line)

        result = "\n".join(result_lines)
        self._show_output(result)

    # ── 文字 → 大字 ──
    def _generate_banner(self):
        text = self._banner_var.get().upper()
        if not text:
            messagebox.showwarning("提示", "请输入文字")
            return

        fill = self._fill_char_var.get() or "#"
        spacing = self._spacing_var.get()
        spacer = " " * spacing

        # 每行5行高
        output_lines = [""] * 5
        for ch in text:
            template = BANNER_FONT.get(ch)
            if template is None:
                template = BANNER_FONT.get(" ", ["     "] * 5)
            for row in range(5):
                if output_lines[row]:
                    output_lines[row] += spacer
                line = template[row].replace("#", fill)
                output_lines[row] += line

        result = "\n".join(output_lines)
        self._show_output(result)

    # ── 输出 ──
    def _show_output(self, text):
        self._output_text.delete("1.0", "end")
        self._output_text.insert("1.0", text)

    def _copy_result(self):
        text = self._output_text.get("1.0", "end-1c")
        if text.strip():
            self.clipboard_clear()
            self.clipboard_append(text)
            messagebox.showinfo("完成", "已复制到剪贴板")

    def _save_txt(self):
        text = self._output_text.get("1.0", "end-1c")
        if not text.strip():
            return
        path = filedialog.asksaveasfilename(
            title="保存 TXT",
            initialfile="ascii_art.txt",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            messagebox.showinfo("完成", f"已保存到 {path}")

    def _save_image(self):
        """把 ASCII 渲染成图片保存"""
        text = self._output_text.get("1.0", "end-1c")
        if not text.strip():
            return

        path = filedialog.asksaveasfilename(
            title="保存图片",
            initialfile="ascii_art.png",
            defaultextension=".png",
            filetypes=[("PNG", "*.png")])
        if not path:
            return

        lines = text.split("\n")
        font_size = 12
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf",
                                       font_size)
        except Exception:
            font = ImageFont.load_default()

        char_bbox = font.getbbox("M")
        char_w = char_bbox[2] - char_bbox[0]
        char_h = int(font_size * 1.3)
        max_len = max(len(line) for line in lines) if lines else 1
        pad = 16

        img_w = max_len * char_w + pad * 2
        img_h = len(lines) * char_h + pad * 2

        img = Image.new("RGB", (img_w, img_h), (30, 30, 30))
        draw = ImageDraw.Draw(img)

        for i, line in enumerate(lines):
            draw.text((pad, pad + i * char_h), line,
                      fill=(0, 255, 0), font=font)

        img.save(path)
        messagebox.showinfo("完成",
                            f"已保存到 {path}\n尺寸 {img_w}x{img_h} px")


if __name__ == "__main__":
    app = ASCIIArtApp()
    app.mainloop()
