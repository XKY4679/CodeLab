"""
网页截图工具 —— GUI 图形窗口版
用真实浏览器引擎渲染网页后截图
支持整页/视口/单个元素/批量元素截图
支持 1x-4x 高清倍率，完美捕获 JS 动态渲染内容
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
import time

HAS_PLAYWRIGHT = False
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    pass

HAS_PIL = False
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    pass

WINDOW_WIDTH = 820
WINDOW_HEIGHT = 680


class WebCaptureApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("网页截图工具")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self._preview_photo = None
        self._capturing = False

        if not HAS_PLAYWRIGHT:
            self._dep_error()
        else:
            self._build_ui()

    def _dep_error(self):
        f = tk.Frame(self)
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="需要安装 Playwright",
                 font=("Microsoft YaHei", 18, "bold"),
                 fg="#c62828").pack(pady=(0, 16))

        steps = tk.Frame(f)
        steps.pack()
        tk.Label(steps, text="步骤 1：安装 Python 库",
                 font=("Microsoft YaHei", 11), fg="#333",
                 anchor="w").pack(fill="x", pady=(0, 4))
        tk.Label(steps, text="pip install playwright Pillow",
                 font=("Consolas", 13, "bold"), fg="#1a73e8").pack(pady=(0, 16))

        tk.Label(steps, text="步骤 2：下载浏览器内核（只需一次，约 150MB）",
                 font=("Microsoft YaHei", 11), fg="#333",
                 anchor="w").pack(fill="x", pady=(0, 4))
        tk.Label(steps, text="playwright install chromium",
                 font=("Consolas", 13, "bold"), fg="#1a73e8").pack(pady=(0, 16))

        tk.Label(steps, text="安装完成后重新运行本工具即可",
                 font=("Microsoft YaHei", 10), fg="#888").pack(pady=(8, 0))

    def _build_ui(self):
        # ── 顶部：标题 ──
        top = tk.Frame(self)
        top.pack(fill="x", padx=16, pady=(14, 6))
        tk.Label(top, text="网页截图工具",
                 font=("Microsoft YaHei", 16, "bold")).pack(side="left")
        tk.Label(top, text="JS 动态渲染也能截",
                 font=("Microsoft YaHei", 10), fg="#888").pack(side="left", padx=12)

        # ── 文件/URL 选择 ──
        src_frame = tk.Frame(self)
        src_frame.pack(fill="x", padx=16, pady=(0, 6))

        tk.Label(src_frame, text="来源：",
                 font=("Microsoft YaHei", 10)).pack(side="left")
        self._url_var = tk.StringVar()
        self._url_entry = tk.Entry(src_frame, textvariable=self._url_var,
                                   font=("Microsoft YaHei", 10))
        self._url_entry.pack(side="left", fill="x", expand=True, padx=(4, 8))

        tk.Button(src_frame, text="选择 HTML 文件",
                  font=("Microsoft YaHei", 9),
                  command=self._select_file).pack(side="right")

        # ── 设置区（两列）──
        settings = tk.Frame(self)
        settings.pack(fill="x", padx=16, pady=(0, 6))

        col1 = tk.LabelFrame(settings, text=" 截图设置 ",
                              font=("Microsoft YaHei", 10, "bold"))
        col1.pack(side="left", fill="both", expand=True, padx=(0, 6))

        col2 = tk.LabelFrame(settings, text=" 视口与倍率 ",
                              font=("Microsoft YaHei", 10, "bold"))
        col2.pack(side="right", fill="both", expand=True, padx=(6, 0))

        # ─ 左列 ─

        # 截图模式
        r1 = tk.Frame(col1)
        r1.pack(fill="x", padx=8, pady=(8, 3))
        tk.Label(r1, text="模式：", font=("Microsoft YaHei", 9)).pack(side="left")
        self._mode_var = tk.StringVar(value="fullpage")
        modes = [
            ("整页截图", "fullpage"),
            ("视口截图", "viewport"),
            ("元素截图", "element"),
            ("批量提取", "batch"),
        ]
        for text, val in modes:
            tk.Radiobutton(r1, text=text, variable=self._mode_var, value=val,
                           font=("Microsoft YaHei", 9),
                           command=self._on_mode_change).pack(side="left", padx=2)

        # CSS 选择器（元素/批量模式用）
        self._selector_frame = tk.Frame(col1)
        self._selector_frame.pack(fill="x", padx=8, pady=3)
        tk.Label(self._selector_frame, text="CSS 选择器：",
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self._selector_var = tk.StringVar(value="img, svg")
        tk.Entry(self._selector_frame, textvariable=self._selector_var,
                 font=("Consolas", 10), width=28).pack(side="left", padx=4)
        self._selector_frame.pack_forget()

        # 等待时间
        r3 = tk.Frame(col1)
        r3.pack(fill="x", padx=8, pady=3)
        tk.Label(r3, text="等待渲染：",
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self._wait_var = tk.DoubleVar(value=1.5)
        tk.Spinbox(r3, from_=0.5, to=15, increment=0.5,
                   textvariable=self._wait_var, width=5,
                   font=("Microsoft YaHei", 10)).pack(side="left", padx=4)
        tk.Label(r3, text="秒（JS 复杂可加长）",
                 font=("Microsoft YaHei", 8), fg="#888").pack(side="left")

        # 隐藏滚动条
        r3b = tk.Frame(col1)
        r3b.pack(fill="x", padx=8, pady=(3, 8))
        self._hide_scrollbar_var = tk.BooleanVar(value=True)
        tk.Checkbutton(r3b, text="隐藏滚动条",
                       variable=self._hide_scrollbar_var,
                       font=("Microsoft YaHei", 9)).pack(side="left")
        self._transparent_var = tk.BooleanVar(value=False)
        tk.Checkbutton(r3b, text="透明背景",
                       variable=self._transparent_var,
                       font=("Microsoft YaHei", 9)).pack(side="left", padx=(8, 0))

        # ─ 右列 ─

        # 视口尺寸
        r4 = tk.Frame(col2)
        r4.pack(fill="x", padx=8, pady=(8, 3))
        tk.Label(r4, text="视口宽：",
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self._vw_var = tk.IntVar(value=1920)
        ttk.Combobox(r4, values=["800", "1024", "1280", "1440", "1920", "2560"],
                     textvariable=self._vw_var, width=6).pack(side="left", padx=4)

        tk.Label(r4, text="高：",
                 font=("Microsoft YaHei", 9)).pack(side="left", padx=(8, 0))
        self._vh_var = tk.IntVar(value=1080)
        ttk.Combobox(r4, values=["720", "768", "900", "1080", "1200", "1440"],
                     textvariable=self._vh_var, width=6).pack(side="left", padx=4)

        # 缩放倍率
        r5 = tk.Frame(col2)
        r5.pack(fill="x", padx=8, pady=3)
        tk.Label(r5, text="高清倍率：",
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self._scale_var = tk.IntVar(value=2)
        scales = [("1x", 1), ("2x（推荐）", 2), ("3x", 3), ("4x", 4)]
        for text, val in scales:
            tk.Radiobutton(r5, text=text, variable=self._scale_var, value=val,
                           font=("Microsoft YaHei", 9)).pack(side="left", padx=2)

        # 实际分辨率提示
        r5b = tk.Frame(col2)
        r5b.pack(fill="x", padx=8, pady=(0, 3))
        self._res_label = tk.Label(
            r5b, text="2x 倍率 → 实际输出 3840 x 2160 px",
            font=("Microsoft YaHei", 8), fg="#1a73e8")
        self._res_label.pack(side="left")

        # 绑定更新分辨率提示
        self._vw_var.trace_add("write", self._update_res_label)
        self._vh_var.trace_add("write", self._update_res_label)
        self._scale_var.trace_add("write", self._update_res_label)

        # 预设尺寸快捷
        r6 = tk.Frame(col2)
        r6.pack(fill="x", padx=8, pady=(0, 8))
        tk.Label(r6, text="预设：", font=("Microsoft YaHei", 8),
                 fg="#888").pack(side="left")
        presets = [("1080p", 1920, 1080), ("2K", 2560, 1440),
                   ("iPad", 1024, 768), ("手机", 375, 812)]
        for name, w, h in presets:
            tk.Button(r6, text=name, font=("Microsoft YaHei", 8),
                      command=lambda ww=w, hh=h: self._set_viewport(ww, hh)
                      ).pack(side="left", padx=2)

        # ── 预览区 ──
        preview_outer = tk.Frame(self, bg="#1a1a2e", relief="sunken", bd=1)
        preview_outer.pack(fill="both", expand=True, padx=16, pady=(0, 6))

        self._preview_label = tk.Label(preview_outer, bg="#1a1a2e",
                                       text="选择文件后点「开始截图」查看效果",
                                       font=("Microsoft YaHei", 10), fg="#555")
        self._preview_label.pack(fill="both", expand=True, padx=4, pady=4)

        # ── 底部：按钮 + 状态 ──
        btn_row = tk.Frame(self)
        btn_row.pack(fill="x", padx=16, pady=(0, 4))

        self._capture_btn = tk.Button(
            btn_row, text="开始截图",
            font=("Microsoft YaHei", 13, "bold"),
            command=self._start_capture)
        self._capture_btn.pack(side="left", padx=(0, 10))

        self._progress = ttk.Progressbar(btn_row, mode="indeterminate",
                                         length=200)
        self._progress.pack(side="left", padx=(0, 10))

        self._status_label = tk.Label(btn_row, text="就绪",
                                      font=("Microsoft YaHei", 10), fg="#666")
        self._status_label.pack(side="left")

        # ── 日志 ──
        self._log = scrolledtext.ScrolledText(
            self, font=("Consolas", 9), height=4, state="disabled",
            bg="#fafafa")
        self._log.pack(fill="x", padx=16, pady=(0, 12))

    # ── 界面交互 ──

    def _select_file(self):
        path = filedialog.askopenfilename(
            title="选择 HTML 文件",
            filetypes=[("HTML 文件", "*.html *.htm *.xhtml"),
                       ("所有文件", "*.*")])
        if path:
            # 转为 file:/// URL
            abs_path = os.path.abspath(path).replace("\\", "/")
            self._url_var.set(f"file:///{abs_path}")

    def _on_mode_change(self):
        mode = self._mode_var.get()
        if mode in ("element", "batch"):
            self._selector_frame.pack(fill="x", padx=8, pady=3)
            if mode == "element":
                self._selector_var.set("#main")
            else:
                self._selector_var.set("img, svg")
        else:
            self._selector_frame.pack_forget()

    def _set_viewport(self, w, h):
        self._vw_var.set(w)
        self._vh_var.set(h)

    def _update_res_label(self, *args):
        try:
            w = self._vw_var.get()
            h = self._vh_var.get()
            s = self._scale_var.get()
            self._res_label.configure(
                text=f"{s}x 倍率 → 实际输出 {w * s} x {h * s} px")
        except (tk.TclError, ValueError):
            pass

    def _log_msg(self, msg):
        self._log.configure(state="normal")
        self._log.insert("end", msg + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _set_status(self, text, color="#666"):
        self._status_label.configure(text=text, fg=color)

    # ── 截图核心 ──

    def _start_capture(self):
        url = self._url_var.get().strip()
        if not url:
            messagebox.showwarning("提示", "请先选择 HTML 文件或输入网址")
            return
        if not url.startswith(("http://", "https://", "file:///")):
            # 可能是本地路径
            if os.path.isfile(url):
                abs_path = os.path.abspath(url).replace("\\", "/")
                url = f"file:///{abs_path}"
                self._url_var.set(url)
            else:
                url = "https://" + url
                self._url_var.set(url)

        if self._capturing:
            return
        self._capturing = True
        self._capture_btn.configure(state="disabled")
        self._progress.start(20)
        self._set_status("正在启动浏览器...", "#1a73e8")

        mode = self._mode_var.get()
        thread = threading.Thread(target=self._capture_thread,
                                  args=(url, mode), daemon=True)
        thread.start()

    def _capture_thread(self, url, mode):
        try:
            vw = self._vw_var.get()
            vh = self._vh_var.get()
            scale = self._scale_var.get()
            wait_ms = int(self._wait_var.get() * 1000)
            selector = self._selector_var.get().strip()
            hide_sb = self._hide_scrollbar_var.get()
            transparent = self._transparent_var.get()

            self.after(0, self._log_msg,
                       f"启动浏览器 视口 {vw}x{vh} 倍率 {scale}x")

            with sync_playwright() as p:
                browser = p.chromium.launch()
                context = browser.new_context(
                    viewport={"width": vw, "height": vh},
                    device_scale_factor=scale,
                )
                page = context.new_page()

                self.after(0, self._set_status, "正在加载页面...", "#1a73e8")
                self.after(0, self._log_msg, f"加载: {url}")

                page.goto(url, wait_until="load")

                self.after(0, self._set_status,
                           f"等待 JS 渲染 ({wait_ms}ms)...", "#1a73e8")
                page.wait_for_timeout(wait_ms)

                # 隐藏滚动条
                if hide_sb:
                    page.add_style_tag(
                        content="::-webkit-scrollbar{display:none !important}"
                                "html{scrollbar-width:none !important}")

                if mode == "fullpage":
                    self._capture_fullpage(page, transparent)
                elif mode == "viewport":
                    self._capture_viewport(page, transparent)
                elif mode == "element":
                    self._capture_element(page, selector, transparent)
                elif mode == "batch":
                    self._capture_batch(page, selector, transparent)

                browser.close()

        except Exception as e:
            err = str(e)
            if "Executable doesn't exist" in err:
                self.after(0, messagebox.showerror, "浏览器未安装",
                           "请在命令行运行：\nplaywright install chromium\n\n"
                           "安装完成后重新运行本工具")
            else:
                self.after(0, messagebox.showerror, "截图失败", err)
            self.after(0, self._log_msg, f"错误: {err}")
        finally:
            self.after(0, self._finish_capture)

    def _capture_fullpage(self, page, transparent):
        self.after(0, self._set_status, "正在截取整页...", "#1a73e8")

        save_path = self._ask_save("screenshot_fullpage.png")
        if not save_path:
            return

        omit = transparent and save_path.lower().endswith(".png")
        page.screenshot(path=save_path, full_page=True,
                        omit_background=omit)

        self.after(0, self._log_msg, f"整页截图已保存: {save_path}")
        self.after(0, self._show_preview, save_path)
        self.after(0, self._set_status, "截图完成！", "#2e7d32")

    def _capture_viewport(self, page, transparent):
        self.after(0, self._set_status, "正在截取视口...", "#1a73e8")

        save_path = self._ask_save("screenshot_viewport.png")
        if not save_path:
            return

        omit = transparent and save_path.lower().endswith(".png")
        page.screenshot(path=save_path, full_page=False,
                        omit_background=omit)

        self.after(0, self._log_msg, f"视口截图已保存: {save_path}")
        self.after(0, self._show_preview, save_path)
        self.after(0, self._set_status, "截图完成！", "#2e7d32")

    def _capture_element(self, page, selector, transparent):
        self.after(0, self._set_status,
                   f"正在查找元素: {selector}", "#1a73e8")

        el = page.query_selector(selector)
        if not el:
            self.after(0, messagebox.showwarning, "未找到",
                       f"未找到匹配的元素：{selector}")
            return

        save_path = self._ask_save("element.png")
        if not save_path:
            return

        omit = transparent and save_path.lower().endswith(".png")
        el.screenshot(path=save_path, omit_background=omit)

        self.after(0, self._log_msg, f"元素截图已保存: {save_path}")
        self.after(0, self._show_preview, save_path)
        self.after(0, self._set_status, "截图完成！", "#2e7d32")

    def _capture_batch(self, page, selector, transparent):
        self.after(0, self._set_status,
                   f"正在查找所有: {selector}", "#1a73e8")

        elements = page.query_selector_all(selector)
        if not elements:
            self.after(0, messagebox.showwarning, "未找到",
                       f"未找到匹配的元素：{selector}")
            return

        self.after(0, self._log_msg,
                   f"找到 {len(elements)} 个匹配元素")

        output_dir = self._ask_dir()
        if not output_dir:
            return

        success = 0
        for i, el in enumerate(elements):
            try:
                # 获取元素信息
                tag = el.evaluate("el => el.tagName.toLowerCase()")
                cls = el.evaluate(
                    "el => el.className ? el.className.toString().slice(0,20) : ''")
                src = el.evaluate(
                    "el => el.src || el.getAttribute('href') || ''")

                # 跳过不可见元素
                box = el.bounding_box()
                if not box or box["width"] < 2 or box["height"] < 2:
                    continue

                # 文件名
                if src:
                    base = os.path.splitext(os.path.basename(
                        src.split("?")[0]))[0][:30]
                    name = f"{i + 1}_{base}.png"
                elif cls:
                    name = f"{i + 1}_{tag}_{cls.replace(' ', '_')[:20]}.png"
                else:
                    name = f"{i + 1}_{tag}_{int(box['width'])}x{int(box['height'])}.png"

                save_path = os.path.join(output_dir, name)
                omit = transparent and True
                el.screenshot(path=save_path, omit_background=omit)
                success += 1

                self.after(0, self._log_msg,
                           f"  [{i + 1}/{len(elements)}] {name}  "
                           f"({int(box['width'])}x{int(box['height'])})")

            except Exception as e:
                self.after(0, self._log_msg,
                           f"  [{i + 1}] 跳过: {e}")

        self.after(0, self._log_msg,
                   f"\n批量提取完成: {success}/{len(elements)} 个")
        self.after(0, self._set_status,
                   f"提取完成！{success} 个元素", "#2e7d32")
        self.after(0, lambda: os.startfile(output_dir))

    # ── 文件对话框（从主线程调用）──

    def _ask_save(self, default_name):
        result = [None]
        event = threading.Event()

        def ask():
            path = filedialog.asksaveasfilename(
                title="保存截图",
                initialfile=default_name,
                defaultextension=".png",
                filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
            result[0] = path
            event.set()

        self.after(0, ask)
        event.wait(timeout=120)
        return result[0]

    def _ask_dir(self):
        result = [None]
        event = threading.Event()

        def ask():
            path = filedialog.askdirectory(title="选择元素保存文件夹")
            result[0] = path
            event.set()

        self.after(0, ask)
        event.wait(timeout=120)
        return result[0]

    # ── 预览 ──

    def _show_preview(self, path):
        if not HAS_PIL or not os.path.isfile(path):
            return
        try:
            img = Image.open(path)
            preview_w = WINDOW_WIDTH - 40
            preview_h = 180
            ratio = min(preview_w / img.width, preview_h / img.height, 1.0)
            disp_w = max(int(img.width * ratio), 1)
            disp_h = max(int(img.height * ratio), 1)
            disp = img.resize((disp_w, disp_h), Image.LANCZOS)
            self._preview_photo = ImageTk.PhotoImage(disp)
            self._preview_label.configure(image=self._preview_photo, text="")
        except Exception:
            pass

    def _finish_capture(self):
        self._capturing = False
        self._capture_btn.configure(state="normal")
        self._progress.stop()


if __name__ == "__main__":
    app = WebCaptureApp()
    app.mainloop()
