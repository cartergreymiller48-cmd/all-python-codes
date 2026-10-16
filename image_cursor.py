"""Image Cursor - run with:  python image_cursor.py   (Windows)
Needs Pillow once:  pip install pillow
Pick an image, press Start, and it becomes your mouse cursor. Press Stop to get your normal cursor back."""
import atexit
import ctypes
import os
import subprocess
import sys
import traceback
import tkinter as tk
from ctypes import wintypes
from tkinter import filedialog, messagebox

if sys.platform != "win32":
    sys.exit("Image Cursor only works on Windows.")


def show_error(exc_type, exc, tb):
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    try:
        with open(os.path.join(os.path.expanduser("~"), "image_cursor_error.txt"), "w") as f:
            f.write(text)
    except Exception:
        pass
    try:
        r = tk.Tk()
        r.withdraw()
        messagebox.showerror("Image Cursor had a problem", text[-900:])
    except Exception:
        print(text)
        input("Press Enter to close...")


sys.excepthook = show_error

try:
    from PIL import Image, ImageTk
except ImportError:  # first run: install Pillow automatically
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
        from PIL import Image, ImageTk
    except Exception:
        r = tk.Tk()
        r.withdraw()
        messagebox.showerror("Image Cursor", "I couldn't install Pillow.\nOpen Command Prompt and type:\n\npy -m pip install pillow")
        sys.exit(1)

user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32


class ICONINFO(ctypes.Structure):
    _fields_ = [("fIcon", wintypes.BOOL), ("xHotspot", wintypes.DWORD), ("yHotspot", wintypes.DWORD),
                ("hbmMask", ctypes.c_void_p), ("hbmColor", ctypes.c_void_p)]


gdi32.CreateBitmap.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p]
gdi32.CreateBitmap.restype = ctypes.c_void_p
gdi32.DeleteObject.argtypes = [ctypes.c_void_p]
user32.CreateIconIndirect.argtypes = [ctypes.POINTER(ICONINFO)]
user32.CreateIconIndirect.restype = ctypes.c_void_p
user32.SetSystemCursor.argtypes = [ctypes.c_void_p, wintypes.DWORD]

# the normal cursor shapes Windows uses (arrow, text, hand, busy, resize, ...)
CURSOR_IDS = [32512, 32513, 32514, 32515, 32516, 32642, 32643, 32644, 32645, 32646, 32648, 32649, 32650]
SPI_SETCURSORS = 0x0057


def restore_cursors():
    user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)


def make_cursor(img, hot):
    w, h = img.size
    r, g, b, a = img.convert("RGBA").split()
    bgra = Image.merge("RGBA", (b, g, r, a)).tobytes()
    color = gdi32.CreateBitmap(w, h, 1, 32, ctypes.create_string_buffer(bgra, len(bgra)))
    mask_bytes = bytes(((w + 15) // 16) * 2 * h)
    mask = gdi32.CreateBitmap(w, h, 1, 1, ctypes.create_string_buffer(mask_bytes, len(mask_bytes)))
    info = ICONINFO(False, hot[0], hot[1], mask, color)
    cur = user32.CreateIconIndirect(ctypes.byref(info))
    gdi32.DeleteObject(color)
    gdi32.DeleteObject(mask)
    return cur


atexit.register(restore_cursors)  # always give you your normal cursor back

root = tk.Tk()
root.report_callback_exception = show_error
root.title("Image Cursor")
root.geometry("340x470")
root.resizable(False, False)
state = {"img": None, "on": False}

tk.Label(root, text="Image Cursor", font=("Segoe UI", 15, "bold")).pack(pady=(12, 2))
preview = tk.Label(root, text="No image yet", width=26, height=8, bg="#eee")
preview.pack(pady=6)
status = tk.Label(root, text="Cursor: normal", fg="#555")


def choose():
    path = filedialog.askopenfilename(title="Pick an image",
                                      filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp *.ico"), ("All files", "*.*")])
    if not path:
        return
    try:
        img = Image.open(path).convert("RGBA")
    except Exception:
        messagebox.showerror("Image Cursor", "I couldn't open that image.")
        return
    if img.getchannel("A").getextrema()[1] == 0:
        messagebox.showerror("Image Cursor", "That image is fully see-through, so you couldn't see your cursor.")
        return
    state["img"] = img
    thumb = img.copy()
    thumb.thumbnail((150, 120))
    tkimg = ImageTk.PhotoImage(thumb)
    preview.config(image=tkimg, text="", width=150, height=120)
    preview.image = tkimg
    start_btn.config(state="normal")


def start():
    if state["img"] is None:
        return
    size = size_var.get()
    img = state["img"].copy()
    img.thumbnail((size, size))
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))  # square, so the click point is predictable
    canvas.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
    hot = (size // 2, size // 2) if hot_var.get() == "center" else (0, 0)
    restore_cursors()
    for cid in CURSOR_IDS:
        cur = make_cursor(canvas, hot)  # Windows takes ownership of each handle, so make a new one each time
        if cur:
            user32.SetSystemCursor(cur, cid)
    state["on"] = True
    status.config(text="Cursor: YOUR IMAGE (press Stop to undo)", fg="#168a3a")


def stop(event=None):
    restore_cursors()
    state["on"] = False
    status.config(text="Cursor: normal", fg="#555")


def on_close():
    restore_cursors()
    root.destroy()


tk.Button(root, text="Choose image...", command=choose).pack(pady=4)
size_var = tk.IntVar(value=48)
tk.Label(root, text="Cursor size").pack()
tk.Scale(root, from_=16, to=128, orient="horizontal", variable=size_var, length=240).pack()
hot_var = tk.StringVar(value="topleft")
row = tk.Frame(root)
row.pack(pady=4)
tk.Label(row, text="Click point:").pack(side="left")
tk.Radiobutton(row, text="Top-left", variable=hot_var, value="topleft").pack(side="left")
tk.Radiobutton(row, text="Center", variable=hot_var, value="center").pack(side="left")
btns = tk.Frame(root)
btns.pack(fill="x", padx=14, pady=8)
start_btn = tk.Button(btns, text="START", bg="#27ae60", fg="white", bd=0, font=("Segoe UI", 12, "bold"),
                      state="disabled", command=start)
start_btn.pack(side="left", expand=True, fill="x", padx=(0, 6), ipady=8)
tk.Button(btns, text="STOP", bg="#d9423a", fg="white", bd=0, font=("Segoe UI", 12, "bold"),
          command=stop).pack(side="left", expand=True, fill="x", padx=(6, 0), ipady=8)
status.pack()
tk.Label(root, text="Tip: press Esc in this window to stop.", fg="#888", font=("Segoe UI", 8)).pack(pady=4)
root.bind("<Escape>", stop)
root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
