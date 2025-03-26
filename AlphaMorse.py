import sys
import numpy as np
import pygame
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QWidget, QLabel, QSlider, QComboBox, QCheckBox)
from PyQt5.QtCore import Qt
import random

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

# Common CW abbreviations for radio amateurs
CW_ABBREVIATIONS = {
    'CQ': 'Call for contact', 'QTH': 'Location', 'RST': 'Signal report', 
    '73': 'Best regards', 'SK': 'End of contact'
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

    def mousePressEvent(self, event):
        """Handle mouse press events on the button."""
        if event.button() == Qt.LeftButton:
            if self.parent.mode == "Straight Key":
                print("Debug: Straight Key - Left click (dit)")
                self.parent.generate_tone(self.parent.dit_length)
                self.parent.morse_input += "."
                self.parent.decode_morse()
            elif self.parent.mode == "Iambic Key":
                print("Debug: Iambic Key - Left click (dit)")
                self.parent.generate_tone(self.parent.dit_length)
                self.parent.morse_input += "."
                self.parent.decode_morse()
        elif event.button() == Qt.RightButton:
            if self.parent.mode == "Iambic Key":
                print("Debug: Iambic Key - Right click (dah)")
                self.parent.generate_tone(self.parent.dah_length)
                self.parent.morse_input += "-"
                self.parent.decode_morse()
            else:
                print("Debug: Right click ignored in Straight Key mode")
        else:
            print(f"Debug: Unknown button clicked - Button: {event.button()}, Mode: {self.parent.mode}")

class AlphaMorse(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AlphaMorse")
        self.setGeometry(100, 100, 400, 600)
        self.current_word = ""
        self.morse_input = ""
        self.koch_level = 5  # Start with first 5 Koch letters for more word options
        self.mode = "Straight Key"  # Default mode

        # Setup GUI
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        widget = QWidget()
        layout = QVBoxLayout()

        # Display label for showing decoded text
        self.display_label = QLabel("WELCOME TO ALPHAMORSE", self)
        self.display_label.setAlignment(Qt.AlignCenter)
        self.display_label.setStyleSheet("font-size: 20px;")
        layout.addWidget(self.display_label)

        # Morse key button using custom class
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

        # Mode selector (Straight or Iambic)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Straight Key", "Iambic Key"])
        self.mode_combo.currentTextChanged.connect(self.update_mode)
        layout.addWidget(QLabel("Key Mode:"))
        layout.addWidget(self.mode_combo)

        # Dark mode toggle
        self.dark_mode_checkbox = QCheckBox("Dark Mode")
        self.dark_mode_checkbox.stateChanged.connect(self.toggle_dark_mode)
        layout.addWidget(self.dark_mode_checkbox)

        # Training button for Koch method
        self.train_button = QPushButton("Start Koch Training", self)
        self.train_button.clicked.connect(self.koch_training)
        layout.addWidget(self.train_button)

        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.update_wpm()  # Set initial WPM timing

    def update_wpm(self):
        """Update timing based on WPM value."""
        self.wpm = self.wpm_slider.value()
        self.dit_length = 1200 // self.wpm  # Time in ms for one "dit"
        self.dah_length = self.dit_length * 3  # "Dah" is 3x "dit"

    def update_mode(self):
        """Update keying mode."""
        self.mode = self.mode_combo.currentText()

    def toggle_dark_mode(self):
        """Switch between light and dark mode."""
        if self.dark_mode_checkbox.isChecked():
            self.setStyleSheet("background-color: #333; color: #FFF;")
            self.key_button.setStyleSheet("background-color: #555; color: #FFF;")
        else:
            self.setStyleSheet("background-color: #FFF; color: #000;")
            self.key_button.setStyleSheet("background-color: #DDD; color: #000;")

    def generate_tone(self, duration, frequency=700):
        """Generate a sine wave tone for 'dit' or 'dah'."""
        sample_rate = 44100
        t = np.linspace(0, duration / 1000, int(sample_rate * duration / 1000), False)
        tone = np.sin(2 * np.pi * frequency * t) * 32767
        channels = pygame.mixer.get_num_channels() if pygame.mixer.get_init() else 1
        if channels == 1:
            tone_2d = tone.reshape(-1, 1).astype(np.int16)  # Mono
        else:
            tone_2d = np.column_stack((tone, tone)).astype(np.int16)  # Stereo
        try:
            sound = pygame.sndarray.make_sound(tone_2d)
            sound.play()
        except Exception as e:
            print(f"Debug: Error in generate_tone - {e}")

    def decode_morse(self):
        """Decode Morse input to text."""
        reverse_dict = {value: key for key, value in MORSE_CODE_DICT.items()}
        if self.morse_input in reverse_dict:
            self.current_word += reverse_dict[self.morse_input]
            self.morse_input = ""
        elif self.morse_input == "":
            self.current_word += " "  # Space between words
        self.display_label.setText(self.current_word.upper())

    def encode_to_morse(self, text):
        """Convert text to Morse code."""
        return " ".join(MORSE_CODE_DICT.get(char.upper(), "") for char in text)

    def koch_training(self):
        """Generate a random word using current Koch level letters and play it."""
        available_letters = KOCH_ORDER[:self.koch_level]
        try:
            word = random.choice([w for w in WORD_LIST if all(c.upper() in available_letters for c in w)])
            morse = self.encode_to_morse(word)
            self.display_label.setText(f"Listen: {morse}")
            for symbol in morse:
                if symbol == ".":
                    self.generate_tone(self.dit_length)
                    pygame.time.wait(self.dit_length + 50)
                elif symbol == "-":
                    self.generate_tone(self.dah_length)
                    pygame.time.wait(self.dah_length + 50)
                elif symbol == " ":
                    pygame.time.wait(self.dit_length * 3)
            self.current_word = ""
            self.morse_input = ""
        except Exception as e:
            print(f"Debug: Error in koch_training - {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AlphaMorse()
    window.show()
    sys.exit(app.exec_())