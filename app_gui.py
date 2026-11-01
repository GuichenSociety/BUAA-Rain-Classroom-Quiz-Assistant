import os
import re
import time
import random
import ctypes
import threading
import unicodedata
from difflib import SequenceMatcher
import tkinter as tk
from tkinter import filedialog, scrolledtext
import pyautogui
import keyboard
from PIL import ImageGrab
from rapidocr_onnxruntime import RapidOCR

# 解决 Windows 125%/150% 缩放导致的截图不全与鼠标点击位置偏移问题
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# ==================== 默认配置 ====================
DEFAULT_BANK_FILE = "QuestionBank/timu.txt"


# =================================================


def normalize_text(text):
    """将康熙部首等异体字转换为标准汉字，并去除标点、空格"""
    if not text:
        return ""
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', text)
    return text.lower()


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


class AutoAnswerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("工程伦理 - OCR自动答题助手 v3.2 (防侧边栏干扰防误判)")
        self.root.geometry("510x560")
        self.root.attributes("-topmost", True)  # 默认窗口置顶

        self.ocr = None
        self.bank = []
        self.is_running_loop = False
        self.bank_file_path = tk.StringVar(value=DEFAULT_BANK_FILE)
        self.topmost_var = tk.BooleanVar(value=True)
        self.fullscreen_var = tk.BooleanVar(value=True)
        self.click_submit_var = tk.BooleanVar(value=True)
        self.click_next_var = tk.BooleanVar(value=False)

        self._build_ui()
        self._init_backend()

        # 注册全局热键
        keyboard.add_hotkey('f8', self.trigger_single)
        keyboard.add_hotkey('f9', self.trigger_loop)
        keyboard.add_hotkey('esc', self.stop_loop)

    def _build_ui(self):
        # 1. 顶部：题库选择区
        frame_top = tk.LabelFrame(self.root, text="题库设置", padx=8, pady=6)
        frame_top.pack(fill="x", padx=10, pady=6)

        tk.Entry(frame_top, textvariable=self.bank_file_path, width=38).pack(side="left", padx=(0, 6))
        tk.Button(frame_top, text="浏览...", command=self.browse_file).pack(side="left", padx=2)
        tk.Button(frame_top, text="重载", command=self.reload_bank).pack(side="left", padx=2)

        # 2. 中部：选项配置区
        frame_opt = tk.Frame(self.root)
        frame_opt.pack(fill="x", padx=12, pady=2)

        tk.Checkbutton(frame_opt, text="窗口置顶", variable=self.topmost_var, command=self.toggle_topmost).pack(
            side="left", padx=(0, 8))
        tk.Checkbutton(frame_opt, text="全屏识别", variable=self.fullscreen_var).pack(side="left", padx=(0, 8))
        tk.Checkbutton(frame_opt, text="自动点[提交]", variable=self.click_submit_var).pack(side="left", padx=(0, 8))
        tk.Checkbutton(frame_opt, text="额外点[下一题]", variable=self.click_next_var).pack(side="left")

        # 3. 核心：控制按钮区
        frame_btn = tk.LabelFrame(self.root, text="答题控制 (支持按钮点击 & 快捷键)", padx=8, pady=8)
        frame_btn.pack(fill="x", padx=10, pady=6)

        self.btn_single = tk.Button(frame_btn, text="🎯 单题解答 (F8)", bg="#e1f5fe", fg="#01579b",
                                    font=("Microsoft YaHei", 10, "bold"), height=2, width=15,
                                    command=self.trigger_single)
        self.btn_single.pack(side="left", expand=True, padx=4)

        self.btn_loop = tk.Button(frame_btn, text="🚀 自动连刷 (F9)", bg="#e8f5e9", fg="#1b5e20",
                                  font=("Microsoft YaHei", 10, "bold"), height=2, width=15, command=self.trigger_loop)
        self.btn_loop.pack(side="left", expand=True, padx=4)

        self.btn_stop = tk.Button(frame_btn, text="🛑 停止 (ESC)", bg="#ffebee", fg="#b71c1c",
                                  font=("Microsoft YaHei", 10, "bold"), height=2, width=12, state="disabled",
                                  command=self.stop_loop)
        self.btn_stop.pack(side="left", expand=True, padx=4)

        # 4. 底部：实时运行日志区
        frame_log = tk.LabelFrame(self.root, text="运行日志", padx=6, pady=6)
        frame_log.pack(fill="both", expand=True, padx=10, pady=(2, 10))

        self.log_area = scrolledtext.ScrolledText(frame_log, wrap=tk.WORD, font=("Consolas", 9), bg="#1e1e1e",
                                                  fg="#d4d4d4")
        self.log_area.pack(fill="both", expand=True)

    def log(self, msg):
        def _append():
            self.log_area.insert(tk.END, msg + "\n")
            self.log_area.see(tk.END)

        self.root.after(0, _append)

    def toggle_topmost(self):
        self.root.attributes("-topmost", self.topmost_var.get())

    def browse_file(self):
        path = filedialog.askopenfilename(title="选择题库 txt 文件",
                                          filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if path:
            self.bank_file_path.set(path)
            self.reload_bank()

    def _init_backend(self):
        def _load():
            self.log("[*] 正在初始化 RapidOCR 引擎，请稍候...")
            self.ocr = RapidOCR()
            self.log("[+] OCR 引擎加载完成！")
            self.reload_bank()

        threading.Thread(target=_load, daemon=True).start()

    def reload_bank(self):
        filepath = self.bank_file_path.get()
        if not os.path.exists(filepath):
            self.log(f"[-] 找不到题库文件: {filepath}，请点击[浏览]选择！")
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = unicodedata.normalize('NFKC', f.read())
        except UnicodeDecodeError:
            with open(filepath, 'r', encoding='gbk', errors='ignore') as f:
                content = unicodedata.normalize('NFKC', f.read())

        blocks = content.split('----------------------------------------')
        questions = []
        current_chapter = "默认章节"

        for block in blocks:
            block = block.strip()
            if not block:
                continue
            raw_lines = [line.strip() for line in block.split('\n') if line.strip()]

            lines = []
            for line in raw_lines:
                if re.match(r'^第\s*\d+\s*讲', line):
                    current_chapter = line
                else:
                    lines.append(line)

            if len(lines) < 2:
                continue

            q_lines = []
            opt_start_idx = 1
            for idx, line in enumerate(lines):
                if re.match(r'^([A-E]|true|false)[\.、\s]*', line, re.IGNORECASE) or line.startswith('参考答案'):
                    opt_start_idx = idx
                    break
                q_lines.append(line)

            raw_q = re.sub(r'^\d+[\.、\s]*', '', " ".join(q_lines))
            options = {}
            ans_list = []

            for line in lines[opt_start_idx:]:
                opt_match = re.match(r'^([A-E]|true|false)[\.、\s]*(.*)$', line, re.IGNORECASE)
                if opt_match and not line.startswith('参考答案'):
                    key = opt_match.group(1).upper()
                    val = opt_match.group(2).strip()
                    options[key] = val
                elif line.startswith('参考答案：') or line.startswith('参考答案:'):
                    ans_str = line.split('：')[-1].split(':')[-1].strip()
                    if '✔' in ans_str or ans_str.upper() == 'TRUE' or ans_str == '正确':
                        ans_list = ['TRUE']
                    elif '❌' in ans_str or ans_str.upper() == 'FALSE' or ans_str == '错误':
                        ans_list = ['FALSE']
                    else:
                        ans_list = [a.strip().upper() for a in ans_str.split(',') if a.strip()]

            if not ans_list:
                continue

            target_texts = []
            for ans in ans_list:
                if ans == 'TRUE':
                    target_texts.append(('正确', 'TRUE'))
                elif ans == 'FALSE':
                    target_texts.append(('错误', 'FALSE'))
                elif ans in options:
                    opt_val = options[ans]
                    if opt_val.startswith('!['):
                        target_texts.append(('', ans))
                    else:
                        target_texts.append((opt_val, ans))

            questions.append({
                'chapter': current_chapter,
                'raw_q': raw_q,
                'norm_q': normalize_text(raw_q),
                'ans_list': ans_list,
                'targets': target_texts
            })

        self.bank = questions
        self.log(f"[+] 成功加载题库: 共 {len(self.bank)} 道题。")

    def _get_capture_bbox(self):
        screen_w, screen_h = pyautogui.size()
        if self.fullscreen_var.get():
            return None, 0, 0
        else:
            left = int(screen_w * 0.25)
            top = int(screen_h * 0.08)
            bbox = (left, top, screen_w, screen_h)
            return bbox, left, top

    def _capture_ocr_items(self):
        self.root.attributes("-alpha", 0.0)
        time.sleep(0.15)
        bbox, offset_x, offset_y = self._get_capture_bbox()
        img = ImageGrab.grab(bbox=bbox)
        self.root.attributes("-alpha", 1.0)

        result, _ = self.ocr(img)
        if not result:
            return [], "", img, (offset_x, offset_y)

        ocr_items = []
        full_screen_norm = ""
        for box, text, score in result:
            norm_t = normalize_text(text)
            left_x = int(box[0][0]) + offset_x
            bottom_y = int(box[2][1]) + offset_y
            center_x = int((box[0][0] + box[2][0]) / 2) + offset_x
            center_y = int((box[0][1] + box[2][1]) / 2) + offset_y
            ocr_items.append({
                'raw': text.strip(),
                'norm': norm_t,
                'center': (center_x, center_y),
                'left_bottom': (left_x, bottom_y)
            })
            full_screen_norm += norm_t
        return ocr_items, full_screen_norm, img, (offset_x, offset_y)

    def _find_true_false_circles(self, ocr_items, q_left_bottom, q_top_y):
        """查找判断题圆圈，加入 X/Y 严格边界过滤"""
        true_pos, false_pos = None, None
        bx, by = q_left_bottom

        # 1. 尝试在题干下方寻找勾/叉/圆圈
        for item in ocr_items:
            # ★ 关键修复：必须满足以下条件：
            # Y轴：在题干上方边界之下，且不能超出题干底部太远（超150像素）
            # X轴：必须在题干文字的最左侧（bx）右侧，以此过滤掉左侧题号栏的绿勾
            if item['center'][1] < q_top_y or item['center'][1] > by + 150:
                continue
            if item['center'][0] < bx - 20:
                continue

            raw = item['raw'].strip().lower()
            if len(raw) <= 3:
                if any(c in raw for c in ['√', 'v', '✓', '对', 'y']):
                    true_pos = item['center']
                elif any(c in raw for c in ['×', 'x', '✗', '错', 'n']):
                    false_pos = item['center']

        if true_pos and false_pos:
            if true_pos[0] > false_pos[0]:
                true_pos, false_pos = false_pos, true_pos
            return true_pos, false_pos, "OCR精准图案"
        elif true_pos:
            return true_pos, (true_pos[0] + 54, true_pos[1]), "OCR勾+横向推算"
        elif false_pos:
            return (false_pos[0] - 54, false_pos[1]), false_pos, "OCR叉+横向推算"

        # 2. 兜底推算（针对空心图标没被OCR识别的情况）
        # 使用精准的像素级推算
        true_pos = (bx + 18, by + 55)
        false_pos = (bx + 72, by + 55)
        return true_pos, false_pos, "边界兜底推算"

    def _click_submit(self):
        if not self.click_submit_var.get() and not self.click_next_var.get():
            self.log("  [*] 已完成选项勾选（未开启自动提交）。")
            return

        time.sleep(0.4)
        self.log("  [*] 正在定位底部 [提交] 按钮...")
        ocr_items, _, _, _ = self._capture_ocr_items()

        submit_pos = None
        prev_pos = None
        next_pos = None

        for item in ocr_items:
            raw = item['raw'].replace(" ", "")
            if "提交" in raw or "提" == raw:
                submit_pos = item['center']
            elif "上一题" in raw or "上一" in raw:
                prev_pos = item['center']
            elif "下一题" in raw or "下一" in raw:
                next_pos = item['center']

        if self.click_submit_var.get():
            if not submit_pos and prev_pos and next_pos:
                submit_pos = (int((prev_pos[0] + next_pos[0]) / 2), int((prev_pos[1] + next_pos[1]) / 2))
                self.log(f"  [*] 通过[上一题/下一题]中点推算出 [提交] 坐标: {submit_pos}")
            elif not submit_pos and next_pos:
                submit_pos = (next_pos[0] - 240, next_pos[1])
                self.log(f"  [*] 通过[下一题]左侧偏移推算出 [提交] 坐标: {submit_pos}")

            if submit_pos:
                self.log(f"  -> 点击 [提交] @({submit_pos[0]}, {submit_pos[1]})，等待自动跳转下一题...")
                pyautogui.click(submit_pos[0], submit_pos[1])
            else:
                self.log("  [!] 警告：未能找到 [提交] 按钮坐标！")

        if self.click_next_var.get() and next_pos:
            time.sleep(0.8)
            self.log(f"  -> 额外点击 [下一题] @({next_pos[0]}, {next_pos[1]})")
            pyautogui.click(next_pos[0], next_pos[1])

    def solve_once(self):
        if not self.ocr or not self.bank:
            self.log("[!] OCR 尚未就绪或题库为空！")
            return

        self.log("\n[*] 正在截屏并执行 OCR 识别题目...")
        ocr_items, full_screen_norm, pil_img, offset = self._capture_ocr_items()
        if not ocr_items:
            self.log("[-] 未识别到任何屏幕文字！")
            return

        best_match = None
        best_score = 0

        # 1. 匹配题库
        for item in self.bank:
            q_norm = item['norm_q']
            if not q_norm:
                continue
            if q_norm in full_screen_norm:
                best_match = item
                best_score = 1.0
                break

            for i, ocr_item in enumerate(ocr_items):
                if len(ocr_item['norm']) < 4:
                    continue
                combined_norm = "".join([x['norm'] for x in ocr_items[i:i + 3]])
                score = max(similarity(q_norm, ocr_item['norm']), similarity(q_norm, combined_norm))
                if score > best_score:
                    best_score = score
                    best_match = item

        if not best_match or best_score < 0.45:
            self.log(f"[-] 未匹配到题目 (最高相似度: {best_score:.2f})")
            return

        # 2. 精确定位题干边界
        q_norm = best_match['norm_q']
        best_line = None
        best_line_sim = 0
        for item in ocr_items:
            if len(item['norm']) >= 4:
                sim = similarity(q_norm, item['norm'])
                if sim > best_line_sim:
                    best_line_sim = sim
                    best_line = item

        if best_line:
            q_left_x = best_line['left_bottom'][0]
            q_bottom_y = best_line['left_bottom'][1]

            for item in ocr_items:
                if item['left_bottom'][1] > q_bottom_y and item['left_bottom'][1] - q_bottom_y < 100:
                    if abs(item['left_bottom'][0] - q_left_x) < 80:
                        q_bottom_y = item['left_bottom'][1]

            q_top_y = q_bottom_y - 60
            q_left_bottom = (q_left_x, q_bottom_y)
        else:
            q_left_bottom = (474, 302)
            q_top_y = 0

        self.log(f"[+] 章节: {best_match['chapter']}")
        self.log(f"[+] 题目: {best_match['raw_q'][:28]}... ({best_score:.2f})")
        self.log(f"[+] 答案: {best_match['ans_list']}")

        is_tf = any(ans in ('TRUE', 'FALSE') for ans in best_match['ans_list'])

        # 3. 执行点击
        for target_text, ans_key in best_match['targets']:
            norm_target = normalize_text(target_text)
            clicked = False
            delay_sec = random.uniform(0.3, 0.8)

            # 判断题
            if ans_key in ('TRUE', 'FALSE'):
                true_pos, false_pos, method = self._find_true_false_circles(ocr_items, q_left_bottom, q_top_y)
                target_pos = true_pos if ans_key == 'TRUE' else false_pos
                label = "左圆[勾 ✓]" if ans_key == 'TRUE' else "右圆[叉 ×]"
                self.log(f"  -> ({method}) 点击 {label} @({target_pos[0]},{target_pos[1]})")
                pyautogui.click(target_pos[0], target_pos[1])
                time.sleep(delay_sec)
                clicked = True

            # 单选/多选题
            if not clicked and not is_tf:
                found_pos = None
                ocr_items.sort(key=lambda item: item['center'][1])

                # 策略 A：精准寻找独立的字母图标
                for ocr_item in ocr_items:
                    # ★ 关键修复：X 轴必须大于题干最左侧坐标，防止识别到左侧题号栏里的数字或字母
                    if ocr_item['center'][1] < q_top_y or ocr_item['center'][0] < q_left_x - 20:
                        continue
                    raw_text = ocr_item['raw'].strip().upper()
                    if len(raw_text) <= 3:
                        clean_letter = re.sub(r'[^A-E]', '', raw_text)
                        if clean_letter == ans_key:
                            found_pos = (ocr_item['center'][0], ocr_item['center'][1], f"精准字母")
                            break

                # 策略 B：文字严格匹配
                if not found_pos and norm_target:
                    for ocr_item in ocr_items:
                        # ★ 关键修复：同样限制 X 轴
                        if not ocr_item['norm'] or ocr_item['center'][1] < q_top_y or ocr_item['center'][
                            0] < q_left_x - 20:
                            continue
                        is_exact_match = (norm_target == ocr_item['norm'])
                        is_long_contain = (len(norm_target) > 5 and norm_target in ocr_item['norm'])

                        if is_exact_match or is_long_contain:
                            target_x = ocr_item['center'][0] - 45
                            target_y = ocr_item['center'][1]
                            found_pos = (target_x, target_y, f"文字匹配")
                            break

                if found_pos:
                    tx, ty, method = found_pos
                    self.log(f"  -> {method} 定位 [{ans_key}] @({tx},{ty}) [间隔{delay_sec:.2f}s]")
                    pyautogui.click(tx, ty)
                    time.sleep(delay_sec)
                    clicked = True

            if not clicked:
                self.log(f"  [!] 未找到选项 [{ans_key}] 的位置，请手动选择！")

        self._click_submit()

    def trigger_single(self):
        if self.is_running_loop:
            return
        threading.Thread(target=self.solve_once, daemon=True).start()

    def trigger_loop(self):
        if self.is_running_loop:
            return
        self.is_running_loop = True
        self.btn_single.config(state="disabled")
        self.btn_loop.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.log("\n[🚀] 开启连续自动答题模式 (点[停止]或按 ESC 中断)...")

        def _loop_worker():
            while self.is_running_loop:
                self.solve_once()
                for _ in range(random.randint(16, 24)):
                    if not self.is_running_loop:
                        break
                    time.sleep(0.1)
            self.log("[🛑] 已停止连续答题。")
            self.root.after(0, self._reset_buttons)

        threading.Thread(target=_loop_worker, daemon=True).start()

    def stop_loop(self):
        if self.is_running_loop:
            self.is_running_loop = False

    def _reset_buttons(self):
        self.btn_single.config(state="normal")
        self.btn_loop.config(state="normal")
        self.btn_stop.config(state="disabled")


if __name__ == '__main__':
    root = tk.Tk()
    app = AutoAnswerApp(root)
    root.mainloop()
