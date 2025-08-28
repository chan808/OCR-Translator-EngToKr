import sys
import os
import re
import time
import tkinter as tk
import ctypes
import json

# --- 라이브러리 임포트 ---
try:
    app_data_path = os.getenv('APPDATA')
    if app_data_path:
        site_packages_path = os.path.join(app_data_path, 'Python', 'Python39', 'site-packages')
        if os.path.exists(site_packages_path) and site_packages_path not in sys.path:
            sys.path.insert(0, site_packages_path)

    import pyautogui
    import pyperclip
    import keyboard
    import google.generativeai as genai
    from PIL import Image
    import pytesseract
except ImportError as e:
    print(f"오류: 필수 라이브러리를 찾을 수 없습니다. ({e})")
    print("먼저 다음 명령어를 실행하여 라이브러리를 설치해주세요:")
    print("python -m pip install pyautogui pyperclip keyboard pillow pytesseract google-generativeai")
    sys.exit(1)

# --- 전역 설정 ---
TESSERACT_PATH = r'C:\Users\freetime\Desktop\Tesseract-OCR\tesseract.exe'

# --- 화면 영역 선택 함수 ---
def get_selection_area():
    """
    마우스 드래그로 화면 영역을 선택하는 GUI를 띄우고,
    선택된 영역의 좌표 (x, y, width, height)를 반환합니다.
    """
    root = tk.Tk()
    root.attributes('-alpha', 0.3)
    root.attributes('-topmost', True)
    root.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0")
    root.overrideredirect(True)

    start_x, start_y, end_x, end_y = 0, 0, 0, 0
    rect_id = None
    
    canvas = tk.Canvas(root, cursor="cross", bg='black')
    canvas.pack(fill=tk.BOTH, expand=True)

    def on_mouse_down(event):
        nonlocal start_x, start_y, rect_id
        start_x, start_y = event.x, event.y
        if rect_id:
            canvas.delete(rect_id)
        rect_id = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='red', width=2)

    def on_mouse_move(event):
        if rect_id:
            canvas.coords(rect_id, start_x, start_y, event.x, event.y)

    def on_mouse_up(event):
        nonlocal end_x, end_y
        end_x, end_y = event.x, event.y
        root.quit()

    canvas.bind("<ButtonPress-1>", on_mouse_down)
    canvas.bind("<B1-Motion>", on_mouse_move)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)

    root.mainloop()
    root.destroy()

    x1 = min(start_x, end_x)
    y1 = min(start_y, end_y)
    width = abs(end_x - start_x)
    height = abs(end_y - start_y)

    if width > 0 and height > 0:
        return (x1, y1, width, height)
    else:
        return None

