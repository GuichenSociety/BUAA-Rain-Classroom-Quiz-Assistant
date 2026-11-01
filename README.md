# 🎓 工程伦理自动答题助手 (Engineering Ethics Auto-Answer Tool)

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/)

一个基于 **Python + RapidOCR + Tkinter** 开发的轻量级桌面端自动化答题辅助工具。专为各类在线课程平台的客观题、多选题及判断题设计，支持图形化界面控制、题库模糊匹配、随机间隔防监控模拟以及单题/连刷双模式。

---

## ✨ 核心功能

* **🖼️ 桌面端 GUI 软件**：提供直观轻量的可视化操作面板，支持窗口置顶、全屏识别、自定义题库路径。
* **🔍 智能 OCR 识别**：采用离线 `RapidOCR` 引擎，无需配置繁琐的 Tesseract 环境，pip 安装即用，毫秒级响应。
* **🧠 多维度题库模糊匹配**：完美兼容异体字（如康熙部首“⼈”、“⽂”等自动标准化），支持长题干换行模糊搜索。
* **🛡️ 防风控拟人化设计**：
  * 多选题选项之间支持**毫秒级随机停顿间隔**，规避固定时间机器特征。
  * 完美保留原版精准点击逻辑，确保 100% 命中选项且不与人手操作抢鼠标。
* **✔️ 判断题精准识别**：针对无文字的圆圈图标（`✓` 勾 / `×` 叉）采用 OpenCV 轮廓识别 + 题干像素定位双保险。
* **🚀 灵活的提交流程**：支持用户自主选择是否“自动点击提交”及“自动点下一题”。

---

## 📂 项目结构

```text
ProjectRoot/
├── QuestionBank/
│   └── timu.txt          # 题库文件（支持多章节合并，按格式存放）
├── app_gui.py            # 桌面端 GUI 主程序
├── requirements.txt      # 依赖包列表
└── README.md             # 项目说明文档
```

---

## 🛠️ 安装与配置

### 1. 克隆项目到本地
```bash
git clone https://github.com/你的用户名/你的仓库名.git
cd 你的仓库名
```

### 2. 安装依赖项
建议使用 Python 3.8 ~ 3.12 环境，通过清华镜像源快速安装依赖：
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

`requirements.txt` 文件内容参考：
```text
# 安装命令: pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
-i https://pypi.tuna.tsinghua.edu.cn/simple

rapidocr_onnxruntime>=1.3.0
onnxruntime>=1.15.0
pyautogui>=0.9.54
Pillow>=10.0.0
keyboard>=0.13.5
opencv-python>=4.8.0
numpy<2.0.0
```

---

## 🚀 使用指南

1. **准备题库**：将你的题库文件放置在 `QuestionBank/timu.txt` 目录下（确保格式包含题干、选项及 `参考答案：`）。
2. **启动软件**：
   ```bash
   python app_gui.py
   ```
   *(提示：如果不想看到黑色的命令行窗口，可将脚本后缀改为 `.pyw` 后直接双击运行)*
3. **操作说明**：
   - 切换到浏览器的答题页面，保持题目完整显示在屏幕上。
   - 点击软件上的 **[🎯 单题解答 (F8)]** 或按快捷键 `F8` 测试单题。
   - 确认无误后点击 **[🚀 自动连刷 (F9)]** 开始自动答题循环。
   - 运行过程中随时可按 `ESC` 键或点击 **[🛑 停止]** 中断。

---

## 📝 题库文件格式示例

题库采用标准的纯文本格式，各题目之间通过 `----------------------------------------` 分割：

```text
第01讲 工程伦理概论
1. 把工程看成是科学技术的应用是一种对工程的认识,以下哪一种对工程的说法,与这种认识不同( )
   A. 工程是指将科学知识系统运用于结构和机器的设计、制造和使用中
   B. 工程是将自然科学的原理应用到工农业生产部⻔中去而形成的各学科的总称。
   C. 工程是一种实践性研究...
   D. 工程是指将科学知识应用于工农业生产过程而形成的各学科的总称...
参考答案：C
----------------------------------------
```

---

## ⚠️ 免责声明

本仓库提供的所有内容仅供 **Python 编程学习、OCR 图像识别技术交流与个人效率研究** 使用。请勿将本工具用于任何违反学校规定、考试纪律或商业平台的违规操作。使用者因使用本工具产生的一切后果由使用者本人承担。

---

## 📄 License

本项目采用 [MIT License](LICENSE) 开源许可证进行许可。