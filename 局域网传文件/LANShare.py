"""
局域网传文件工具 1.0 —— GUI 图形窗口版
在电脑上开一个临时网页服务器，同局域网的手机/电脑用浏览器即可上传下载文件
无需第三方依赖，Python 自带库即可运行
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import socket
import threading
import http.server
import urllib.parse
import html
import io
import cgi
import webbrowser

WINDOW_WIDTH = 650
WINDOW_HEIGHT = 480
DEFAULT_PORT = 8000


def get_local_ip():
    """获取本机局域网 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class FileHandler(http.server.BaseHTTPRequestHandler):
    """处理文件上传和下载的 HTTP 请求"""

    def log_message(self, format, *args):
        # 静默日志，不在终端输出
        pass

    def do_GET(self):
        if self.path == "/" or self.path == "":
            self._serve_page()
        else:
            self._serve_file()

    def do_POST(self):
        """处理文件上传"""
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self.send_error(400)
            return

        # 解析 multipart
        boundary = content_type.split("boundary=")[-1].encode()
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        # 简单解析 multipart
        parts = body.split(b"--" + boundary)
        saved = []
        for part in parts:
            if b"filename=\"" not in part:
                continue
            # 提取文件名
            header_end = part.find(b"\r\n\r\n")
            if header_end < 0:
                continue
            header_str = part[:header_end].decode("utf-8", errors="replace")
            file_data = part[header_end + 4:]
            # 去掉尾部的 \r\n
            if file_data.endswith(b"\r\n"):
                file_data = file_data[:-2]

            # 从 header 中提取 filename
            fn_start = header_str.find('filename="') + len('filename="')
            fn_end = header_str.find('"', fn_start)
            filename = header_str[fn_start:fn_end]

            if not filename:
                continue

            # 安全文件名
            filename = os.path.basename(filename)
            save_path = os.path.join(self.server.share_dir, filename)

            # 防覆盖
            if os.path.exists(save_path):
                stem, ext = os.path.splitext(filename)
                i = 1
                while os.path.exists(save_path):
                    save_path = os.path.join(self.server.share_dir, f"{stem}_{i}{ext}")
                    i += 1

            with open(save_path, "wb") as f:
                f.write(file_data)
            saved.append(os.path.basename(save_path))

            # 通知 GUI
            if hasattr(self.server, "on_upload") and self.server.on_upload:
                self.server.on_upload(os.path.basename(save_path))

        # 重定向回首页
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def _serve_page(self):
        """生成首页 HTML"""
        share_dir = self.server.share_dir
        files = []
        for f in sorted(os.listdir(share_dir)):
            full = os.path.join(share_dir, f)
            if os.path.isfile(full):
                size = os.path.getsize(full)
                if size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                files.append((f, size_str))

        file_rows = ""
        if files:
            for name, size in files:
                encoded = urllib.parse.quote(name)
                escaped = html.escape(name)
                file_rows += f'<tr><td><a href="/{encoded}" download>{escaped}</a></td><td>{size}</td></tr>\n'
        else:
            file_rows = '<tr><td colspan="2" style="color:#999">文件夹为空</td></tr>'

        page = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>局域网文件共享</title>
