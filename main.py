import sys
import os

# Garante que o diretório do app está no path para imports relativos
sys.path.insert(0, os.path.dirname(__file__))

from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from screens.main_screen import MainScreen
from screens.result_screen import ResultScreen


class DiveCalcApp(MDApp):

    def build(self):
        self.title = "Mergulho Bühlmann ZH-L16C"
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "Cyan"
        self.theme_cls.theme_style = "Dark"

        sm = ScreenManager(transition=SlideTransition())
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(ResultScreen(name='result'))
        return sm


if __name__ == "__main__":
    DiveCalcApp().run()
