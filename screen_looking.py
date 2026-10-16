"""Screen Looking - run with:  python screen_looking.py
Plug in your Android phone (USB debugging on). You'll see its screen and its apps on your PC.
VIEW ONLY: nothing you do on the PC (scrolling, clicking) is ever sent to the phone."""
import base64
import importlib
import importlib.util
import json
import math
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import traceback
from tkinter import font as tkfont
from tkinter import messagebox

W, H = 760, 500
BG1, BG2, MAIN_BG = "#0f1b33", "#0b3d4a", "#10172a"


def show_error(exc_type, exc, tb):
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    try:
        r = tk.Tk()
        r.withdraw()
        messagebox.showerror("Screen Looking had a problem", text[-900:])
    except Exception:
        print(text)
        input("Press Enter to close...")


sys.excepthook = show_error


# ------------------------------------------------------------------ cutscene
def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(pa[i] + (pb[i] - pa[i]) * t) for i in range(3))


def ease_out_back(t):
    t = max(0.0, min(1.0, t))
    return 1 + 2.70158 * (t - 1) ** 3 + 1.70158 * (t - 1) ** 2


def rrect(c, x0, y0, x1, y1, r, **kw):
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return c.create_polygon(pts, smooth=True, **kw)


def monitor(c, x, y, s, col="#5aa9ff"):
    c.create_rectangle(x - 60 * s, y - 40 * s, x + 60 * s, y + 30 * s, fill="#1d2b4d", outline=col, width=max(2, int(4 * s)))
    c.create_rectangle(x - 50 * s, y - 31 * s, x + 50 * s, y + 21 * s, fill=col, outline="")
    c.create_rectangle(x - 8 * s, y + 30 * s, x + 8 * s, y + 44 * s, fill=col, outline="")
    c.create_rectangle(x - 28 * s, y + 44 * s, x + 28 * s, y + 50 * s, fill=col, outline="")


