#!/usr/bin/env python3
"""
GDSapache3 Final — updated to ask sudo password once at startup,
and show Apache3 status with colored status bar.
"""

import os
import subprocess
import webbrowser
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox

# Try to use sv-ttk for modern dark theme, fall back if missing
try:
    import sv_ttk
    SVTTK = True
except Exception:
    SVTTK = False

APP_TITLE = "GDS Apache3 Control Panel"
rules = []
SUDO_PW = None

# ---------------- sudo helpers ----------------
def ask_sudo_password_startup():
    """Ask for sudo password before GUI loads."""
    global SUDO_PW
    pw_ans = {"pw": None}

    root_pw = tk.Tk()
    root_pw.title("Sudo Password Required")
    root_pw.geometry("360x120")
    root_pw.resizable(False, False)
    if SVTTK:
        sv_ttk.set_theme("dark")

    ttk.Label(root_pw, text="Enter your sudo password:").pack(pady=(12,6))
    entry = ttk.Entry(root_pw, show="*", width=40)
    entry.pack(padx=12)
    entry.focus_set()

    def submit(event=None):
        val = entry.get()
        if not val:
            messagebox.showerror("Error", "Password cannot be empty.", parent=root_pw)
            return
        try:
            proc = subprocess.run(
                ["sudo", "-S", "-k", "true"],
                input=val + "\n",
                text=True,
                capture_output=True
            )
            if proc.returncode == 0:
                pw_ans["pw"] = val
                root_pw.destroy()
            else:
                messagebox.showerror("Error", "Incorrect password. Try again.", parent=root_pw)
                entry.delete(0, tk.END)
                entry.focus_set()
        except Exception as e:
            messagebox.showerror("Error", f"Sudo check failed: {e}", parent=root_pw)
            root_pw.destroy()

    entry.bind("<Return>", submit)
    enter_btn = ttk.Button(root_pw, text="Enter", command=submit)
    enter_btn.pack(pady=8)
    root_pw.bind("<Return>", lambda event: enter_btn.invoke())

    root_pw.mainloop()
    if pw_ans["pw"]:
        SUDO_PW = pw_ans["pw"]
    else:
        raise SystemExit("Sudo password required to run this script.")

def get_sudo_password():
    global SUDO_PW
    return SUDO_PW

def which(cmd):
    for p in os.getenv("PATH", "").split(os.pathsep):
        full = os.path.join(p, cmd)
        if os.path.isfile(full) and os.access(full, os.X_OK):
            return full
    return None

def append_output(text):
    output_text.insert(tk.END, text + "\n")
    output_text.see(tk.END)

def sudo_systemctl(action_list):
    pw = get_sudo_password()
    if pw is None:
        append_output("Sudo password not provided; action cancelled.")
        return None, None, None
    cmd = ["sudo", "-S", "systemctl"] + action_list
    try:
        proc = subprocess.run(cmd, input=pw + "\n", capture_output=True, text=True)
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except Exception as e:
        return -4, "", str(e)

def sudo_popen(cmd_list):
    pw = get_sudo_password()
    if pw is None:
        raise RuntimeError("Sudo password not provided")
    full = ["sudo", "-S"] + cmd_list
    proc = subprocess.Popen(full, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        proc.stdin.write(pw + "\n")
        proc.stdin.flush()
    except Exception:
        pass
    return proc

# ---------------- core ----------------
def add_rule():
    listen = listen_port.get().strip()
    host = target_host.get().strip()
    port = target_port.get().strip()
    if not (listen and host and port):
        messagebox.showerror("Add Rule", "Please fill Listen Port, Target Host and Target Port.")
        return
    for r in rules:
        if r["listen"] == listen and r["host"] == host and r["port"] == port:
            messagebox.showinfo("Add Rule", "Rule already exists.")
            return
    rules.append({"listen": listen, "host": host, "port": port, "active": False, "proc": None})
    refresh_table()
    status_var.set(f"Added rule: {listen} -> {host}:{port}")
    append_output(f"Added rule: {listen} -> {host}:{port}")

def activate_rule(index):
    if index < 0 or index >= len(rules):
        return
    r = rules[index]
    if r["active"]:
        proc = r.get("proc")
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=1)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        r["proc"] = None
        r["active"] = False
        refresh_table()
        status_var.set(f"Stopped forwarding {r['listen']}")
        append_output(f"Stopped forwarding {r['listen']} -> {r['host']}:{r['port']}")
        return
    for o in rules:
        o["active"] = False
    socat = which("socat")
    if socat:
        listen = r["listen"]; host = r["host"]; port = r["port"]
        cmd = [socat, f"TCP-LISTEN:{listen},reuseaddr,fork", f"TCP:{host}:{port}"]
        try:
            if int(listen) < 1024 and which("sudo"):
                proc = sudo_popen(cmd)
            else:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            r["proc"] = proc
            r["active"] = True
            refresh_table()
            status_var.set(f"Forwarding {listen} -> {host}:{port}")
            append_output(f"Started socat: {listen} -> {host}:{port}")
            return
        except Exception as e:
            append_output(f"socat start failed: {e}")
    r["active"] = True
    r["proc"] = None
    refresh_table()
    status_var.set(f"Activated (no socat) {r['listen']}")
    append_output(f"Activated rule (no socat): {r['listen']} -> {r['host']}:{r['port']}")

