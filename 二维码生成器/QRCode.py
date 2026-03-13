"""
二维码生成器 1.0 —— GUI 图形窗口版
输入文字/网址 → 生成二维码图片
支持自定义颜色、大小、边距，可保存为 PNG
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import os

try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

WINDOW_WIDTH = 680
WINDOW_HEIGHT = 580


class QRCodeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("二维码生成器 1.0")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)

        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self._fg_color = (0, 0, 0)
        self._bg_color = (255, 255, 255)
        self._qr_image = None  # PIL Image
        self._tk_image = None  # PhotoImage (prevent GC)

        if not HAS_QR or not HAS_PIL:
            self._dep_error()
        else:
            self._build_ui()

    def _dep_error(self):
        f = tk.Frame(self.container)
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="缺少依赖库", font=("Microsoft YaHei", 20, "bold"), fg="#c62828").pack(pady=(0, 12))
        tk.Label(f, text="请在命令行中运行：", font=("Microsoft YaHei", 11)).pack()
        tk.Label(f, text="pip install qrcode[pil] Pillow", font=("Consolas", 13, "bold"), fg="#1a73e8").pack(pady=12)

    def _build_ui(self):
        # ── 左侧控制面板 ─────────────────────────────
        left = tk.Frame(self.container, width=340)
        left.pack(side="left", fill="y", padx=(20, 10), pady=15)
        left.pack_propagate(False)

        tk.Label(left, text="二维码生成器", font=("Microsoft YaHei", 18, "bold")).pack(anchor="w", pady=(0, 15))

        # 输入内容
        tk.Label(left, text="输入内容（文字 / 网址）：", font=("Microsoft YaHei", 10)).pack(anchor="w", pady=(0, 3))
        self._content_text = tk.Text(left, height=5, font=("Microsoft YaHei", 10), wrap="word")
        self._content_text.pack(fill="x", pady=(0, 10))
        self._content_text.insert("1.0", "https://")

        # 容错等级
        r1 = tk.Frame(left)
        r1.pack(fill="x", pady=4)
        tk.Label(r1, text="容错等级：", font=("Microsoft YaHei", 10)).pack(side="left")
        self._error_var = tk.StringVar(value="M（推荐）")
        ttk.Combobox(r1, textvariable=self._error_var, state="readonly", width=14,
                     values=["L（7%）", "M（推荐）", "Q（25%）", "H（30%）"]).pack(side="left", padx=5)

        # 尺寸
        r2 = tk.Frame(left)
        r2.pack(fill="x", pady=4)
        tk.Label(r2, text="图片尺寸：", font=("Microsoft YaHei", 10)).pack(side="left")
        self._size_var = tk.StringVar(value="10")
        tk.Spinbox(r2, from_=5, to=30, textvariable=self._size_var, width=5,
                   font=("Microsoft YaHei", 10)).pack(side="left", padx=5)
        tk.Label(r2, text="（越大图片越清晰）", font=("Microsoft YaHei", 9), fg="#888").pack(side="left")

        # 边距
        r3 = tk.Frame(left)
        r3.pack(fill="x", pady=4)
        tk.Label(r3, text="边距大小：", font=("Microsoft YaHei", 10)).pack(side="left")
        self._border_var = tk.StringVar(value="4")
        tk.Spinbox(r3, from_=1, to=10, textvariable=self._border_var, width=5,
                   font=("Microsoft YaHei", 10)).pack(side="left", padx=5)

        # 颜色
        color_frame = tk.Frame(left)
        color_frame.pack(fill="x", pady=(8, 4))

        tk.Label(color_frame, text="前景色：", font=("Microsoft YaHei", 10)).pack(side="left")
        self._fg_btn = tk.Button(color_frame, text="  ", bg="black", width=3,
                                 command=lambda: self._pick_color("fg"))
        self._fg_btn.pack(side="left", padx=(0, 15))

        tk.Label(color_frame, text="背景色：", font=("Microsoft YaHei", 10)).pack(side="left")
        self._bg_btn = tk.Button(color_frame, text="  ", bg="white", width=3,
                                 command=lambda: self._pick_color("bg"))
        self._bg_btn.pack(side="left")

        # 生成按钮
        tk.Button(left, text="生成二维码", font=("Microsoft YaHei", 13, "bold"),
                  width=18, height=2, command=self._generate).pack(pady=(18, 8))

        # 保存按钮
        self._save_btn = tk.Button(left, text="保存为图片", font=("Microsoft YaHei", 11),
                                   width=18, command=self._save, state="disabled")
        self._save_btn.pack()

        # ── 右侧预览区 ──────────────────────────────
        right = tk.Frame(self.container, bg="#f0f0f0", relief="groove", bd=1)
        right.pack(side="left", fill="both", expand=True, padx=(0, 20), pady=15)

        tk.Label(right, text="预览", font=("Microsoft YaHei", 10, "bold"), bg="#f0f0f0").pack(pady=(10, 5))

        self._preview_label = tk.Label(right, text="在左侧输入内容\n点击「生成二维码」",
                                       font=("Microsoft YaHei", 11), fg="#999", bg="#f0f0f0")
        self._preview_label.pack(expand=True)

    def _pick_color(self, target):
        initial = self._fg_color if target == "fg" else self._bg_color
        color = colorchooser.askcolor(initialcolor=initial, title="选择颜色")
        if color[0]:
            rgb = tuple(int(c) for c in color[0])
            if target == "fg":
                self._fg_color = rgb
                self._fg_btn.config(bg=color[1])
            else:
                self._bg_color = rgb
                self._bg_btn.config(bg=color[1])

    def _generate(self):
        content = self._content_text.get("1.0", "end").strip()
        if not content:
            messagebox.showwarning("提示", "请输入要编码的内容。")
            return

        # 容错等级映射
        error_map = {
            "L（7%）": qrcode.constants.ERROR_CORRECT_L,
            "M（推荐）": qrcode.constants.ERROR_CORRECT_M,
            "Q（25%）": qrcode.constants.ERROR_CORRECT_Q,
            "H（30%）": qrcode.constants.ERROR_CORRECT_H,
        }
        error_level = error_map.get(self._error_var.get(), qrcode.constants.ERROR_CORRECT_M)

        try:
            box_size = int(self._size_var.get())
            border = int(self._border_var.get())
        except ValueError:
            box_size, border = 10, 4

        try:
            qr = qrcode.QRCode(
                version=None,  # 自动选择
                error_correction=error_level,
                box_size=box_size,
                border=border,
            )
            qr.add_data(content)
            qr.make(fit=True)

            img = qr.make_image(fill_color=self._fg_color, back_color=self._bg_color).convert("RGB")
            self._qr_image = img

            # 缩放用于预览（最大 280x280）
            preview = img.copy()
            preview.thumbnail((280, 280), Image.LANCZOS)
            self._tk_image = ImageTk.PhotoImage(preview)

            self._preview_label.config(image=self._tk_image, text="")
            self._save_btn.config(state="normal")

        except Exception as e:
            messagebox.showerror("生成失败", str(e))

    def _save(self):
        if not self._qr_image:
            return

        save_path = filedialog.asksaveasfilename(
            title="保存二维码",
            defaultextension=".png",
            initialfile="二维码.png",
            filetypes=[("PNG", "*.png"), ("JPG", "*.jpg")],
        )
        if not save_path:
            return

        try:
            self._qr_image.save(save_path)
            messagebox.showinfo("保存成功", f"二维码已保存至：\n{save_path}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))


if __name__ == "__main__":
    app = QRCodeApp()
    app.mainloop()