def phone(c, x, y, s, col="#ffd166", tiles=False):
    rrect(c, x - 26 * s, y - 50 * s, x + 26 * s, y + 50 * s, 10 * s, fill="#1d2b4d", outline=col, width=max(2, int(4 * s)))
    if tiles:
        colors = ["#ff6b6b", "#4dd599", "#5aa9ff", "#ffd166", "#c792ea", "#7ee8ff"]
        for i in range(6):
            tx, ty = x - 15 * s + (i % 2) * 17 * s, y - 36 * s + (i // 2) * 24 * s
            rrect(c, tx, ty, tx + 13 * s, ty + 18 * s, 4 * s, fill=colors[i], outline="")
    else:
        c.create_rectangle(x - 18 * s, y - 38 * s, x + 18 * s, y + 36 * s, fill=col, outline="")


def star(c, x, y, s, col):
    k = s * 0.25
    c.create_polygon(x, y - s, x + k, y - k, x + s, y, x + k, y + k, x, y + s, x - k, y + k, x - s, y, x - k, y - k,
                     fill=col, outline="")


INTRO_FRAMES = 365


def draw_intro(c, t, adv):
    c.delete("all")
    bg = BG1 if t < 190 else mix(BG1, BG2, (t - 190) / 40)
    c.create_rectangle(0, 0, W, H, fill=bg, outline="")
    if t < 190:  # "Screen share? Who needs that?"
        fall = max(0, t - 115)
        cy = 270 + 0.45 * fall * fall
        sh = math.sin(t * 1.7) * 4 if 75 < t < 115 else 0
        monitor(c, 230 + sh, cy, 1.4)
        phone(c, 530 + sh, cy, 1.4)
        c.create_line(330 + sh, cy, 430 + sh, cy, fill="#9bd1ff", width=5, dash=(10, 8), dashoffset=int(-t), arrow="last")
        if t >= 60:
            r = 62 * ease_out_back((t - 60) / 20)
            xs = 380 + sh
            c.create_line(xs - r, cy - r, xs + r, cy + r, fill="#ff4d5e", width=16, capstyle="round")
            c.create_line(xs - r, cy + r, xs + r, cy - r, fill="#ff4d5e", width=16, capstyle="round")
        if t < 110:
            c.create_text(W / 2, 90, text="Screen share?", font=("Segoe UI", 40, "bold"), fill=mix(bg, "#ffffff", t / 25))
        else:
            c.create_text(W / 2, 90, text="Who needs that?", font=("Segoe UI", 40, "bold"), fill=mix(bg, "#ffffff", (t - 110) / 20))
            for k in range(3):
                c.create_text(150 + k * 230, 400 + math.sin(t / 6 + k) * 10, text="?", font=("Segoe UI", 44, "bold"),
                              fill=mix(bg, "#8fa3c7", (t - 120) / 20))
    else:  # "Say hello to SCREEN LOOKING!"
        u = t - 190
        if u > 30:
            for i in range(16):
                sz = max(0.0, math.sin(u / 7 + i)) * 11
                if sz > 1:
                    star(c, (i * 137) % (W - 40) + 20, (i * 89) % (H - 40) + 20, sz, "#ffe9a8")
        sp = ease_out_back((u - 25) / 25)
        if sp > 0.02:
            monitor(c, 110 - (1 - sp) * 220, 215, 0.95 * sp)
            phone(c, 650 + (1 - sp) * 220, 215, 0.95 * sp, tiles=True)
        e = ease_out_back((u - 8) / 24)
        if e > 0.02:
            look, look_y, m = math.sin(u / 16), math.sin(u / 10), u % 90
            squish = max(0.08, abs(m - 63) / 3) if 60 <= m <= 66 else 1.0
            squish = min(1.0, squish)
            for ex in (W / 2 - 80, W / 2 + 80):
                ry = 62 * e * squish
                c.create_oval(ex - 56 * e, 190 - ry, ex + 56 * e, 190 + ry, fill="white", outline="#1a1a2e", width=4)
                px, py, pr = ex + 22 * look * e, 190 + 12 * look_y * e, 22 * e
                c.create_oval(px - pr, py - pr * squish, px + pr, py + pr * squish, fill="#1a1a2e", outline="")
        if u > 40:
            c.create_text(W / 2, 308, text="Say hello to", font=("Segoe UI", 22), fill=mix(bg, "#cfe9ff", (u - 40) / 20))
        word = "SCREEN LOOKING!"
        x0 = W / 2 - adv * len(word) / 2
        for i, ch in enumerate(word):
            s = u - 60 - i * 3
            if s > 0:
                p = ease_out_back(s / 14)
                c.create_text(x0 + adv * (i + 0.5), 360 + 70 * (1 - p), text=ch, font=("Courier New", 34, "bold"),
                              fill=mix("#7ee8ff", "#ffd166", i / len(word)))
    if t >= 345:
        c.create_rectangle(0, 0, W * (t - 345) / 20, H, fill=MAIN_BG, outline="")
    else:
        c.create_text(W - 10, H - 8, anchor="se", text="click to skip", font=("Segoe UI", 9), fill=mix(bg, "#ffffff", 0.35))


# ------------------------------------------------------------------ phone access (adb)
NO_WINDOW = 0x08000000 if os.name == "nt" else 0
ADB_HELP = ("Screen Looking needs Android's free tool called adb.\n\n"
            "1. Download 'platform-tools' from developer.android.com/tools/releases/platform-tools\n"
            "2. Unzip it into the same folder as this program (so there's a 'platform-tools' folder).\n"
            "3. On your phone: Settings > About phone > tap 'Build number' 7 times,\n"
            "   then Developer options > turn on USB debugging.\n"
            "4. Plug the phone in with USB and tap Allow on the phone.\n\n"
            "(This works with Android phones.)")


def find_adb():
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("adb.exe", "adb"):
        for sub in ("", "platform-tools"):
            p = os.path.join(here, sub, name)
            if os.path.exists(p):
                return p
    return shutil.which("adb")


ADB = find_adb()


def adb(*args, serial=None, timeout=8, raw=False):
    cmd = [ADB] + (["-s", serial] if serial else []) + list(args)
    r = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=NO_WINDOW)
    return r.stdout if raw else r.stdout.decode("utf-8", "replace")


