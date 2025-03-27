import sys
import numpy as np
import pygame
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QWidget, QLabel, QSlider, QComboBox, QCheckBox)
from PyQt5.QtCore import Qt, QTimer
import random
import time

# Initialize pygame for sound with explicit parameters
pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=4096)  # Mono, 44100 Hz, 16-bit

# English Morse code alphabet
MORSE_CODE_DICT = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.', 
    'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..', 
    'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.', 
    'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-', 
    'Y': '-.--', 'Z': '--..', '1': '.----', '2': '..---', '3': '...--', 
    '4': '....-', '5': '.....', '6': '-....', '7': '--...', '8': '---..', 
    '9': '----.', '0': '-----', ' ': '/'
}

# Koch method order for learning Morse code
KOCH_ORDER = ['K', 'M', 'R', 'E', 'S', 'N', 'A', 'P', 'T', 'L', 'W', 'I', 
              'J', 'Z', 'F', 'O', 'H', 'V', 'G', 'Q', 'Y', 'C', 'D', 'B', 
              'X', 'U']

# Expanded word list with early Koch-compatible words
WORD_LIST = ['me', 're', 'see', 'key', 'make', 'are', 'the', 'be', 'to', 'of', 
             'and', 'in', 'that', 'have', 'it', 'for', 'not', 'on', 'with', 
             'he', 'as', 'you', 'do', 'at', 'this', 'but']

class MorseButton(QPushButton):
    def __init__(self, parent):
        super().__init__("Key", parent)
        self.parent = parent
        self.tone = None
        self.press_time = None
        self.decode_timer = QTimer(self)
        self.decode_timer.setSingleShot(True)
        self.decode_timer.timeout.connect(self.parent.decode_morse_with_reset)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.parent.mode == "Straight Key":
                print("Debug: Straight Key - Left click (start tone)")
                self.press_time = time.time()
                sample_rate = 44100
                duration = 5000
                t = np.linspace(0, duration / 1000, int(sample_rate * duration / 1000), False)
                tone = np.sin(2 * np.pi * 700 * t) * 32767
                channels = pygame.mixer.get_num_channels() if pygame.mixer.get_init() else 1
                if channels == 1:
                    tone_2d = tone.reshape(-1, 1).astype(np.int16)
                else:
                    tone_2d = np.column_stack((tone, tone)).astype(np.int16)
                self.tone = pygame.sndarray.make_sound(tone_2d)
                self.tone.play(-1)
            elif self.parent.mode == "Iambic Key":
                print("Debug: Iambic Key - Left click (dit)")
                self.parent.generate_tone(self.parent.dit_length)
                self.parent.morse_input += "."
                self.parent.decode_morse()
        elif event.button() == Qt.RightButton and self.parent.mode == "Iambic Key":
            print("Debug: Iambic Key - Right click (dah)")
            self.parent.generate_tone(self.parent.dah_length)
            self.parent.morse_input += "-"
            self.parent.decode_morse()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.parent.mode == "Straight Key" and self.tone:
            print("Debug: Straight Key - Left release")
            self.tone.stop()
            duration = (time.time() - self.press_time) * 1000
            print(f"Debug: Tone duration: {duration:.0f} ms")

            if duration < self.parent.dit_length * 2:
                self.parent.morse_input += "."
                print("Debug: Added dit (.)")
            else:
                self.parent.morse_input += "-"
                print("Debug: Added dah (-)")
            
            self.parent.update_morse_display()
            self.decode_timer.start(750)
            self.parent.reset_display_timer.start(2000)

            self.tone = None
            self.press_time = None

