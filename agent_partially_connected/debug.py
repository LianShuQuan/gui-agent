from pynput import keyboard
import pyperclip
import time
from threading import Timer

class TypeRecorder:
    def __init__(self):
        self.typing_buffer = []  # 存储按键
        self.last_key_time = 0   # 上次按键时间
        self.typing_timeout = 1.0 # 打字超时时间
        self.last_clipboard = ''  # 上次剪贴板内容
        self.is_typing = False    # 是否正在打字
        self.control_pressed = False
        self.shift_pressed = False
        
    def start(self):
        # 启动键盘监听
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release)
        self.keyboard_listener.start()
        
    def check_typing_timeout(self):
        if self.is_typing:
            # 检查剪贴板变化
            current_clipboard = pyperclip.paste()
            if current_clipboard != self.last_clipboard:
                # 找出新增的文本
                new_text = self.get_new_text(self.last_clipboard, current_clipboard)
                if new_text:
                    print(f"Typing(text='{new_text}')")
                self.last_clipboard = current_clipboard
            
            self.is_typing = False
            self.typing_buffer = []
    
    def get_new_text(self, old_text, new_text):
        """识别新增的文本"""
        if len(new_text) <= len(old_text):
            return ''
        # 假设新文本总是在末尾添加
        return new_text[len(old_text):]
    
    def on_press(self, key):
        current_time = time.time()
        
        # 检查控制键
        if key == keyboard.Key.ctrl:
            self.control_pressed = True
            return
        if key == keyboard.Key.shift:
            self.shift_pressed = True
            return
            
        # 处理快捷键
        if self.control_pressed or self.shift_pressed:
            try:
                key_char = key.char
            except AttributeError:
                key_char = str(key)
            print(f"Shortcut: {'Ctrl+' if self.control_pressed else ''}{'Shift+' if self.shift_pressed else ''}{key_char}")
            return
            
        # 普通打字操作
        if not self.is_typing:
            self.is_typing = True
            self.last_clipboard = pyperclip.paste()
            
        self.typing_buffer.append(key)
        self.last_key_time = current_time
        
        # 设置超时检查
        Timer(self.typing_timeout, self.check_typing_timeout).start()
        
    def on_release(self, key):
        if key == keyboard.Key.ctrl:
            self.control_pressed = False
        elif key == keyboard.Key.shift:
            self.shift_pressed = False

if __name__ == "__main__":
    recorder = TypeRecorder()
    recorder.start()
    print("Recording started... Press Ctrl+C to exit")
    
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nRecording stopped.")