"""
屏幕取色器 —— GUI 图形窗口版
鼠标指哪取哪，实时显示颜色值
支持放大镜、HEX/RGB/HSL、颜色历史
"""

import tkinter as tk
from tkinter import ttk, messagebox
import ctypes
import colorsys
import os

try:
    from PIL import Image, ImageGrab, ImageTk, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

WINDOW_W = 460
WINDOW_H = 580
MAG_SIZE = 11       # 放大镜取样区域 11x11 像素
MAG_DISPLAY = 143   # 放大镜显示尺寸
MAG_ZOOM = MAG_DISPLAY // MAG_SIZE  # 每像素放大倍数


def get_cursor_pos():
    """获取全局鼠标坐标"""
    pt = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def get_pixel_color(x, y):
    """用 GDI 获取屏幕某点颜色（最快）"""
    hdc = ctypes.windll.user32.GetDC(0)
    pixel = ctypes.windll.gdi32.GetPixel(hdc, x, y)
    ctypes.windll.user32.ReleaseDC(0, hdc)
    if pixel == -1:
        return (0, 0, 0)
    r = pixel & 0xFF
    g = (pixel >> 8) & 0xFF
    b = (pixel >> 16) & 0xFF
    return (r, g, b)


def rgb_to_hsl(r, g, b):
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return int(h * 360), int(s * 100), int(l * 100)


def contrast_color(r, g, b):
    """返回黑或白，用于文字对比色"""
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    return "#000000" if luma > 128 else "#ffffff"


# 需要 ctypes.wintypes
import ctypes.wintypes


class ColorPickerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("屏幕取色器")
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        self._picking = False
        self._current_rgb = (0, 0, 0)
        self._history = []  # [(r,g,b), ...]
        self._mag_photo = None

        if not HAS_PIL:
            f = tk.Frame(self)
            f.place(relx=0.5, rely=0.5, anchor="center")
            tk.Label(f, text="pip install Pillow",
                     font=("Consolas", 14, "bold"), fg="#1a73e8").pack()
            return

        self._build_ui()

    def _build_ui(self):
        # ── 标题 + 开关 ──
        top = tk.Frame(self)
        top.pack(fill="x", padx=16, pady=(12, 6))
        tk.Label(top, text="屏幕取色器",
                 font=("Microsoft YaHei", 16, "bold")).pack(side="left")

        self._pick_btn = tk.Button(
            top, text="开始取色 (F1)",
            font=("Microsoft YaHei", 11, "bold"),
            bg="#1a73e8", fg="white", relief="flat",
            command=self._toggle_picking)
        self._pick_btn.pack(side="right")

        # ── 颜色预览 + 放大镜 ──
        mid = tk.Frame(self)
        mid.pack(fill="x", padx=16, pady=(0, 8))

        # 左：颜色方块
        self._color_frame = tk.Frame(mid, width=140, height=140,
                                      bg="#000000", relief="solid", bd=1)
        self._color_frame.pack(side="left", padx=(0, 12))
        self._color_frame.pack_propagate(False)
        self._color_hex_label = tk.Label(
            self._color_frame, text="#000000",
            font=("Consolas", 16, "bold"),
            bg="#000000", fg="#ffffff")
        self._color_hex_label.place(relx=0.5, rely=0.5, anchor="center")

        # 右：放大镜
        mag_outer = tk.Frame(mid, relief="solid", bd=1)
        mag_outer.pack(side="left")
        self._mag_canvas = tk.Canvas(mag_outer,
                                      width=MAG_DISPLAY, height=MAG_DISPLAY,
                                      bg="#1a1a2e", highlightthickness=0)
        self._mag_canvas.pack()

        # 坐标显示
        self._pos_label = tk.Label(mid, text="X: 0  Y: 0",
                                    font=("Consolas", 10), fg="#888")
        self._pos_label.pack(side="left", padx=(12, 0), anchor="n")

        # ── 颜色值显示 ──
        val_frame = tk.LabelFrame(self, text=" 颜色值（点击可复制）",
                                   font=("Microsoft YaHei", 10, "bold"))
        val_frame.pack(fill="x", padx=16, pady=(0, 8))

        self._value_rows = {}
        for label_text, key in [("HEX", "hex"), ("RGB", "rgb"),
                                 ("HSL", "hsl"), ("RGBA", "rgba")]:
            r = tk.Frame(val_frame)
            r.pack(fill="x", padx=8, pady=2)
            tk.Label(r, text=f"{label_text}：",
                     font=("Microsoft YaHei", 10), width=6,
                     anchor="e").pack(side="left")
            val_label = tk.Label(r, text="—",
                                  font=("Consolas", 12, "bold"),
                                  fg="#333", cursor="hand2")
            val_label.pack(side="left", padx=4)
            val_label.bind("<Button-1>",
                           lambda e, k=key: self._copy_value(k))
            # 复制提示
            tip = tk.Label(r, text="", font=("Microsoft YaHei", 8),
                           fg="#2e7d32")
            tip.pack(side="right")
            self._value_rows[key] = (val_label, tip)

        # ── 历史记录 ──
        hist_frame = tk.LabelFrame(self, text=" 历史记录（点击恢复 / 右键删除）",
                                    font=("Microsoft YaHei", 10, "bold"))
        hist_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self._hist_canvas = tk.Canvas(hist_frame, height=120, bg="#fafafa",
                                       highlightthickness=0)
        self._hist_canvas.pack(fill="both", expand=True, padx=8, pady=8)

        # 底部提示
        tk.Label(self, text="取色中移动鼠标 → 实时预览 │ 按空格/回车锁定颜色 │ Esc 停止",
                 font=("Microsoft YaHei", 8), fg="#aaa").pack(pady=(0, 8))

        # ── 快捷键 ──
        self.bind("<F1>", lambda e: self._toggle_picking())
        self.bind("<space>", lambda e: self._lock_color())
        self.bind("<Return>", lambda e: self._lock_color())
        self.bind("<Escape>", lambda e: self._stop_picking())

    def _toggle_picking(self):
        if self._picking:
            self._stop_picking()
        else:
            self._start_picking()

    def _start_picking(self):
        self._picking = True
        self._pick_btn.configure(text="停止取色 (Esc)", bg="#c62828")
        self._poll()

    def _stop_picking(self):
        self._picking = False
        self._pick_btn.configure(text="开始取色 (F1)", bg="#1a73e8")

    def _poll(self):
        if not self._picking:
            return

        x, y = get_cursor_pos()

        # 检查鼠标是否在本窗口上
        try:
            wx = self.winfo_rootx()
            wy = self.winfo_rooty()
            ww = self.winfo_width()
            wh = self.winfo_height()
            in_window = (wx <= x <= wx + ww and wy <= y <= wy + wh)
        except Exception:
            in_window = False

        if not in_window:
            r, g, b = get_pixel_color(x, y)
            self._current_rgb = (r, g, b)
            self._update_display(r, g, b)
            self._update_magnifier(x, y)

        self._pos_label.configure(text=f"X: {x}  Y: {y}")
        self.after(50, self._poll)

    def _update_display(self, r, g, b):
        hex_str = f"#{r:02X}{g:02X}{b:02X}"
        fg = contrast_color(r, g, b)

        self._color_frame.configure(bg=hex_str)
        self._color_hex_label.configure(text=hex_str, bg=hex_str, fg=fg)

        h, s, l = rgb_to_hsl(r, g, b)

        values = {
            "hex": hex_str,
            "rgb": f"rgb({r}, {g}, {b})",
            "hsl": f"hsl({h}, {s}%, {l}%)",
            "rgba": f"rgba({r}, {g}, {b}, 1.0)",
        }
        for key, val in values.items():
            self._value_rows[key][0].configure(text=val)

    def _update_magnifier(self, cx, cy):
        try:
            half = MAG_SIZE // 2
            bbox = (cx - half, cy - half, cx + half + 1, cy + half + 1)
            grab = ImageGrab.grab(bbox)

            # 放大（最近邻，保持像素锐利）
            mag = grab.resize((MAG_DISPLAY, MAG_DISPLAY), Image.NEAREST)

            # 画十字准心
            draw = ImageDraw.Draw(mag)
            center = MAG_DISPLAY // 2
            cell = MAG_ZOOM
            # 中心格边框
            x0 = center - cell // 2
            y0 = center - cell // 2
            draw.rectangle([x0, y0, x0 + cell, y0 + cell],
                           outline="#FF0000", width=2)
            # 十字线
            draw.line([(center, 0), (center, MAG_DISPLAY)],
                      fill="#FF000080", width=1)
            draw.line([(0, center), (MAG_DISPLAY, center)],
                      fill="#FF000080", width=1)

            self._mag_photo = ImageTk.PhotoImage(mag)
            self._mag_canvas.delete("all")
            self._mag_canvas.create_image(0, 0, anchor="nw",
                                           image=self._mag_photo)
        except Exception:
            pass

    def _lock_color(self):
        if not self._picking:
            return
        rgb = self._current_rgb
        if rgb not in self._history:
            self._history.insert(0, rgb)
            if len(self._history) > 24:
                self._history.pop()
        self._draw_history()
        # 自动复制 HEX
        hex_str = f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
        self.clipboard_clear()
        self.clipboard_append(hex_str)
        self._flash_tip("hex", "已复制!")

    def _draw_history(self):
        c = self._hist_canvas
        c.delete("all")
        cols = 8
        size = 40
        pad = 6
        for i, (r, g, b) in enumerate(self._history):
            row = i // cols
            col = i % cols
            x = pad + col * (size + pad)
            y = pad + row * (size + pad)
            hex_str = f"#{r:02X}{g:02X}{b:02X}"
            fg = contrast_color(r, g, b)

            rect_id = c.create_rectangle(x, y, x + size, y + size,
                                          fill=hex_str, outline="#ccc")
            text_id = c.create_text(x + size // 2, y + size // 2,
                                     text=hex_str, font=("Consolas", 7),
                                     fill=fg)
            # 点击恢复
            for item_id in (rect_id, text_id):
                c.tag_bind(item_id, "<Button-1>",
                           lambda e, rgb=(r, g, b): self._restore_color(rgb))
                c.tag_bind(item_id, "<Button-3>",
                           lambda e, rgb=(r, g, b): self._remove_history(rgb))

    def _restore_color(self, rgb):
        r, g, b = rgb
        self._current_rgb = rgb
        self._update_display(r, g, b)
        hex_str = f"#{r:02X}{g:02X}{b:02X}"
        self.clipboard_clear()
        self.clipboard_append(hex_str)
        self._flash_tip("hex", "已复制!")

    def _remove_history(self, rgb):
        if rgb in self._history:
            self._history.remove(rgb)
            self._draw_history()

    def _copy_value(self, key):
        text = self._value_rows[key][0].cget("text")
        if text and text != "—":
            self.clipboard_clear()
            self.clipboard_append(text)
            self._flash_tip(key, "已复制!")

    def _flash_tip(self, key, msg):
        tip_label = self._value_rows[key][1]
        tip_label.configure(text=msg)
        self.after(1500, lambda: tip_label.configure(text=""))


if __name__ == "__main__":
    app = ColorPickerApp()
    app.mainloop()