class AlphaMorse(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AlphaMorse")
        self.setGeometry(100, 100, 400, 600)
        self.current_word = ""
        self.morse_input = ""
        self.koch_level = 5
        self.mode = "Straight Key"
        self.training_mode = "Letter"
        self.target_text = ""
        self.target_morse = ""
        self.correct_letters = []

        # Timere
        self.reset_display_timer = QTimer(self)
        self.reset_display_timer.setSingleShot(True)
        self.reset_display_timer.timeout.connect(self.reset_display)

        # Setup GUI
        self.init_ui()

    def init_ui(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Display label for decoded text
        self.display_label = QLabel("WELCOME TO ALPHAMORSE", self)
        self.display_label.setAlignment(Qt.AlignCenter)
        self.display_label.setStyleSheet("font-size: 20px;")
        layout.addWidget(self.display_label)

        # Morse input display
        self.morse_display = QLabel("", self)
        self.morse_display.setAlignment(Qt.AlignCenter)
        self.morse_display.setStyleSheet("font-size: 16px; color: #666;")
        layout.addWidget(self.morse_display)

        # Morse key button
        self.key_button = MorseButton(self)
        self.key_button.setFixedSize(100, 100)
        layout.addWidget(self.key_button, alignment=Qt.AlignCenter)

        # WPM slider
        self.wpm_slider = QSlider(Qt.Horizontal)
        self.wpm_slider.setMinimum(5)
        self.wpm_slider.setMaximum(40)
        self.wpm_slider.setValue(20)
        self.wpm_slider.valueChanged.connect(self.update_wpm)
        layout.addWidget(QLabel("WPM (Words Per Minute):"))
        layout.addWidget(self.wpm_slider)

        # Mode selector (Straight/Iambic)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Straight Key", "Iambic Key"])
        self.mode_combo.currentTextChanged.connect(self.update_mode)
        layout.addWidget(QLabel("Key Mode:"))
        layout.addWidget(self.mode_combo)

        # Training mode selector
        self.training_combo = QComboBox()
        self.training_combo.addItems(["Letter", "Word"])
        self.training_combo.currentTextChanged.connect(self.update_training_mode)
        layout.addWidget(QLabel("Training Mode:"))
        layout.addWidget(self.training_combo)

        # Dark mode toggle
        self.dark_mode_checkbox = QCheckBox("Dark Mode")
        self.dark_mode_checkbox.stateChanged.connect(self.toggle_dark_mode)
        layout.addWidget(self.dark_mode_checkbox)

        # Training button
        self.train_button = QPushButton("Start Training", self)
        self.train_button.clicked.connect(self.start_training)
        layout.addWidget(self.train_button)

        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.update_wpm()

    def update_wpm(self):
        self.wpm = self.wpm_slider.value()
        self.dit_length = 1200 // self.wpm
        self.dah_length = self.dit_length * 3

    def update_mode(self):
        self.mode = self.mode_combo.currentText()

    def update_training_mode(self):
        self.training_mode = self.training_combo.currentText()
        self.reset_training()

    def toggle_dark_mode(self):
        if self.dark_mode_checkbox.isChecked():
            self.setStyleSheet("background-color: #333; color: #FFF;")
            self.key_button.setStyleSheet("background-color: #555; color: #FFF;")
            self.morse_display.setStyleSheet("font-size: 16px; color: #BBB;")
        else:
            self.setStyleSheet("background-color: #FFF; color: #000;")
            self.key_button.setStyleSheet("background-color: #DDD; color: #000;")
            self.morse_display.setStyleSheet("font-size: 16px; color: #666;")
        self.update_display()

    def generate_tone(self, duration, frequency=700):
        sample_rate = 44100
        t = np.linspace(0, duration / 1000, int(sample_rate * duration / 1000), False)
        tone = np.sin(2 * np.pi * frequency * t) * 32767
        channels = pygame.mixer.get_num_channels() if pygame.mixer.get_init() else 1
        if channels == 1:
            tone_2d = tone.reshape(-1, 1).astype(np.int16)
        else:
            tone_2d = np.column_stack((tone, tone)).astype(np.int16)
        try:
            sound = pygame.sndarray.make_sound(tone_2d)
            sound.play()
        except Exception as e:
            print(f"Debug: Error in generate_tone - {e}")

    def decode_morse(self):
        reverse_dict = {value: key for key, value in MORSE_CODE_DICT.items()}
        print(f"Debug: Attempting to decode morse_input: '{self.morse_input}'")
        if self.morse_input in reverse_dict:
            letter = reverse_dict[self.morse_input]
            if self.training_mode == "Letter":
                if self.target_text and letter == self.target_text:
                    self.current_word = letter
                    self.display_label.setStyleSheet("font-size: 20px; color: green;")
                    print(f"Debug: Correct letter '{letter}'")
                else:
                    print(f"Debug: Incorrect letter, expected '{self.target_text}'")
            elif self.training_mode == "Word":
                if self.target_morse and self.morse_input == self.target_morse.split()[len(self.correct_letters)]:
                    self.correct_letters.append(letter)
                    print(f"Debug: Correct letter '{letter}' in word")
                    if len(self.correct_letters) == len(self.target_text):
                        self.current_word = self.target_text
                        self.display_label.setStyleSheet("font-size: 20px; color: green;")
                        print("Debug: Entire word correct!")
                    self.update_display()
                else:
                    print(f"Debug: Incorrect letter, expected '{self.target_morse.split()[len(self.correct_letters)]}'")
        self.update_display()

    def decode_morse_with_reset(self):
        self.decode_morse()
        self.morse_input = ""
        self.update_morse_display()
        print("Debug: Reset morse_input after decoding")

    def update_morse_display(self):
        self.morse_display.setText(self.morse_input if self.morse_input else "")

    def reset_display(self):
        self.current_word = ""
        self.update_display()
        print("Debug: Reset display_label after pause")

    def update_display(self):
        if not self.target_text:
            self.display_label.setText("Press 'Start Training' to begin")
            return
        if self.training_mode == "Letter":
            self.display_label.setText(f"{self.target_text}\n{self.target_morse}")
            if self.current_word == self.target_text:
                self.display_label.setStyleSheet("font-size: 20px; color: green;")
            else:
                self.display_label.setStyleSheet("font-size: 20px; color: #000;" if not self.dark_mode_checkbox.isChecked() else "font-size: 20px; color: #FFF;")
        elif self.training_mode == "Word":
            display_text = ""
            for i, char in enumerate(self.target_text):
                if i < len(self.correct_letters) and self.correct_letters[i] == char:
                    display_text += f"<span style='color: green'>{char}</span>"
                else:
                    display_text += char
            display_text += f"\n{self.target_morse}"
            self.display_label.setText(f"<html>{display_text}</html>")
            if len(self.correct_letters) == len(self.target_text):
                self.display_label.setStyleSheet("font-size: 20px; color: green;")

    def reset_training(self):
        self.current_word = ""
        self.morse_input = ""
        self.correct_letters = []
        self.target_text = ""
        self.target_morse = ""
        self.display_label.setStyleSheet("font-size: 20px; color: #000;" if not self.dark_mode_checkbox.isChecked() else "font-size: 20px; color: #FFF;")
        self.update_morse_display()
        self.update_display()

    def start_training(self):
        self.reset_training()
        if self.training_mode == "Letter":
            self.target_text = random.choice(KOCH_ORDER[:self.koch_level])
            self.target_morse = MORSE_CODE_DICT[self.target_text]
            self.update_display()
            # Fjernet play_morse her
        elif self.training_mode == "Word":
            self.target_text = random.choice([w for w in WORD_LIST if all(c.upper() in KOCH_ORDER[:self.koch_level] for c in w)]).upper()
            self.target_morse = self.encode_to_morse(self.target_text)
            self.update_display()
            # Fjernet play_morse her

    def encode_to_morse(self, text):
        return " ".join(MORSE_CODE_DICT.get(char.upper(), "") for char in text)

    def play_morse(self, morse):
        for symbol in morse:
            if symbol == ".":
                self.generate_tone(self.dit_length)
                pygame.time.wait(self.dit_length + 50)
            elif symbol == "-":
                self.generate_tone(self.dah_length)
                pygame.time.wait(self.dah_length + 50)
            elif symbol == " ":
                pygame.time.wait(self.dit_length * 3)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AlphaMorse()
    window.show()
    sys.exit(app.exec_())