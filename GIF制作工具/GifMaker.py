"""
GIF 制作工具 1.0 —— GUI 图形窗口版
选择一组图片 → 设置帧率和尺寸 → 一键生成 GIF 动图
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

WINDOW_WIDTH = 720
WINDOW_HEIGHT = 560
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def format_size(b):
    if b < 1024:
        return f"{b} B"
    elif b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b / (1024 * 1024):.2f} MB"


class GifMakerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GIF 制作工具 1.0")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)
        self._images = []

        if not HAS_PIL:
            self._dep_error()
        else:
            self._show_start()

    def _clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    def _dep_error(self):
        self._clear()
        f = tk.Frame(self.container); f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="缺少依赖库", font=("Microsoft YaHei", 20, "bold"), fg="#c62828").pack(pady=(0, 12))
        tk.Label(f, text="pip install Pillow", font=("Consolas", 14, "bold"), fg="#1a73e8").pack(pady=12)

    # ── 开始页 ───────────────────────────────────────

    def _show_start(self):
        self._clear()
        self._images = []

        f = tk.Frame(self.container); f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="GIF 制作工具", font=("Microsoft YaHei", 24, "bold")).pack(pady=(0, 6))
        tk.Label(f, text="选一组图片，生成 GIF 动图",
                 font=("Microsoft YaHei", 10), fg="#666").pack(pady=(0, 35))

        tk.Button(f, text="选择图片文件", font=("Microsoft YaHei", 13),
                  width=20, height=2, command=self._pick_files).pack(pady=6)
        tk.Label(f, text="可一次选多张，按文件名顺序排列作为帧",
                 font=("Microsoft YaHei", 9), fg="#999").pack(pady=(4, 10))

        tk.Button(f, text="选择整个文件夹", font=("Microsoft YaHei", 13),
                  width=20, height=2, command=self._pick_folder).pack(pady=6)
        tk.Label(f, text="自动按文件名排序加载文件夹内所有图片",
                 font=("Microsoft YaHei", 9), fg="#999").pack()

    def _pick_files(self):
        files = filedialog.askopenfilenames(
            title="选择图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.webp *.bmp")],
        )
        if not files:
            return
        self._images = sorted(files)
        if len(self._images) < 2:
            messagebox.showwarning("提示", "请至少选择 2 张图片。")
            return
        self._show_settings()

    def _pick_folder(self):
        folder = filedialog.askdirectory(title="选择图片文件夹")
        if not folder:
            return
        imgs = []
        for f in sorted(os.listdir(folder)):
            full = os.path.join(folder, f)
            if os.path.isfile(full) and os.path.splitext(f)[1].lower() in IMAGE_EXTS:
                imgs.append(full)
        if len(imgs) < 2:
            messagebox.showwarning("提示", "文件夹中需要至少 2 张图片。")
            return
        self._images = imgs
        self._show_settings()

    # ── 设置页 ───────────────────────────────────────

    def _show_settings(self):
        self._clear()
        num = len(self._images)

        top = tk.Frame(self.container)
        top.pack(fill="x", padx=20, pady=(15, 5))
        tk.Button(top, text="← 返回", font=("Microsoft YaHei", 10), command=self._show_start).pack(side="left")
        tk.Label(top, text="GIF 设置", font=("Microsoft YaHei", 14, "bold")).pack(side="left", padx=15)

        body = tk.Frame(self.container)
        body.pack(fill="both", expand=True, padx=25, pady=10)

        tk.Label(body, text=f"已选择 {num} 张图片（即 {num} 帧）", font=("Microsoft YaHei", 11, "bold")).pack(anchor="w", pady=(0, 8))

        # 帧列表
        lb = tk.Listbox(body, height=min(6, num), font=("Microsoft YaHei", 9))
        for i, v in enumerate(self._images):
            lb.insert("end", f"  帧 {i+1}:  {os.path.basename(v)}")
        lb.pack(fill="x", pady=(0, 12))

        # 帧率
        r1 = tk.Frame(body); r1.pack(fill="x", pady=4)
        tk.Label(r1, text="帧率（每秒几帧）：", font=("Microsoft YaHei", 10)).pack(side="left")
        self._fps_var = tk.IntVar(value=5)
        tk.Scale(r1, from_=1, to=30, orient="horizontal", variable=self._fps_var, length=200).pack(side="left", padx=10)
        tk.Label(r1, text="数值越大播放越快", font=("Microsoft YaHei", 9), fg="#888").pack(side="left")

        # 尺寸
        r2 = tk.Frame(body); r2.pack(fill="x", pady=4)
        tk.Label(r2, text="输出宽度（像素）：", font=("Microsoft YaHei", 10)).pack(side="left")
        self._width_var = tk.StringVar(value="0")
        tk.Entry(r2, textvariable=self._width_var, width=8, font=("Microsoft YaHei", 10)).pack(side="left", padx=10)
        tk.Label(r2, text="填 0 = 使用原图尺寸，填数字则等比缩放", font=("Microsoft YaHei", 9), fg="#888").pack(side="left")

        # 循环
        self._loop_var = tk.BooleanVar(value=True)
        tk.Checkbutton(body, text="无限循环播放", variable=self._loop_var,
                       font=("Microsoft YaHei", 10)).pack(anchor="w", pady=(8, 0))

        # 生成
        tk.Button(body, text="生成 GIF", font=("Microsoft YaHei", 13, "bold"),
                  width=16, height=2, command=self._do_generate).pack(pady=(18, 0))

    def _do_generate(self):
        fps = self._fps_var.get()
        duration = max(1, int(1000 / fps))  # ms per frame

        try:
            target_w = int(self._width_var.get())
        except ValueError:
            target_w = 0

        loop = 0 if self._loop_var.get() else 1

        save_path = filedialog.asksaveasfilename(
            title="保存 GIF",
            defaultextension=".gif",
            initialfile="output.gif",
            filetypes=[("GIF", "*.gif")],
        )
        if not save_path:
            return

        try:
            frames = []
            for path in self._images:
                img = Image.open(path).convert("RGBA")
                if target_w > 0:
                    ratio = target_w / img.size[0]
                    new_h = max(1, int(img.size[1] * ratio))
                    img = img.resize((target_w, new_h), Image.LANCZOS)
                # GIF 不支持 RGBA，转换
                bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
                bg.paste(img, mask=img)
                frames.append(bg.convert("RGB"))

            # 统一尺寸（以第一帧为基准）
            base_size = frames[0].size
            for i in range(1, len(frames)):
                if frames[i].size != base_size:
                    frames[i] = frames[i].resize(base_size, Image.LANCZOS)

            frames[0].save(
                save_path,
                save_all=True,
                append_images=frames[1:],
                duration=duration,
                loop=loop,
                optimize=True,
            )

            size = format_size(os.path.getsize(save_path))
            self._show_result(True, save_path, size, len(frames), fps)

        except Exception as e:
            self._show_result(False, str(e), "", 0, 0)

    # ── 结果页 ───────────────────────────────────────

    def _show_result(self, success, info, size, frames, fps):
        self._clear()
        f = tk.Frame(self.container); f.place(relx=0.5, rely=0.5, anchor="center")

        if success:
            tk.Label(f, text="GIF 生成成功", font=("Microsoft YaHei", 22, "bold"), fg="#2e7d32").pack(pady=(0, 15))
            tk.Label(f, text=f"{frames} 帧  |  {fps} FPS  |  文件大小 {size}",
                     font=("Microsoft YaHei", 12), fg="#555").pack()
            tk.Label(f, text=os.path.basename(info), font=("Microsoft YaHei", 11, "bold"), fg="#1a73e8").pack(pady=(8, 3))
            tk.Label(f, text=os.path.dirname(info), font=("Microsoft YaHei", 9), fg="#999").pack(pady=(0, 20))
        else:
            tk.Label(f, text="生成失败", font=("Microsoft YaHei", 22, "bold"), fg="#c62828").pack(pady=(0, 15))
            tk.Label(f, text=info, font=("Microsoft YaHei", 10), fg="#c62828", wraplength=500).pack(pady=(0, 20))

        btn = tk.Frame(f); btn.pack()
        tk.Button(btn, text="继续制作", font=("Microsoft YaHei", 11), width=12,
                  command=self._show_start).pack(side="left", padx=6)
        if success:
            tk.Button(btn, text="打开所在文件夹", font=("Microsoft YaHei", 11), width=14,
                      command=lambda: os.startfile(os.path.dirname(info))).pack(side="left", padx=6)


if __name__ == "__main__":
    app = GifMakerApp()
    app.mainloop()
