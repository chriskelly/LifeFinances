import tkinter as tk

class DWFrame(tk.Frame):
    def __init__(self,window,label,SecondWidget):
        super().__init__(window)
        label = tk.Label(self,text=label)
        label.pack( side = "left")
        SecondWidget.pack( side = "left" )
        if isinstance(SecondWidget,tk.Entry):
            pass
        