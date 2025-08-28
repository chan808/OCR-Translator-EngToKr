# OCR-Translator-EngToKr

영역 지정 후 영어 텍스트를 읽어 자동으로 한국어로 번역해주는 파이썬 데스크톱 프로그램입니다.  
OCR + Gemini API를 활용하여 실시간 AI 번역을 지원합니다.

---

## 필요한 라이브러리 설치:
```bash
pip install pyautogui pyperclip keyboard pillow pytesseract google-generativeai
```
## 📌 사용법

- 바탕화면\Tesseract-OCR\tesseract.exe 경로에 맞게 Tesseract-OCR 설치
- Config.json 파일에서 다음 3가지 지정
    - Gemini api key
    - 번역 결과 창 유지 시간
    - 번역 단축키
- python "~\Translator-EngToKr.py" 로 실행
- 번역할 영역 지정 후 지정한 번역 단축키를 통해 번역 실행
- 번역 창 위치와 크기 조정 후 사용
  
<img width="1032" height="588" alt="OCR1" src="https://github.com/user-attachments/assets/fd934f84-0cba-44a1-a283-ee88c849f284" />
<img width="2192" height="373" alt="OCR2" src="https://github.com/user-attachments/assets/4a9b76aa-90f1-4fc9-a06f-6f667593b6ec" />