def devices():
    out = adb("devices", timeout=20)
    return [(p[0], p[1]) for p in (ln.split() for ln in out.splitlines()[1:]) if len(p) >= 2]


def recent_apps(serial):
    txt = adb("shell", "dumpsys", "activity", "recents", serial=serial, timeout=15)
    found = []
    for m in re.finditer(r"(?:realActivity=|\bA=\d+:)([A-Za-z][\w.]*)", txt):  # keeps the phone's own order
        if m.group(1) not in found:
            found.append(m.group(1))
    return found


def installed_apps(serial, system):
    out = adb("shell", "pm", "list", "packages", *([] if system else ["-3"]), serial=serial, timeout=20)
    return sorted(ln[8:].strip() for ln in out.splitlines() if ln.startswith("package:"))


# ------------------------------------------------------------------ Apple (iPhone / iPad)
APPLE_HELP = ("Apple setup:\n\n"
              "1. Windows: install iTunes or the 'Apple Devices' app from the Microsoft Store (it gives your PC the\n"
              "   iPhone USB driver). On a Mac nothing is needed.\n"
              "2. Plug the iPhone/iPad in with USB and tap Trust on it.\n"
              "3. Screen Looking installs its Apple tool (pymobiledevice3) by itself the first time.\n\n"
              "For the live screen picture you may also need Developer Mode on the iPhone\n"
              "(Settings > Privacy & Security > Developer Mode). The app list works without it.")
APPLE_SCREEN_HELP = ("The apps list works, but Apple blocks the live screen\npicture until Developer Mode is on\n"
                     "(iPhone Settings > Privacy & Security >\nDeveloper Mode). On iOS 17 or newer it also needs\n"
                     "this run once in an Administrator\nCommand Prompt:\n  py -m pymobiledevice3 remote tunneld")
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def pmd(*args, udid=None, timeout=30):
    cmd = [sys.executable, "-m", "pymobiledevice3"] + list(args) + (["--udid", udid] if udid else [])
    r = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=NO_WINDOW)
    if r.returncode != 0:
        raise RuntimeError(ANSI.sub("", r.stderr.decode("utf-8", "replace")).strip()[-300:] or "command failed")
    return ANSI.sub("", r.stdout.decode("utf-8", "replace"))


def apple_devices():
    data = json.loads(pmd("usbmux", "list"))
    return [(d.get("UniqueDeviceID") or d.get("SerialNumber") or d.get("Identifier"), d.get("DeviceName", ""),
             d.get("ProductType", "")) for d in data if isinstance(d, dict)]


def apple_apps(udid, system):
    data = json.loads(pmd("apps", "list", udid=udid, timeout=60))
    out = []
    for bundle, info in data.items():
        if not system and info.get("ApplicationType") != "User":
            continue
        out.append(f'{info.get("CFBundleDisplayName") or info.get("CFBundleName") or bundle}  ({bundle})')
    return sorted(out, key=str.lower)


def apple_running(udid):
    try:  # only works when Developer Mode is on, otherwise the iPhone doesn't share this
        procs = json.loads(pmd("developer", "dvt", "proclist", udid=udid, timeout=30))
        return [p.get("name", "?") for p in procs if p.get("isApplication")]
    except Exception:
        return []


def apple_screenshot(udid):
    path = os.path.join(tempfile.gettempdir(), "screen_looking_apple.png")
    last = RuntimeError("no screenshot")
    for cmd in (("developer", "dvt", "screenshot"), ("developer", "screenshot")):
        try:
            if os.path.exists(path):
                os.remove(path)
            pmd(*cmd, path, udid=udid, timeout=40)
            with open(path, "rb") as f:
                data = f.read()
            if data[:4] != b"\x89PNG":  # older iPhones give another picture format
                import io
                from PIL import Image
                buf = io.BytesIO()
                Image.open(io.BytesIO(data)).convert("RGB").save(buf, "PNG")
                data = buf.getvalue()
            return data
        except Exception as e:
            last = e
    raise last