def remove_rule(index):
    if index < 0 or index >= len(rules):
        append_output(f"Remove failed: invalid index {index}")
        return
    r = rules[index]
    # Stop active forwarding process if running
    if r.get("active") and r.get("proc"):
        proc = r["proc"]
        try:
            proc.terminate()
            proc.wait(timeout=1)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        r["proc"] = None
        r["active"] = False
        append_output(f"Stopped forwarding before removing rule {r['listen']}")
    # Remove the rule
    removed = rules.pop(index)
    refresh_table()
    status_var.set(f"Removed rule: {removed['listen']} -> {removed['host']}:{removed['port']}")
    append_output(f"Removed rule: {removed['listen']} -> {removed['host']}:{removed['port']}")

def open_rule(index):
    if index < 0 or index >= len(rules):
        return
    r = rules[index]
    url = f"http://localhost:{r['listen']}"
    try:
        webbrowser.open(url)
        status_var.set(f"Opened {url}")
        append_output(f"Opened {url}")
    except Exception as e:
        messagebox.showerror("Open", str(e))

def refresh_table():
    tree.delete(*tree.get_children())
    for i, r in enumerate(rules):
        status_text = "● Active" if r["active"] else "○ Inactive"
        act_text = "Deactivate" if r["active"] else "Activate"
        tree.insert("", "end", iid=str(i), values=(
            r["listen"], r["host"], r["port"], status_text, act_text, "Open", "Remove"
        ))

def start_apache():
    rc, out, err = sudo_systemctl(["start", "apache2"])
    if rc is None:
        return
    append_output(out or err or f"start returned {rc}")
    if rc == 0:
        status_var.set("Apache3 started")
        status_bar.config(bg="green", fg="white")
    else:
        status_var.set("Apache3 start error")
        status_bar.config(bg="red", fg="white")

def stop_apache():
    rc, out, err = sudo_systemctl(["stop", "apache2"])
    if rc is None:
        return
    append_output(out or err or f"stop returned {rc}")
    if rc == 0:
        status_var.set("Apache3 stopped")
        status_bar.config(bg="red", fg="white")
    else:
        status_var.set("Apache3 stop error")
        status_bar.config(bg="red", fg="white")

def check_apache():
    rc, out, err = sudo_systemctl(["is-active", "apache2"])
    if rc is None:
        return
    status = (out or err or "").strip().lower()

    if status == "active":
        status_var.set("Apache3 Status: Running")
        status_bar.config(bg="green", fg="white")
    elif status == "inactive":
        status_var.set("Apache3 Status: Disabled")
        status_bar.config(bg="orange", fg="black")
    else:
        status_var.set(f"Apache3 Status: {status.capitalize()}")
        status_bar.config(bg="red", fg="white")

    append_output(out or err or f"Status check returned {rc}")

def add_html_popup():
    editor = tk.Toplevel(root)
    editor.title("Add HTML")
    editor.geometry("700x500")
    editor.transient(root)
    editor.grab_set()
    frm = ttk.Frame(editor, padding=(8,8))
    frm.pack(fill="x")
    ttk.Label(frm, text="Filename (example: index.html):").pack(anchor="w")
    filename_var = tk.StringVar(value="index.html")
    filename_entry = ttk.Entry(frm, textvariable=filename_var)
    filename_entry.pack(fill="x", pady=(2,6))
    ttk.Label(frm, text="Target directory (default /var/www/html):").pack(anchor="w")
    target_dir_var = tk.StringVar(value="/var/www/html")
    target_dir_entry = ttk.Entry(frm, textvariable=target_dir_var)
    target_dir_entry.pack(fill="x", pady=(2,6))
    def choose_dir():
        d = filedialog.askdirectory(parent=editor, title="Choose directory")
        if d:
            target_dir_var.set(d)
    ttk.Button(frm, text="Choose directory...", command=choose_dir).pack(anchor="e", pady=(0,6))
    ttk.Label(editor, text="HTML Content:").pack(anchor="w", padx=8)
    html_text = scrolledtext.ScrolledText(editor, wrap=tk.WORD, height=20)
    html_text.pack(fill="both", expand=True, padx=8, pady=(2,8))
    default_template = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>New Page</title></head>