<style>
body {{ font-family: -apple-system, "Microsoft YaHei", sans-serif; max-width: 700px; margin: 40px auto; padding: 0 20px; background: #f5f5f5; }}
h1 {{ color: #333; }} h2 {{ color: #555; margin-top: 30px; }}
table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #eee; }}
th {{ background: #fafafa; font-weight: 600; }}
a {{ color: #1a73e8; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.upload-box {{ background: white; padding: 20px; border-radius: 8px; margin-top: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
input[type=file] {{ margin: 10px 0; }}
button {{ background: #1a73e8; color: white; border: none; padding: 10px 24px; border-radius: 6px; font-size: 15px; cursor: pointer; }}
button:hover {{ background: #1557b0; }}
</style></head><body>
<h1>局域网文件共享</h1>

<h2>上传文件</h2>
<div class="upload-box">
<form method="POST" enctype="multipart/form-data">
<input type="file" name="file" multiple><br>
<button type="submit">上传</button>
</form></div>

<h2>文件列表（点击下载）</h2>
<table><tr><th>文件名</th><th>大小</th></tr>
{file_rows}
</table>

</body></html>"""

        data = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def _serve_file(self):
        """提供文件下载"""
        path = urllib.parse.unquote(self.path.lstrip("/"))
        full = os.path.join(self.server.share_dir, path)

        if not os.path.isfile(full) or ".." in path:
            self.send_error(404)
            return

        size = os.path.getsize(full)
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Disposition", f'attachment; filename="{urllib.parse.quote(os.path.basename(full))}"')
        self.send_header("Content-Length", size)
        self.end_headers()

        with open(full, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)


# ── GUI ─────────────────────────────────────────────

class LANShareApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("局域网传文件工具 1.0")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)
        self._server = None
        self._show_start()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    def _on_close(self):
        if self._server:
            self._server.shutdown()
        self.destroy()

    # ── 开始页 ───────────────────────────────────────

    def _show_start(self):
        self._clear()
        f = tk.Frame(self.container); f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="局域网传文件工具", font=("Microsoft YaHei", 24, "bold")).pack(pady=(0, 6))
        tk.Label(f, text="在电脑上开个临时网页，同一 WiFi 下的手机/电脑用浏览器就能传文件",
                 font=("Microsoft YaHei", 10), fg="#666", wraplength=500).pack(pady=(0, 30))

        tk.Button(f, text="选择共享文件夹", font=("Microsoft YaHei", 13),
                  width=20, height=2, command=self._on_select).pack(pady=6)

        tk.Label(f, text="选择一个文件夹作为共享目录，里面的文件可被下载\n别人上传的文件也会保存到这个文件夹里",
                 font=("Microsoft YaHei", 9), fg="#999", justify="center").pack(pady=(10, 0))

    def _on_select(self):
        folder = filedialog.askdirectory(title="选择共享文件夹")
        if not folder:
            return
        self._folder = folder
        self._start_server()

    # ── 服务运行中页面 ───────────────────────────────

    def _start_server(self):
        ip = get_local_ip()
        port = DEFAULT_PORT

        # 尝试端口
        for attempt in range(10):
            try:
                server = http.server.HTTPServer((ip, port), FileHandler)
                break
            except OSError:
                port += 1
        else:
            messagebox.showerror("错误", "无法找到可用端口。")
            return

        server.share_dir = self._folder
        server.on_upload = self._on_file_uploaded
        self._server = server
        self._url = f"http://{ip}:{port}"

        # 后台运行服务器
        threading.Thread(target=server.serve_forever, daemon=True).start()

        self._show_running(ip, port)

    def _show_running(self, ip, port):
        self._clear()

        f = tk.Frame(self.container)
        f.pack(expand=True, fill="both", padx=30, pady=20)

        tk.Label(f, text="服务已启动", font=("Microsoft YaHei", 20, "bold"), fg="#2e7d32").pack(pady=(10, 15))

        # URL 显示
        url_frame = tk.Frame(f, bg="#e8f5e9", relief="groove", bd=1)
        url_frame.pack(fill="x", pady=(0, 10))
        tk.Label(url_frame, text="在手机或其他电脑的浏览器中打开：",
                 font=("Microsoft YaHei", 10), bg="#e8f5e9").pack(pady=(10, 2))
        tk.Label(url_frame, text=self._url,
                 font=("Consolas", 20, "bold"), fg="#1a73e8", bg="#e8f5e9").pack(pady=(2, 10))

        tk.Label(f, text="确保手机和电脑连的是同一个 WiFi",
                 font=("Microsoft YaHei", 10), fg="#e65100").pack(pady=(0, 12))

        # 操作按钮
        btn_row = tk.Frame(f)
        btn_row.pack(pady=(0, 12))
        tk.Button(btn_row, text="用浏览器打开", font=("Microsoft YaHei", 10),
                  command=lambda: webbrowser.open(self._url)).pack(side="left", padx=6)
        tk.Button(btn_row, text="打开共享文件夹", font=("Microsoft YaHei", 10),
                  command=lambda: os.startfile(self._folder)).pack(side="left", padx=6)

        # 共享目录
        tk.Label(f, text=f"共享目录：{self._folder}",
                 font=("Microsoft YaHei", 9), fg="#888").pack(anchor="w")

        # 日志
        tk.Label(f, text="传输记录：", font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", pady=(12, 3))
        self._log_text = tk.Text(f, height=8, font=("Microsoft YaHei", 9), state="disabled", bg="#fafafa")
        self._log_text.pack(fill="both", expand=True)

        self._add_log("服务已启动，等待连接...")

        # 停止按钮
        tk.Button(f, text="停止服务并返回", font=("Microsoft YaHei", 11),
                  command=self._stop_server, fg="#c62828").pack(pady=(10, 0))

    def _add_log(self, msg):
        self._log_text.config(state="normal")
        self._log_text.insert("end", f"  {msg}\n")
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    def _on_file_uploaded(self, filename):
        self.after(0, lambda: self._add_log(f"收到文件：{filename}"))

    def _stop_server(self):
        if self._server:
            threading.Thread(target=self._server.shutdown, daemon=True).start()
            self._server = None
        self._show_start()


if __name__ == "__main__":
    app = LANShareApp()
    app.mainloop()