# ------------------------------------------------------------------ the program
def main():
    root = tk.Tk()
    root.report_callback_exception = show_error
    root.title("Screen Looking")
    root.geometry(f"{W}x{H}")
    root.configure(bg=MAIN_BG)
    adv = tkfont.Font(family="Courier New", size=34, weight="bold").measure("M")
    st = {"t": 0, "intro": True, "look": False, "serial": None, "mode": "android"}
    ui_q = queue.Queue()

    cv = tk.Canvas(root, width=W, height=H, highlightthickness=0, bg=BG1)
    cv.pack()
    menu = tk.Frame(root, bg=MAIN_BG)
    view = tk.Frame(root, bg=MAIN_BG)

    def intro_step():
        if not st["intro"]:
            return
        draw_intro(cv, st["t"], adv)
        st["t"] += 1
        if st["t"] > INTRO_FRAMES:
            end_intro()
        else:
            root.after(27, intro_step)

    def end_intro(event=None):
        if not st["intro"]:
            return
        st["intro"] = False
        cv.pack_forget()
        menu.pack(fill="both", expand=True)
        check_phone()

    cv.bind("<Button-1>", end_intro)
    root.bind("<Key>", end_intro)

    # ---- menu
    tk.Label(menu, text="Screen Looking", bg=MAIN_BG, fg="#7ee8ff", font=("Segoe UI", 32, "bold")).pack(pady=(70, 6))
    tk.Label(menu, text="See your phone's screen and apps on your PC.\nView only: scrolling here never touches the phone.",
             bg=MAIN_BG, fg="#cfe0ff", font=("Segoe UI", 12)).pack()
    status = tk.Label(menu, text="Looking for a phone...", bg=MAIN_BG, fg="#ffd166", font=("Segoe UI", 11))
    status.pack(pady=24)
    start_btn = tk.Button(menu, text="Start screen look", bg="#27ae60", fg="white", bd=0, font=("Segoe UI", 18, "bold"),
                          command=lambda: start_look())
    start_btn.pack(ipadx=30, ipady=12)
    tk.Button(menu, text="Check for phone again", bg=MAIN_BG, fg="#9bd1ff", bd=0, command=lambda: check_phone()).pack(pady=14)

    modebar = tk.Frame(menu, bg=MAIN_BG)
    modebar.place(relx=1.0, x=-12, y=10, anchor="ne")  # top corner: pick Android or Apple
    mode_btns = {}
    for m, label in (("android", "Android"), ("apple", "Apple (iPhone / iPad)")):
        mode_btns[m] = tk.Button(modebar, text=label, bd=0, fg="white", font=("Segoe UI", 10, "bold"),
                                 command=lambda m=m: set_mode(m))
        mode_btns[m].pack(side="left", padx=2, ipadx=8, ipady=3)

    def style_modes():
        for k, b in mode_btns.items():
            b.config(bg="#27ae60" if k == st["mode"] else "#1d2b4d")

    def set_mode(m):
        st["mode"] = m
        style_modes()
        check_phone()

    style_modes()

    def check_apple():
        if importlib.util.find_spec("pymobiledevice3") is None:
            status.config(text="The Apple tool installs when you press Start.")
            return
        status.config(text="Looking for an iPhone/iPad...")

        def work():
            try:
                ds = apple_devices()
            except Exception as e:
                ui_q.put(("status", f"Couldn't check Apple devices: {str(e)[:80]}"))
                return
            if ds:
                ui_q.put(("status", f"Apple device connected: {ds[0][1] or ds[0][0]}"))
            else:
                ui_q.put(("status", "No iPhone/iPad found. Plug it in and tap Trust."))

        threading.Thread(target=work, daemon=True).start()

    def check_phone():
        if st["mode"] == "apple":
            return check_apple()
        if not ADB:
            status.config(text="adb not found yet (press Start for help)")
            return
        status.config(text="Looking for a phone...")

        def work():
            try:
                ds = devices()
            except Exception:
                ui_q.put(("status", "Couldn't talk to adb."))
                return
            ok = [d for d in ds if d[1] == "device"]
            if ok:
                model = adb("shell", "getprop", "ro.product.model", serial=ok[0][0]).strip() or ok[0][0]
                ui_q.put(("status", f"Phone connected: {model}"))
            elif any(d[1] == "unauthorized" for d in ds):
                ui_q.put(("status", "Phone found. Tap Allow on the phone screen."))
            else:
                ui_q.put(("status", "No phone found. Plug it in with USB."))

        threading.Thread(target=work, daemon=True).start()

    # ---- viewer
    top = tk.Frame(view, bg=MAIN_BG)
    top.pack(fill="x", padx=12, pady=8)
    dev_l = tk.Label(top, text="", bg=MAIN_BG, fg="white", font=("Segoe UI", 12, "bold"))
    dev_l.pack(side="left")
    tk.Button(top, text="Stop screen look", bg="#d9423a", fg="white", bd=0, font=("Segoe UI", 10, "bold"),
              command=lambda: stop_look()).pack(side="right", ipadx=8, ipady=3)
    sys_var = tk.BooleanVar(value=False)
    tk.Checkbutton(top, text="Show system apps", variable=sys_var, bg=MAIN_BG, fg="white", selectcolor="#1d2b4d",
                   activebackground=MAIN_BG, activeforeground="white", command=lambda: load_apps()).pack(side="right", padx=10)
    screen_l = tk.Label(view, bg="black", fg="white", text="Waiting for the phone screen...", width=30)
    screen_l.pack(side="left", padx=12, pady=(0, 12), anchor="n")
    right = tk.Frame(view, bg=MAIN_BG)
    right.pack(side="left", fill="both", expand=True, padx=(0, 12), pady=(0, 12))
    tk.Label(right, text="Apps on the phone (scroll here, the phone stays put)", bg=MAIN_BG, fg="#9bd1ff",
             anchor="w").pack(fill="x")
    sb = tk.Scrollbar(right)
    lb = tk.Listbox(right, yscrollcommand=sb.set, bg="#1d2b4d", fg="white", bd=0, highlightthickness=0,
                    font=("Consolas", 10), activestyle="none")
    sb.config(command=lb.yview)
    sb.pack(side="right", fill="y")
    lb.pack(side="left", fill="both", expand=True)
    imgref = {}

    def load_apps():
        serial = st["serial"]

        def work():
            try:
                if st["mode"] == "apple":
                    ui_q.put(("apps", apple_running(serial), apple_apps(serial, sys_var.get())))
                    return
                ui_q.put(("apps", recent_apps(serial), installed_apps(serial, sys_var.get())))
            except Exception as e:
                ui_q.put(("status_view", f"Couldn't read apps: {e}"))

        threading.Thread(target=work, daemon=True).start()

    def screen_loop(serial):
        while st["look"] and st["serial"] == serial:
            try:
                png = adb("exec-out", "screencap", "-p", serial=serial, raw=True, timeout=8)
                if png[:4] == b"\x89PNG":
                    ui_q.put(("img", png))
            except Exception:
                ui_q.put(("status_view", "Lost the phone. Plug it back in."))
                time.sleep(1.5)
            time.sleep(0.3)

    def apple_screen_loop(udid):
        warned = False
        while st["look"] and st["serial"] == udid:
            try:
                ui_q.put(("img", apple_screenshot(udid)))
                warned = False
                time.sleep(0.5)
            except Exception as e:
                if not warned:
                    ui_q.put(("note", "No live screen picture yet.\n\n" + APPLE_SCREEN_HELP + "\n\n(" + str(e)[:140] + ")"))
                    warned = True
                time.sleep(4)

    def start_apple():
        if importlib.util.find_spec("pymobiledevice3") is None:
            status.config(text="Installing the Apple tool (about a minute)...")

            def inst():
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymobiledevice3"], creationflags=NO_WINDOW)
                    ui_q.put(("go_start",))
                except Exception:
                    ui_q.put(("status", "Couldn't install it. In Command Prompt run: py -m pip install pymobiledevice3"))

            threading.Thread(target=inst, daemon=True).start()
            return
        try:
            ds = apple_devices()
        except Exception as e:
            messagebox.showerror("Screen Looking", f"Couldn't talk to the Apple tool:\n{e}\n\n" + APPLE_HELP)
            return
        if not ds:
            messagebox.showinfo("Screen Looking", "No iPhone or iPad found.\n\n" + APPLE_HELP)
            return
        st["serial"], st["look"] = ds[0][0], True
        dev_l.config(text=f"Looking at: {ds[0][1] or ds[0][0]}   (view only)")
        menu.pack_forget()
        root.geometry("960x640")
        view.pack(fill="both", expand=True)
        threading.Thread(target=apple_screen_loop, args=(st["serial"],), daemon=True).start()
        load_apps()

    def fill_apps(bg, inst):
        lb.delete(0, "end")

        def header(text):
            lb.insert("end", text)
            lb.itemconfig(lb.size() - 1, fg="#7ee8ff")

        header(f"RUNNING / RECENT ({len(bg)})")
        for p in bg or ["(the phone did not share any)"]:
            lb.insert("end", "  " + p)
        lb.insert("end", "")
        header(f"INSTALLED APPS ({len(inst)})")
        for p in inst:
            lb.insert("end", "  " + p)

    def pump():
        try:
            while True:
                item = ui_q.get_nowait()
                kind = item[0]
                if kind == "status":
                    status.config(text=item[1])
                elif kind == "status_view":
                    dev_l.config(text=item[1])
                elif kind == "go_start":
                    importlib.invalidate_caches()
                    start_look()
                elif kind == "note" and st["look"]:
                    screen_l.config(image="", text=item[1], width=40, height=18, justify="left", wraplength=320)
                elif kind == "apps" and st["look"]:
                    fill_apps(item[1], item[2])
                elif kind == "img" and st["look"]:
                    img = tk.PhotoImage(data=base64.b64encode(item[1]))
                    f = max(1, math.ceil(img.height() / 520))
                    img = img.subsample(f) if f > 1 else img
                    imgref["i"] = img
                    screen_l.config(image=img, text="", width=img.width(), height=img.height())
        except queue.Empty:
            pass
        root.after(100, pump)

    def start_look():
        if st["mode"] == "apple":
            return start_apple()
        if not ADB:
            messagebox.showinfo("One-time setup", ADB_HELP)
            return
        try:
            ds = devices()
        except Exception as e:
            messagebox.showerror("Screen Looking", f"Couldn't run adb:\n{e}")
            return
        ok = [d for d in ds if d[1] == "device"]
        if not ok:
            if any(d[1] == "unauthorized" for d in ds):
                messagebox.showinfo("Screen Looking", "Look at your phone and tap Allow on the USB debugging popup. Then press Start again.")
            else:
                messagebox.showinfo("Screen Looking", "No phone found.\n\n" + ADB_HELP)
            return
        st["serial"], st["look"] = ok[0][0], True
        model = adb("shell", "getprop", "ro.product.model", serial=st["serial"]).strip() or st["serial"]
        dev_l.config(text=f"Looking at: {model}   (view only)")
        menu.pack_forget()
        root.geometry("960x640")
        view.pack(fill="both", expand=True)
        threading.Thread(target=screen_loop, args=(st["serial"],), daemon=True).start()
        load_apps()

    def stop_look():
        st["look"] = False
        view.pack_forget()
        root.geometry(f"{W}x{H}")
        screen_l.config(image="", text="Waiting for the phone screen...", width=30, height=0)
        menu.pack(fill="both", expand=True)
        check_phone()

    root.protocol("WM_DELETE_WINDOW", lambda: (st.update(look=False, intro=False), root.destroy()))
    pump()
    intro_step()
    root.mainloop()


if __name__ == "__main__":
    main()