<body><h1>Hello from GDSapache3</h1><p>Sample page.</p></body>
</html>
"""
    html_text.insert("1.0", default_template)
    def save_html():
        fname = filename_var.get().strip()
        tdir = target_dir_var.get().strip() or "/var/www/html"
        if not fname:
            messagebox.showerror("Error", "Please provide a filename.")
            return
        try:
            os.makedirs(tdir, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot create target directory:\n{e}")
            return
        fullpath = os.path.join(tdir, fname)
        content = html_text.get("1.0", tk.END)
        try:
            with open(fullpath, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Saved", f"Saved HTML to:\n{fullpath}")
            append_output(f"Saved HTML -> {fullpath}")
            editor.destroy()
        except PermissionError:
            messagebox.showerror("Error", "Permission denied.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file:\n{e}")
    btn_frame = ttk.Frame(editor)
    btn_frame.pack(fill="x", pady=6, padx=8)
    ttk.Button(btn_frame, text="Save", command=save_html).pack(side="right", padx=4)
    ttk.Button(btn_frame, text="Cancel", command=editor.destroy).pack(side="right", padx=4)

# ---------------- UI ----------------
ask_sudo_password_startup()  # <<< Ask sudo password before GUI

root = tk.Tk()
root.title(APP_TITLE)
root.geometry("900x600")
root.minsize(900, 600)
root.maxsize(900, 600)
if SVTTK:
    sv_ttk.set_theme("dark")
else:
    root.configure(bg="#1e1e1e")

title_frame = ttk.Frame(root, padding=(8,6))
title_frame.pack(fill="x")
ttk.Label(title_frame, text=APP_TITLE, anchor="center", font=("Segoe UI", 16, "bold")).pack()

controls_outer = ttk.Frame(root, padding=8)
controls_outer.pack(fill="x")

left_ctrl = ttk.Frame(controls_outer)
left_ctrl.pack(side="left", fill="both", expand=True, padx=(0,8))

right_ctrl = ttk.Frame(controls_outer)
right_ctrl.pack(side="right", fill="y")

ttk.Label(left_ctrl, text="Listen Port:").grid(row=0, column=0, sticky="w", pady=2)
listen_port = ttk.Combobox(left_ctrl, values=["80","443","8080","9000"], width=20)
listen_port.set("80")
listen_port.grid(row=0, column=1, sticky="w", padx=6, pady=2)

ttk.Label(left_ctrl, text="Target Host:").grid(row=1, column=0, sticky="w", pady=2)
target_host = ttk.Combobox(left_ctrl, values=["127.0.0.1","192.168.1.10","localhost"], width=20)
target_host.set("127.0.0.1")
target_host.grid(row=1, column=1, sticky="w", padx=6, pady=2)

ttk.Label(left_ctrl, text="Target Port:").grid(row=2, column=0, sticky="w", pady=2)
target_port = ttk.Combobox(left_ctrl, values=["80","443","8080","9000"], width=20)
target_port.set("80")
target_port.grid(row=2, column=1, sticky="w", padx=6, pady=2)

ttk.Button(left_ctrl, text="Add Rule", command=add_rule).grid(row=3, column=0, columnspan=2, pady=(8,0))

ttk.Button(right_ctrl, text="Start Apache3", command=start_apache).pack(fill="x", pady=4)
ttk.Button(right_ctrl, text="Stop Apache3", command=stop_apache).pack(fill="x", pady=4)
ttk.Button(right_ctrl, text="Check Apache3 Status", command=check_apache).pack(fill="x", pady=4)
ttk.Button(right_ctrl, text="Add HTML", command=add_html_popup).pack(fill="x", pady=4)

cols = ("Listen","Target Host","Target Port","Status","Activate","Open","Remove")
table_frame = ttk.Frame(root, padding=(8,8))
table_frame.pack(fill="both", padx=12, pady=(0,6), expand=False)
tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=3)
for c in cols:
    tree.heading(c, text=c)
    if c == "Target Host":
        tree.column(c, width=250, anchor="w")
    elif c in ("Activate","Open","Remove"):
        tree.column(c, width=90, anchor="center")
    else:
        tree.column(c, width=90, anchor="center")
vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=vsb.set)
vsb.pack(side="right", fill="y")
tree.pack(fill="both", expand=True)

def on_table_click(event):
    item = tree.identify_row(event.y)
    col = tree.identify_column(event.x)
    if not item:
        return
    try:
        index = int(item)
    except ValueError:
        index = tree.index(item)
    # Sanity check for index bounds
    if index < 0 or index >= len(rules):
        append_output(f"Clicked invalid rule index: {index}")
        return
    if col == "#5":  # Activate/Deactivate column
        activate_rule(index)
    elif col == "#6":  # Open column
        open_rule(index)
    elif col == "#7":  # Remove column
        remove_rule(index)
tree.bind("<Button-1>", on_table_click)

ttk.Label(root, text="Apache Output Log:").pack(anchor="w", padx=12)
output_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=8)
output_text.pack(fill="both", padx=12, pady=(4,8))

status_var = tk.StringVar(value="Status: No active forwarding")
status_bar = tk.Label(root, textvariable=status_var, anchor="w", relief="sunken", bg="red", fg="white")
status_bar.pack(fill="x", side="bottom")

rules.append({"listen":"80","host":"127.0.0.1","port":"80","active":True,"proc":None})
rules.append({"listen":"8080","host":"example.com","port":"443","active":False,"proc":None})
rules.append({"listen":"9000","host":"localhost","port":"22","active":True,"proc":None})
refresh_table()

root.mainloop()
