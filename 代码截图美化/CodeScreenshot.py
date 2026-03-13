"""
代码截图美化 —— GUI 图形窗口版
把代码渲染成好看的图片（类似 Carbon）
支持语法高亮、多种主题、窗口样式
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os

try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from pygments import lex
    from pygments.lexers import get_lexer_by_name, get_all_lexers, guess_lexer
    from pygments.styles import get_style_by_name, get_all_styles
    from pygments.token import Token
    HAS_PYGMENTS = True
except ImportError:
    HAS_PYGMENTS = False

WINDOW_W = 860
WINDOW_H = 700

# 背景渐变预设
BACKGROUNDS = {
    "紫蓝渐变":    ((74, 0, 224), (142, 45, 226)),
    "蓝绿渐变":    ((0, 198, 255), (0, 114, 255)),
    "橙红渐变":    ((255, 154, 0), (255, 75, 43)),
    "粉紫渐变":    ((233, 64, 87), (138, 35, 135)),
    "青绿渐变":    ((0, 176, 155), (150, 201, 61)),
    "深空灰":      ((30, 30, 30), (60, 60, 60)),
    "纯白":        ((255, 255, 255), (245, 245, 245)),
    "透明":        (None, None),
}

# 常用语言
LANGUAGES = [
    "python", "javascript", "typescript", "java", "c", "cpp", "csharp",
    "go", "rust", "swift", "kotlin", "ruby", "php", "html", "css",
    "sql", "bash", "json", "yaml", "xml", "markdown",
]

# 尝试找一个好的等宽字体
def _find_mono_font(size):
    candidates = [
        "C:/Windows/Fonts/consola.ttf",     # Consolas
        "C:/Windows/Fonts/CascadiaCode.ttf",
        "C:/Windows/Fonts/cour.ttf",        # Courier New
        "C:/Windows/Fonts/lucon.ttf",        # Lucida Console
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _find_bold_font(size):
    candidates = [
        "C:/Windows/Fonts/consolab.ttf",    # Consolas Bold
        "C:/Windows/Fonts/courbd.ttf",      # Courier New Bold
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return _find_mono_font(size)


def make_gradient(w, h, c1, c2):
    """生成垂直渐变背景"""
    img = Image.new("RGB", (w, h))
    for y in range(h):
        ratio = y / max(h - 1, 1)
        r = int(c1[0] + (c2[0] - c1[0]) * ratio)
        g = int(c1[1] + (c2[1] - c1[1]) * ratio)
        b = int(c1[2] + (c2[2] - c1[2]) * ratio)
        for x in range(w):
            img.putpixel((x, y), (r, g, b))
    return img


def draw_rounded_rect(draw, xy, radius, fill):
    """画圆角矩形"""
    x0, y0, x1, y1 = xy
    draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
    draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
    draw.pieslice([x0, y0, x0 + 2 * radius, y0 + 2 * radius],
                  180, 270, fill=fill)
    draw.pieslice([x1 - 2 * radius, y0, x1, y0 + 2 * radius],
                  270, 360, fill=fill)
    draw.pieslice([x0, y1 - 2 * radius, x0 + 2 * radius, y1],
                  90, 180, fill=fill)
    draw.pieslice([x1 - 2 * radius, y1 - 2 * radius, x1, y1],
                  0, 90, fill=fill)


class CodeScreenshotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("代码截图美化")
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.resizable(False, False)
        self._preview_photo = None

        if not HAS_PIL or not HAS_PYGMENTS:
            self._dep_error()
        else:
            self._build_ui()

    def _dep_error(self):
        f = tk.Frame(self)
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="需要安装依赖",
                 font=("Microsoft YaHei", 18, "bold"),
                 fg="#c62828").pack(pady=(0, 16))
        tk.Label(f, text="pip install Pillow pygments",
                 font=("Consolas", 14, "bold"), fg="#1a73e8").pack()

    def _build_ui(self):
        # ── 顶部 ──
        top = tk.Frame(self)
        top.pack(fill="x", padx=14, pady=(10, 4))
        tk.Label(top, text="代码截图美化",
                 font=("Microsoft YaHei", 15, "bold")).pack(side="left")
        tk.Label(top, text="让代码变成好看的图片",
                 font=("Microsoft YaHei", 10), fg="#888").pack(side="left", padx=10)

        # ── 主体（左右分栏）──
        body = tk.Frame(self)
        body.pack(fill="both", expand=True, padx=14, pady=(0, 6))

        # 左：代码输入
        left = tk.Frame(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        tk.Label(left, text="粘贴代码：",
                 font=("Microsoft YaHei", 9)).pack(anchor="w")
        self._code_text = scrolledtext.ScrolledText(
            left, font=("Consolas", 11), wrap="none",
            bg="#282a36", fg="#f8f8f2", insertbackground="white")
        self._code_text.pack(fill="both", expand=True, pady=(2, 0))
        self._code_text.insert("1.0",
                               'def hello():\n    print("Hello, World!")\n\nhello()')

        # 右：设置
        right = tk.Frame(body, width=240)
        right.pack(side="right", fill="y", padx=(6, 0))
        right.pack_propagate(False)

        # 语言
        tk.Label(right, text="语言：",
                 font=("Microsoft YaHei", 9)).pack(anchor="w", pady=(0, 2))
        self._lang_var = tk.StringVar(value="python")
        ttk.Combobox(right, values=LANGUAGES,
                     textvariable=self._lang_var,
                     font=("Microsoft YaHei", 9), width=18).pack(anchor="w")

        # 主题
        tk.Label(right, text="代码主题：",
                 font=("Microsoft YaHei", 9)).pack(anchor="w", pady=(8, 2))
        styles = sorted(get_all_styles())
        self._theme_var = tk.StringVar(value="monokai")
        ttk.Combobox(right, values=styles,
                     textvariable=self._theme_var,
                     font=("Microsoft YaHei", 9), width=18).pack(anchor="w")

        # 背景
        tk.Label(right, text="背景：",
                 font=("Microsoft YaHei", 9)).pack(anchor="w", pady=(8, 2))
        self._bg_var = tk.StringVar(value="紫蓝渐变")
        ttk.Combobox(right, values=list(BACKGROUNDS.keys()),
                     textvariable=self._bg_var,
                     font=("Microsoft YaHei", 9), width=18).pack(anchor="w")

        # 字号
        tk.Label(right, text="字号：",
                 font=("Microsoft YaHei", 9)).pack(anchor="w", pady=(8, 2))
        self._fontsize_var = tk.IntVar(value=16)
        tk.Spinbox(right, from_=10, to=30, textvariable=self._fontsize_var,
                   font=("Microsoft YaHei", 9), width=6).pack(anchor="w")

        # 内边距
        tk.Label(right, text="内边距：",
                 font=("Microsoft YaHei", 9)).pack(anchor="w", pady=(8, 2))
        self._padding_var = tk.IntVar(value=40)
        tk.Spinbox(right, from_=10, to=100, increment=10,
                   textvariable=self._padding_var,
                   font=("Microsoft YaHei", 9), width=6).pack(anchor="w")

        # 窗口样式
        self._show_dots_var = tk.BooleanVar(value=True)
        tk.Checkbutton(right, text="显示窗口圆点",
                       variable=self._show_dots_var,
                       font=("Microsoft YaHei", 9)).pack(anchor="w", pady=(8, 0))

        self._show_lines_var = tk.BooleanVar(value=True)
        tk.Checkbutton(right, text="显示行号",
                       variable=self._show_lines_var,
                       font=("Microsoft YaHei", 9)).pack(anchor="w")

        # 窗口标题
        tk.Label(right, text="窗口标题：",
                 font=("Microsoft YaHei", 9)).pack(anchor="w", pady=(8, 2))
        self._title_var = tk.StringVar(value="")
        tk.Entry(right, textvariable=self._title_var,
                 font=("Microsoft YaHei", 9), width=20).pack(anchor="w")

        # 按钮
        tk.Button(right, text="生成预览",
                  font=("Microsoft YaHei", 11, "bold"),
                  command=self._generate).pack(fill="x", pady=(14, 4))
        tk.Button(right, text="保存图片",
                  font=("Microsoft YaHei", 10),
                  command=self._save).pack(fill="x")

        # ── 底部预览 ──
        pf = tk.LabelFrame(self, text=" 预览 ",
                            font=("Microsoft YaHei", 9))
        pf.pack(fill="x", padx=14, pady=(0, 10))
        self._preview_label = tk.Label(pf, bg="#eee", height=10)
        self._preview_label.pack(fill="x", padx=4, pady=4)

        self._result_image = None

    def _render_image(self):
        code = self._code_text.get("1.0", "end-1c")
        if not code.strip():
            return None

        lang = self._lang_var.get()
        theme_name = self._theme_var.get()
        font_size = self._fontsize_var.get()
        padding = self._padding_var.get()
        show_dots = self._show_dots_var.get()
        show_lines = self._show_lines_var.get()
        bg_name = self._bg_var.get()
        win_title = self._title_var.get().strip()

        # 获取 lexer 和 style
        try:
            lexer = get_lexer_by_name(lang)
        except Exception:
            lexer = guess_lexer(code)

        style = get_style_by_name(theme_name)
        code_bg = style.background_color or "#282a36"

        # 字体
        font = _find_mono_font(font_size)
        font_bold = _find_bold_font(font_size)

        # 测量字符尺寸
        bbox = font.getbbox("M")
        char_w = bbox[2] - bbox[0]
        line_h = int(font_size * 1.55)

        lines = code.split("\n")
        num_lines = len(lines)

        # 行号宽度
        line_num_chars = len(str(num_lines)) + 1
        line_num_w = char_w * line_num_chars + 12 if show_lines else 0

        # 计算代码区尺寸
        max_line_len = max(len(line) for line in lines) if lines else 0
        code_w = max_line_len * char_w + line_num_w + 20
        code_h = num_lines * line_h + 12

        # 窗口镶边
        title_bar_h = 40 if show_dots else 0
        corner_r = 12

        # 内部窗口尺寸
        win_w = code_w + padding * 2
        win_h = code_h + padding + (padding // 2) + title_bar_h

        # 外部图片（加背景边距）
        margin = 48
        img_w = win_w + margin * 2
        img_h = win_h + margin * 2

        # 创建背景
        bg_colors = BACKGROUNDS.get(bg_name, ((74, 0, 224), (142, 45, 226)))
        if bg_colors[0] is None:
            # 透明背景
            img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        else:
            img = make_gradient(img_w, img_h, bg_colors[0], bg_colors[1])

        draw = ImageDraw.Draw(img)

        # 画代码窗口（圆角矩形）
        wx0 = margin
        wy0 = margin
        wx1 = margin + win_w
        wy1 = margin + win_h

        # 窗口阴影
        if bg_colors[0] is not None:
            for offset in range(6, 0, -1):
                alpha = 20 + offset * 5
                shadow_color = (0, 0, 0, alpha) if img.mode == "RGBA" else (
                    max(0, 30 - offset * 5),) * 3
                draw_rounded_rect(draw,
                                  (wx0 + offset * 2, wy0 + offset * 2,
                                   wx1 + offset * 2, wy1 + offset * 2),
                                  corner_r, shadow_color)

        # 窗口背景
        draw_rounded_rect(draw, (wx0, wy0, wx1, wy1), corner_r, code_bg)

        # 标题栏圆点
        if show_dots:
            dots_y = wy0 + title_bar_h // 2
            dot_r = 7
            dot_x_start = wx0 + 20
            colors = ["#FF5F57", "#FEBC2E", "#28C840"]
            for i, c in enumerate(colors):
                cx = dot_x_start + i * 24
                draw.ellipse([cx - dot_r, dots_y - dot_r,
                              cx + dot_r, dots_y + dot_r], fill=c)

            # 窗口标题
            if win_title:
                title_font = _find_mono_font(13)
                tw = title_font.getlength(win_title)
                tx = wx0 + win_w // 2 - tw // 2
                draw.text((tx, dots_y - 7), win_title,
                          fill="#888888", font=title_font)

        # 代码区域起始位置
        code_x0 = wx0 + padding
        code_y0 = wy0 + title_bar_h + (padding // 2)

        # 语法高亮渲染
        tokens = list(lex(code, lexer))
        x = code_x0 + line_num_w
        y = code_y0
        line_idx = 1

        # 先画行号
        if show_lines:
            line_num_font = _find_mono_font(font_size)
            for i in range(1, num_lines + 1):
                ln_str = str(i).rjust(line_num_chars)
                draw.text((code_x0, code_y0 + (i - 1) * line_h),
                          ln_str, fill="#666666", font=line_num_font)

        # 画代码 token
        for tok_type, tok_value in tokens:
            tok_style = style.style_for_token(tok_type)
            color = "#" + tok_style["color"] if tok_style["color"] else "#f8f8f2"
            use_bold = tok_style.get("bold", False)
            cur_font = font_bold if use_bold else font

            parts = tok_value.split("\n")
            for pi, part in enumerate(parts):
                if pi > 0:
                    x = code_x0 + line_num_w
                    y += line_h
                    line_idx += 1
                if part:
                    draw.text((x, y), part, fill=color, font=cur_font)
                    x += cur_font.getlength(part)

        return img

    def _generate(self):
        try:
            img = self._render_image()
            if img is None:
                messagebox.showinfo("提示", "请先输入代码")
                return
            self._result_image = img

            # 缩放预览
            preview_w = WINDOW_W - 36
            preview_h = 160
            ratio = min(preview_w / img.width, preview_h / img.height, 1.0)
            dw = max(int(img.width * ratio), 1)
            dh = max(int(img.height * ratio), 1)
            disp = img.resize((dw, dh), Image.LANCZOS)
            self._preview_photo = ImageTk.PhotoImage(disp)
            self._preview_label.configure(image=self._preview_photo)
        except Exception as e:
            messagebox.showerror("渲染失败", str(e))

    def _save(self):
        if self._result_image is None:
            self._generate()
        if self._result_image is None:
            return

        path = filedialog.asksaveasfilename(
            title="保存截图",
            initialfile="code_screenshot.png",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if not path:
            return

        if path.lower().endswith(".jpg"):
            if self._result_image.mode == "RGBA":
                bg = Image.new("RGB", self._result_image.size, (255, 255, 255))
                bg.paste(self._result_image,
                         mask=self._result_image.split()[3])
                bg.save(path, quality=95)
            else:
                self._result_image.save(path, quality=95)
        else:
            self._result_image.save(path)

        messagebox.showinfo("完成",
                            f"已保存到：\n{path}\n\n"
                            f"尺寸：{self._result_image.width} x "
                            f"{self._result_image.height} px")


if __name__ == "__main__":
    app = CodeScreenshotApp()
    app.mainloop()
