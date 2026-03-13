"""
图片拼接工具 —— GUI 图形窗口版
将多张图片拼接成一张大图
支持横向拼接、纵向拼接、网格拼接
可调间距、背景色，支持 PNG / JPG 输出
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import os

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

WINDOW_WIDTH = 820
WINDOW_HEIGHT = 660

MODE_HORIZONTAL = "horizontal"
MODE_VERTICAL = "vertical"
MODE_GRID = "grid"


def stitch_images(image_paths, mode, gap=0, bg_color=(255, 255, 255),
                  columns=0, auto_resize=True, quality=95):
    """拼接图片，返回 PIL Image 对象"""
    imgs = [Image.open(p).convert("RGBA") for p in image_paths]
    n = len(imgs)

    if mode == MODE_HORIZONTAL:
        if auto_resize:
            # 统一高度为最小高度
            target_h = min(im.height for im in imgs)
            resized = []
            for im in imgs:
                ratio = target_h / im.height
                new_w = int(im.width * ratio)
                resized.append(im.resize((new_w, target_h), Image.LANCZOS))
            imgs = resized

        total_w = sum(im.width for im in imgs) + gap * (n - 1)
        total_h = max(im.height for im in imgs)
        canvas = Image.new("RGBA", (total_w, total_h), bg_color + (255,))

        x = 0
        for im in imgs:
            y_offset = (total_h - im.height) // 2
            canvas.paste(im, (x, y_offset), im)
            x += im.width + gap

    elif mode == MODE_VERTICAL:
        if auto_resize:
            # 统一宽度为最小宽度
            target_w = min(im.width for im in imgs)
            resized = []
            for im in imgs:
                ratio = target_w / im.width
                new_h = int(im.height * ratio)
                resized.append(im.resize((target_w, new_h), Image.LANCZOS))
            imgs = resized

        total_w = max(im.width for im in imgs)
        total_h = sum(im.height for im in imgs) + gap * (n - 1)
        canvas = Image.new("RGBA", (total_w, total_h), bg_color + (255,))

        y = 0
        for im in imgs:
            x_offset = (total_w - im.width) // 2
            canvas.paste(im, (x_offset, y), im)
            y += im.height + gap

    else:  # grid
        cols = columns if columns > 0 else _auto_cols(n)
        rows = (n + cols - 1) // cols

        if auto_resize:
            # 统一到平均尺寸
            avg_w = sum(im.width for im in imgs) // n
            avg_h = sum(im.height for im in imgs) // n
            resized = []
            for im in imgs:
                resized.append(im.resize((avg_w, avg_h), Image.LANCZOS))
            imgs = resized

        cell_w = max(im.width for im in imgs)
        cell_h = max(im.height for im in imgs)
        total_w = cols * cell_w + (cols - 1) * gap
        total_h = rows * cell_h + (rows - 1) * gap
        canvas = Image.new("RGBA", (total_w, total_h), bg_color + (255,))

        for i, im in enumerate(imgs):
            c = i % cols
            r = i // cols
            x = c * (cell_w + gap) + (cell_w - im.width) // 2
            y = r * (cell_h + gap) + (cell_h - im.height) // 2
            canvas.paste(im, (x, y), im)

    return canvas


def _auto_cols(n):
    """自动计算网格列数"""
    if n <= 2:
        return n
    if n <= 4:
        return 2
    if n <= 9:
        return 3
    if n <= 16:
        return 4
    return 5


class ImageStitcherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("图片拼接工具")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self._image_paths = []
        self._preview_photo = None
        self._bg_color = (255, 255, 255)

        if not HAS_PIL:
            self._dep_error()
        else:
            self._build_ui()

    # ── 缺依赖提示 ──

    def _dep_error(self):
        f = tk.Frame(self)
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="缺少依赖库", font=("Microsoft YaHei", 20, "bold"),
                 fg="#c62828").pack(pady=(0, 12))
        tk.Label(f, text="pip install Pillow", font=("Consolas", 14, "bold"),
                 fg="#1a73e8").pack(pady=12)

    # ── 界面布局 ──

    def _build_ui(self):
        # 左侧：文件列表 + 操作按钮
        left = tk.Frame(self, width=300)
        left.pack(side="left", fill="y", padx=(12, 0), pady=12)
        left.pack_propagate(False)

        tk.Label(left, text="图片拼接工具",
                 font=("Microsoft YaHei", 16, "bold")).pack(anchor="w", pady=(0, 10))

        # 添加/移除按钮
        btn_row = tk.Frame(left)
        btn_row.pack(fill="x", pady=(0, 5))
        tk.Button(btn_row, text="添加图片", font=("Microsoft YaHei", 10),
                  command=self._add_images).pack(side="left", padx=(0, 5))
        tk.Button(btn_row, text="清空列表", font=("Microsoft YaHei", 10),
                  command=self._clear_list).pack(side="left", padx=(0, 5))

        # 文件列表
        list_frame = tk.Frame(left)
        list_frame.pack(fill="both", expand=True, pady=(0, 8))

        self._listbox = tk.Listbox(list_frame, font=("Microsoft YaHei", 9),
                                   selectmode="extended")
        sb = ttk.Scrollbar(list_frame, orient="vertical",
                           command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=sb.set)
        self._listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # 上移 / 下移 / 删除
        order_row = tk.Frame(left)
        order_row.pack(fill="x", pady=(0, 8))
        tk.Button(order_row, text="↑ 上移", font=("Microsoft YaHei", 9),
                  width=7, command=self._move_up).pack(side="left", padx=(0, 4))
        tk.Button(order_row, text="↓ 下移", font=("Microsoft YaHei", 9),
                  width=7, command=self._move_down).pack(side="left", padx=(0, 4))
        tk.Button(order_row, text="删除选中", font=("Microsoft YaHei", 9),
                  width=8, command=self._remove_selected).pack(side="left")

        # ── 参数区 ──
        param = tk.LabelFrame(left, text=" 拼接参数 ",
                              font=("Microsoft YaHei", 10, "bold"))
        param.pack(fill="x", pady=(0, 8))

        # 拼接模式
        r1 = tk.Frame(param)
        r1.pack(fill="x", padx=8, pady=(6, 3))
        tk.Label(r1, text="模式：", font=("Microsoft YaHei", 9)).pack(side="left")
        self._mode_var = tk.StringVar(value="horizontal")
        modes = [("横向拼接", "horizontal"),
                 ("纵向拼接", "vertical"),
                 ("网格拼接", "grid")]
        for text, val in modes:
            tk.Radiobutton(r1, text=text, variable=self._mode_var, value=val,
                           font=("Microsoft YaHei", 9),
                           command=self._on_mode_change).pack(side="left", padx=2)

        # 网格列数（仅网格模式显示）
        self._grid_row = tk.Frame(param)
        self._grid_row.pack(fill="x", padx=8, pady=2)
        tk.Label(self._grid_row, text="每行列数：",
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self._cols_var = tk.IntVar(value=0)
        tk.Spinbox(self._grid_row, from_=0, to=10,
                   textvariable=self._cols_var, width=4,
                   font=("Microsoft YaHei", 10)).pack(side="left", padx=4)
        tk.Label(self._grid_row, text="0=自动",
                 font=("Microsoft YaHei", 8), fg="#888").pack(side="left")
        self._grid_row.pack_forget()  # 默认隐藏

        # 间距
        r2 = tk.Frame(param)
        r2.pack(fill="x", padx=8, pady=2)
        tk.Label(r2, text="间距(px)：", font=("Microsoft YaHei", 9)).pack(side="left")
        self._gap_var = tk.IntVar(value=0)
        tk.Spinbox(r2, from_=0, to=100, textvariable=self._gap_var, width=5,
                   font=("Microsoft YaHei", 10)).pack(side="left", padx=4)

        # 背景色
        r3 = tk.Frame(param)
        r3.pack(fill="x", padx=8, pady=2)
        tk.Label(r3, text="背景色：", font=("Microsoft YaHei", 9)).pack(side="left")
        self._bg_btn = tk.Button(r3, text="  ███  ", fg="#FFFFFF", bg="#FFFFFF",
                                 font=("Consolas", 10), relief="solid",
                                 command=self._pick_bg_color)
        self._bg_btn.pack(side="left", padx=4)
        self._bg_label = tk.Label(r3, text="#FFFFFF",
                                  font=("Consolas", 9), fg="#888")
        self._bg_label.pack(side="left")

        # 自动统一尺寸
        r4 = tk.Frame(param)
        r4.pack(fill="x", padx=8, pady=(2, 6))
        self._resize_var = tk.BooleanVar(value=True)
        tk.Checkbutton(r4, text="自动统一尺寸（推荐）",
                       variable=self._resize_var,
                       font=("Microsoft YaHei", 9)).pack(side="left")

        # 生成 / 保存按钮
        act_row = tk.Frame(left)
        act_row.pack(fill="x", pady=(0, 0))
        tk.Button(act_row, text="生成预览", font=("Microsoft YaHei", 11, "bold"),
                  width=12, command=self._preview).pack(side="left", padx=(0, 6))
        tk.Button(act_row, text="保存图片", font=("Microsoft YaHei", 11),
                  width=12, command=self._save).pack(side="left")

        # 右侧：预览区
        right = tk.Frame(self, bg="#f0f0f0", relief="sunken", bd=1)
        right.pack(side="right", fill="both", expand=True,
                   padx=12, pady=12)

        tk.Label(right, text="预览区", font=("Microsoft YaHei", 10),
                 fg="#aaa", bg="#f0f0f0").pack(pady=(8, 0))

        self._preview_label = tk.Label(right, bg="#f0f0f0")
        self._preview_label.pack(fill="both", expand=True, padx=10, pady=10)

        self._info_label = tk.Label(right, text="", font=("Microsoft YaHei", 9),
                                    fg="#666", bg="#f0f0f0")
        self._info_label.pack(pady=(0, 8))

    # ── 文件操作 ──

    def _add_images(self):
        paths = filedialog.askopenfilenames(
            title="选择图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.webp *.tiff")],
        )
        if not paths:
            return
        for p in paths:
            self._image_paths.append(p)
            self._listbox.insert("end", os.path.basename(p))
        self._update_title()

    def _clear_list(self):
        self._image_paths.clear()
        self._listbox.delete(0, "end")
        self._preview_label.configure(image="")
        self._preview_photo = None
        self._info_label.configure(text="")
        self._update_title()

    def _remove_selected(self):
        sel = list(self._listbox.curselection())
        if not sel:
            return
        for i in reversed(sel):
            self._image_paths.pop(i)
            self._listbox.delete(i)
        self._update_title()

    def _move_up(self):
        sel = list(self._listbox.curselection())
        if not sel or sel[0] == 0:
            return
        for i in sel:
            self._image_paths[i - 1], self._image_paths[i] = \
                self._image_paths[i], self._image_paths[i - 1]
        self._refresh_listbox()
        for i in sel:
            self._listbox.selection_set(i - 1)

    def _move_down(self):
        sel = list(self._listbox.curselection())
        if not sel or sel[-1] >= len(self._image_paths) - 1:
            return
        for i in reversed(sel):
            self._image_paths[i + 1], self._image_paths[i] = \
                self._image_paths[i], self._image_paths[i + 1]
        self._refresh_listbox()
        for i in sel:
            self._listbox.selection_set(i + 1)

    def _refresh_listbox(self):
        self._listbox.delete(0, "end")
        for p in self._image_paths:
            self._listbox.insert("end", os.path.basename(p))

    def _update_title(self):
        n = len(self._image_paths)
        self.title(f"图片拼接工具  ({n} 张图片)" if n else "图片拼接工具")

    # ── 参数操作 ──

    def _on_mode_change(self):
        if self._mode_var.get() == "grid":
            self._grid_row.pack(fill="x", padx=8, pady=2)
        else:
            self._grid_row.pack_forget()

    def _pick_bg_color(self):
        color = colorchooser.askcolor(
            initialcolor=self._bg_color, title="选择背景色")
        if color[0]:
            self._bg_color = tuple(int(c) for c in color[0])
            hex_str = color[1]
            self._bg_btn.configure(bg=hex_str, fg=hex_str)
            self._bg_label.configure(text=hex_str.upper())

    # ── 预览 ──

    def _do_stitch(self):
        """执行拼接，返回 PIL Image"""
        if len(self._image_paths) < 2:
            messagebox.showwarning("提示", "请至少添加 2 张图片")
            return None

        mode = self._mode_var.get()
        gap = self._gap_var.get()
        cols = self._cols_var.get() if mode == "grid" else 0
        auto_resize = self._resize_var.get()

        try:
            result = stitch_images(
                self._image_paths, mode, gap=gap,
                bg_color=self._bg_color, columns=cols,
                auto_resize=auto_resize)
            return result
        except Exception as e:
            messagebox.showerror("拼接失败", str(e))
            return None

    def _preview(self):
        result = self._do_stitch()
        if result is None:
            return

        self._result_image = result

        # 缩放到预览区大小
        preview_w = WINDOW_WIDTH - 300 - 50
        preview_h = WINDOW_HEIGHT - 80
        ratio = min(preview_w / result.width, preview_h / result.height, 1.0)
        disp_w = int(result.width * ratio)
        disp_h = int(result.height * ratio)
        disp = result.resize((disp_w, disp_h), Image.LANCZOS)

        self._preview_photo = ImageTk.PhotoImage(disp)
        self._preview_label.configure(image=self._preview_photo)

        w, h = result.size
        self._info_label.configure(
            text=f"尺寸：{w} × {h} px    |    {len(self._image_paths)} 张图片")

    # ── 保存 ──

    def _save(self):
        if not hasattr(self, '_result_image') or self._result_image is None:
            # 还没预览过，先拼一次
            result = self._do_stitch()
            if result is None:
                return
            self._result_image = result

        save_path = filedialog.asksaveasfilename(
            title="保存拼接图片",
            defaultextension=".png",
            initialfile=f"拼接_{len(self._image_paths)}张.png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg"),
                       ("BMP", "*.bmp")],
        )
        if not save_path:
            return

        try:
            output = self._result_image
            ext = os.path.splitext(save_path)[1].lower()

            # JPG/BMP 不支持透明，转为 RGB
            if ext in (".jpg", ".jpeg", ".bmp"):
                rgb = Image.new("RGB", output.size, self._bg_color)
                rgb.paste(output, mask=output.split()[3] if output.mode == "RGBA" else None)
                if ext in (".jpg", ".jpeg"):
                    rgb.save(save_path, "JPEG", quality=95)
                else:
                    rgb.save(save_path, "BMP")
            else:
                output.save(save_path, "PNG")

            messagebox.showinfo("保存成功", f"图片已保存至：\n{save_path}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))


if __name__ == "__main__":
    app = ImageStitcherApp()
    app.mainloop()