# --- 메인 애플리케이션 클래스 ---
class OCRTranslatorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.subtitle_window = None
        
        self.subtitle_region_x = 500
        self.subtitle_region_y = 360
        self.subtitle_region_w = 1000
        self.subtitle_region_h = 200

        self.config = self.load_config()
        self.setup_api_and_tesseract()
        
        print("마우스로 번역할 영역을 드래그하여 지정하세요...")
        self.region = get_selection_area()
        if not self.region:
            print("오류: 유효한 영역이 선택되지 않았습니다. 프로그램을 종료합니다.")
            sys.exit(1)
        print(f"✅ 영역 지정 완료: {self.region}")

    def load_config(self):
        defaults = {
            "gemini_api_key": "YOUR_API_KEY_HERE",
            "translation_duration_seconds": 5,
            "show_translation_hotkey": "`"
        }
        
        # 스크립트의 실제 위치를 기준으로 config.json 경로 설정
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, "config.json")

            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                defaults["gemini_api_key"] = config.get("gemini_api_key", defaults["gemini_api_key"])
                defaults["translation_duration_seconds"] = config.get("translation_duration_seconds", defaults["translation_duration_seconds"])
                defaults["show_translation_hotkey"] = config.get("show_translation_hotkey", defaults["show_translation_hotkey"])
                print("✅ 설정 파일(config.json)을 성공적으로 불러왔습니다.")
        except FileNotFoundError:
            print(f"⚠️ 설정 파일({config_path})을 찾을 수 없습니다. 기본값으로 실행합니다.")
        except json.JSONDecodeError:
            print("⚠️ 설정 파일(config.json)의 형식이 잘못되었습니다. 기본값으로 실행합니다.")
        return defaults

    def setup_api_and_tesseract(self):
        try:
            genai.configure(api_key=self.config['gemini_api_key'])
        except Exception as e:
            print(f"Gemini API 설정 오류: {e}")
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

    def create_subtitle_window(self, text):
        if self.subtitle_window and self.subtitle_window.winfo_exists():
            self.subtitle_window.destroy()
        self.subtitle_window = w = tk.Toplevel(self.root)
        w.overrideredirect(True)
        w.attributes("-alpha", 0.5)
        w.attributes("-topmost", True)
        w.config(bg='black')
        
        w._resize_grip_size = 8

        def on_press_subtitle(event):
            x, y, win_w, win_h = event.x, event.y, w.winfo_width(), w.winfo_height()
            is_in_move_area = (
                x > w._resize_grip_size and x < win_w - w._resize_grip_size and
                y > w._resize_grip_size and y < win_h - w._resize_grip_size
            )
            if is_in_move_area:
                w._current_action = "move"
            else:
                w._current_action = "resize"
                w._resize_edge = ""
                if y < w._resize_grip_size: w._resize_edge += "n"
                if y > win_h - w._resize_grip_size: w._resize_edge += "s"
                if x < w._resize_grip_size: w._resize_edge += "w"
                if x > win_w - w._resize_grip_size: w._resize_edge += "e"
            w._start_x, w._start_y = event.x_root, event.y_root
            w._start_w, w._start_h = win_w, win_h
            w._initial_x, w._initial_y = w.winfo_x(), w.winfo_y()

        def on_motion_subtitle(event):
            x, y, win_w, win_h = event.x, event.y, w.winfo_width(), w.winfo_height()
            cursor = ""
            if (x > w._resize_grip_size and x < win_w - w._resize_grip_size and
                y > w._resize_grip_size and y < win_h - w._resize_grip_size):
                cursor = "fleur"
            else:
                if y < w._resize_grip_size: cursor += "n"
                elif y > win_h - w._resize_grip_size: cursor += "s"
                if x < w._resize_grip_size: cursor += "w"
                elif x > win_w - w._resize_grip_size: cursor += "e"
            cursor_map = {"n": "sb_v_double_arrow", "s": "sb_v_double_arrow", "e": "sb_h_double_arrow", "w": "sb_h_double_arrow",
                          "ne": "size_ne_sw", "sw": "size_ne_sw", "nw": "size_nw_se", "se": "size_nw_se"}
            w.config(cursor=cursor_map.get(cursor, "fleur"))

        def on_drag_subtitle(event):
            if not hasattr(w, '_current_action') or not w._current_action: return
            dx = event.x_root - w._start_x
            dy = event.y_root - w._start_y
            if w._current_action == "move":
                new_x = w._initial_x + dx
                new_y = w._initial_y + dy
                w.geometry(f"+{new_x}+{new_y}")
            elif w._current_action == "resize":
                new_x, new_y, new_w, new_h = w._initial_x, w._initial_y, w._start_w, w._start_h
                if "e" in w._resize_edge: new_w = w._start_w + dx
                if "w" in w._resize_edge: new_w, new_x = w._start_w - dx, w._initial_x + dx
                if "s" in w._resize_edge: new_h = w._start_h + dy
                if "n" in w._resize_edge: new_h, new_y = w._start_h - dy, w._initial_y + dy
                if new_w < 50: new_w = 50
                if new_h < 30: new_h = 30
                w.geometry(f"{new_w}x{new_h}+{new_x}+{new_y}")
            w.update_idletasks()
            update_label_wraplength(None)

        def on_release_subtitle(e):
            w._current_action = None
            self.subtitle_region_x, self.subtitle_region_y = w.winfo_x(), w.winfo_y()
            self.subtitle_region_w, self.subtitle_region_h = w.winfo_width(), w.winfo_height()

        def update_label_wraplength(event):
            l.config(wraplength=w.winfo_width() - 40)

        w.bind("<ButtonPress-1>", on_press_subtitle)
        w.bind("<B1-Motion>", on_drag_subtitle)
        w.bind("<ButtonRelease-1>", on_release_subtitle)
        w.bind("<Motion>", on_motion_subtitle)
        w.bind("<Configure>", update_label_wraplength)

        l = tk.Label(w, text=text, font=("Malgun Gothic", 16, "bold"), fg='white', bg='black')
        l.pack(padx=20, pady=10, expand=True, fill='both')

        # 오른쪽 클릭 시 창을 닫도록 설정
        w.bind("<Button-3>", lambda e: w.destroy())
        l.bind("<Button-3>", lambda e: w.destroy())

        tk.Button(w, text="X", command=w.destroy, bg="red", fg="white", font=("Arial", 8, "bold"), relief="flat", bd=0).place(relx=1.0, rely=0.0, anchor='ne', x=-2, y=2)
        
        w.update_idletasks()
        w.geometry(f"{self.subtitle_region_w}x{self.subtitle_region_h}+{self.subtitle_region_x}+{self.subtitle_region_y}")
        update_label_wraplength(None)

        # ctypes를 사용하여 창을 강제로 최상단으로 올림
        unique_title = f"OCR_Translator_Subtitle_{time.time()}"
        w.title(unique_title)
        
        def force_foreground():
            hwnd = ctypes.windll.user32.FindWindowW(None, unique_title)
            if hwnd:
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        w.after(50, force_foreground)

        # 설정 파일에서 읽어온 시간 후에 창 자동 닫기
        duration_ms = int(self.config['translation_duration_seconds'] * 1000)
        w.after(duration_ms, w.destroy)

    def process_ocr_and_translate(self):
        print("\n캡처 및 번역 진행 중...")
        try:
            screenshot = pyautogui.screenshot(region=self.region)
            text = pytesseract.image_to_string(screenshot, lang='eng', config='--psm 6')
            if not text:
                print("⚠️ 텍스트를 인식하지 못했습니다.")
                return
            
            cleaned_text = re.sub(r'\s+', ' ', text).strip()
            pyperclip.copy(cleaned_text)
            print("✅ 원문 클립보드에 복사 완료!")
            print("  - Gemini 번역 중...")
            
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"You are an expert translator. Translate the following English text into natural, fluent Korean. Only provide the translated text.\n\nEnglish: {cleaned_text}\nKorean:"
            translated_text = model.generate_content(prompt).text.strip()
            
            print("✅ 번역 완료!")
            self.create_subtitle_window(translated_text)
        except Exception as e:
            print(f"처리 중 오류 발생: {e}")
            self.create_subtitle_window(f"오류: {e}")

    def run(self):
        hotkey = self.config['show_translation_hotkey']
        print(f"✅ 준비 완료. [{hotkey.upper()}] 키: 번역 실행 | [ESC]: 종료")
        keyboard.add_hotkey(hotkey, self.process_ocr_and_translate)
        keyboard.add_hotkey('esc', self.quit)
        self.root.mainloop()

    def quit(self):
        print("프로그램을 종료합니다.")
        keyboard.unhook_all()
        self.root.quit()
        self.root.destroy()

if __name__ == "__main__":
    app = OCRTranslatorApp()
    app.run()