from tkinter import *


class Parameter:
    def __init__(self,name,value):
        self.name = name
        self.val = value
        self.lbl = Label(text=self.name)
        self.input = Entry(width=10)