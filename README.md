<h1 align="center">🧰 CodeLab 工具箱</h1>

<p align="center">
  <strong>28 个实用 Python GUI 小工具，覆盖图片 / 音视频 / 文档 / 日常场景</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/GUI-Tkinter-blue" />
  <img src="https://img.shields.io/badge/平台-Windows-0078D6?logo=windows&logoColor=white" />
  <img src="https://img.shields.io/badge/工具数量-28-brightgreen" />
  <img src="https://img.shields.io/github/license/XKY4679/CodeLab" />
</p>

<p align="center">
  全部基于 Python + Tkinter 开发，双击即可运行<br/>
  统一启动器一键管理所有工具
</p>

---

## 📦 快速开始

```bash
# 克隆仓库
git clone https://github.com/XKY4679/CodeLab.git

# 安装常用依赖（按需）
pip install Pillow PyPDF2 PyMuPDF pygments mutagen pydub qrcode fpdf2 pdfplumber

# 启动工具箱
python CodeLab業的工具箱.py
```

---

## 🗂️ 工具一览

### 🖼️ 图片工具（8 个）

| 工具 | 说明 | 核心依赖 |
|------|------|----------|
| **批量图片压缩** | 批量压缩 JPG/PNG，可调质量 | Pillow |
| **图片格式转换** | PNG ↔ JPG ↔ WebP ↔ BMP 互转 | Pillow |
| **批量加水印** | 文字/图片水印，可调透明度和位置 | Pillow |
| **GIF 制作工具** | 多张图合成 GIF，可调帧率 | Pillow |
| **色卡提取器** | 从图片中提取主要颜色 | Pillow |
| **波普效果生成器** | 安迪·沃霍尔风格波普艺术 | Pillow |
| **图片拼接工具** | 横向/纵向/网格拼接多张图片 | Pillow |
| **App 图标生成器** | 一键生成 iOS/Android 全套尺寸图标 | Pillow |

### 🎬 音视频工具（3 个）

| 工具 | 说明 | 核心依赖 |
|------|------|----------|
| **批量压缩视频** | FFmpeg 批量压缩，可调码率/分辨率 | ffmpeg |
| **Mp3 歌词嵌入** | 将 LRC 歌词嵌入 MP3 文件 | mutagen |
| **音频波形图** | 生成音频可视化波形图片 | pydub / Pillow |

### 📄 文档工具（4 个）

| 工具 | 说明 | 核心依赖 |
|------|------|----------|
| **PDF 合并拆分** | 多个 PDF 合并 / 按页拆分 | PyPDF2 |
| **PDF 压缩工具** | 智能压缩 PDF 内嵌图片，四档质量 | PyMuPDF / Pillow |
| **刷题程序 3.0** | Excel 题库导入，随机刷题 | pandas / openpyxl |
| **MD 与 PDF 互转** | Markdown ↔ PDF 双向转换 | fpdf2 / pdfplumber |

### 🔧 实用工具（13 个）

| 工具 | 说明 | 核心依赖 |
|------|------|----------|
| **批量重命名** | 正则/序号/替换，多种重命名规则 | — |
| **局域网传文件** | 同一 WiFi 下手机电脑互传文件 | — |
| **字体预览工具** | 预览系统已安装字体的显示效果 | — |
| **二维码生成器** | 生成带 Logo 的彩色二维码 | qrcode / Pillow |
| **调色板生成器** | 生成配色方案并导出色值 | Pillow |
| **文本去重工具** | 多种去重模式，保留顺序 | — |
| **HTML 图片提取器** | 从 HTML 源码中批量提取图片 | — |
| **网页截图工具** | 用浏览器引擎截取动态网页 | Playwright |
| **屏幕取色器** | 实时取色 + 放大镜 + 颜色历史 | Pillow |
| **代码截图美化** | 代码渲染为精美图片（类似 Carbon） | Pillow / Pygments |
| **ASCII 艺术生成器** | 图片转字符画 / 文字转大字 | Pillow |

---

## 🖥️ 统一启动器

运行 `CodeLab業的工具箱.py` 即可打开启动器，**分类展示所有工具，点击即可启动**，无需记路径。

---

## 💡 特点

- ✅ **纯 Python 实现**，跨平台友好
- ✅ **GUI 图形界面**，无需命令行操作
- ✅ **统一启动器**，一键管理 28 个工具
- ✅ **每个工具附带使用教程**
- ✅ **按需安装依赖**，核心工具零依赖

---

## 📋 环境要求

- Python 3.10+
- Windows 10/11（部分工具使用了 Windows 特性）
- 各工具的依赖见上表，按需安装即可

---

## 📁 目录结构

```
CodeLab/
├── CodeLab業的工具箱.py        ← 统一启动器
├── 批量图片压缩/
│   ├── ImageCompress.py
│   └── 使用教程.txt
├── 图片格式转换/
│   ├── FormatConverter.py
│   └── 使用教程.txt
├── PDF压缩工具/
│   ├── PDFCompressor.py
│   └── 使用教程.txt
├── 屏幕取色器/
│   ├── ColorPicker.py
│   └── 使用教程.txt
├── 代码截图美化/
│   ├── CodeScreenshot.py
│   └── 使用教程.txt
├── ...                         ← 其他工具（结构相同）
└── .gitignore
```

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/XKY4679">XKY4679</a>
</p>
