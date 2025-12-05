import tkinter as tk

class ToolTip:
    """
    Creates a tooltip for a given widget.
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.id = None
        self.x = self.y = 0
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
        self.id = None

    def showtip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left',
                       background="#ffffe0", relief='solid', borderwidth=1,
                       font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tooltip_window
        self.tooltip_window = None
        if tw:
            tw.destroy()

def create_tooltip(widget, text):
    """Factory function to create a tooltip for a widget."""
    ToolTip(widget, text)

def format_speed(Bps: float) -> str:
    """Formats speed from Bytes/sec to a readable string (kbps/Mbps)."""
    # Handle invalid or negative inputs gracefully.
    if not isinstance(Bps, (int, float)):
        raise TypeError("Speed must be a numeric value.")
    if Bps < 0:
        Bps = 0
        
    if Bps < 125000:  # Under 1 Mbps (125,000 Bytes/sec)
        return f"{Bps * 8 / 1000:.1f} kbps"
    else:
        return f"{Bps * 8 / 1000000:.2f} Mbps"