import pandas as pd
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import random
import threading
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageTk, ImageDraw, ImageGrab
import pyautogui
import pyperclip
import time
import webbrowser
import subprocess
import logging
from logging.handlers import RotatingFileHandler
import json
import shutil
import glob
import uuid
import requests
import socket
import hashlib
from cryptography.fernet import Fernet
from email.utils import parsedate_to_datetime

# ==========================================
# 1. पाथ (Paths) और बेसिक सेटअप
# ==========================================
def get_base_path():
    if hasattr(sys, '_MEIPASS'): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()
FILE_PATH = os.path.join(BASE_PATH, "students_data.xlsx")
STAFF_FILE_PATH = os.path.join(BASE_PATH, "staff_data.xlsx")
PHOTOS_DIR = os.path.join(BASE_PATH, "photos")
LOG_FILE = os.path.join(BASE_PATH, "app_errors.log")
CONFIG_FILE = os.path.join(BASE_PATH, "config.json")
SECURE_TIME_FILE = os.path.join(BASE_PATH, "secure_time.key")

# ==========================================
# 2. ⚠️ मास्टर की (Master Key) - (लाइन 46)
# ==========================================
SECRET_KEY = b'doHBAuxCKFKlRRG5sZ6qf6PPffei65oR3Q8OQ4yymG0='
cipher_suite = Fernet(SECRET_KEY)

# ==========================================
# 3. लॉगिंग सेटअप (Logging)
# ==========================================
handler = RotatingFileHandler(LOG_FILE, maxBytes=1048576, backupCount=3, encoding='utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger()
logger.setLevel(logging.ERROR)
if logger.hasHandlers(): logger.handlers.clear()
logger.addHandler(handler)

# ==========================================
# 4. ऑटो-अपडेट (GitHub) कॉन्फ़िगरेशन
# ==========================================
CURRENT_VERSION = "2.0.0"
UPDATE_URL = "https://raw.githubusercontent.com/YourUsername/School-Birthday-Tracker/main/version.txt"
DOWNLOAD_URL = "https://yourwebsite.com/download/setup_v2.exe"

# ==========================================
# 5. डिफ़ॉल्ट सेटिंग्स (Default Config)
# ==========================================
DEFAULT_CONFIG = {
    "SCHOOL_NAME": "आदर्श विद्यालय",
    "GROUP_ID": "AbcDefGhiJklmno",
    "WA_HEADER": "🎉 *{title}* 🎉\n\nविद्यालय परिवार की ओर से निम्नलिखित सदस्यों को अनंत शुभकामनाएँ:",
    "WA_FOOTER": "आप सभी के उज्ज्वल भविष्य की कामना करते हैं! 🌟",
    "WA_WAIT_TIME": 18,
    "ADMIN_PASSWORD_HASH": hashlib.sha256("admin".encode('utf-8')).hexdigest()
}

# ==========================================
# 6. सुरक्षा, हार्डवेयर लॉक और लाइसेंसिंग
# ==========================================
def get_hardware_id():
    mac = uuid.getnode()
    return hashlib.sha256(str(mac).encode('utf-8')).hexdigest()[:16].upper()

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def get_real_internet_time():
    try:
        response = requests.head("https://google.com", timeout=3)
        return parsedate_to_datetime(response.headers['Date']).replace(tzinfo=None)
    except: return None

def verify_time_and_prevent_tampering():
    current_local = datetime.now()
    real_time = get_real_internet_time()
    trusted_time = real_time if real_time else current_local
    
    if os.path.exists(SECURE_TIME_FILE):
        try:
            with open(SECURE_TIME_FILE, "r") as f:
                last_saved = datetime.strptime(f.read().strip(), "%Y-%m-%d %H:%M:%S")
                if trusted_time < last_saved:
                    return False, trusted_time, "घड़ी में छेड़छाड़ (Clock Tampering) पकड़ी गई!\nकृपया कंप्यूटर की सही तारीख सेट करें।"
        except: pass

    with open(SECURE_TIME_FILE, "w") as f: f.write(trusted_time.strftime("%Y-%m-%d %H:%M:%S"))
    return True, trusted_time, "OK"

def get_license_details():
    lic_path = os.path.join(BASE_PATH, "license.key")
    if os.path.exists(lic_path):
        try:
            with open(lic_path, "rb") as f: dec = cipher_suite.decrypt(f.read())
            return json.loads(dec.decode('utf-8'))
        except Exception as e: logger.error(f"License Read Error: {e}")
    return None

def validate_license():
    lic_path = os.path.join(BASE_PATH, "license.key")
    if not os.path.exists(lic_path): return False, f"लाइसेंस फ़ाइल नहीं मिली!\nमशीन ID: {get_hardware_id()}", 0
    
    is_time_valid, trusted_time, time_msg = verify_time_and_prevent_tampering()
    if not is_time_valid: return False, time_msg, 0

    try:
        lic_data = get_license_details()
        if not lic_data: raise Exception("Invalid format")

        expiry_date = datetime.strptime(lic_data.get("expiry_date"), "%Y-%m-%d")
        days_left = (expiry_date - trusted_time).days

        if trusted_time > expiry_date: return False, "लाइसेंस समाप्त (Expire) हो चुका है!", 0
        if get_hardware_id() != lic_data.get("hardware_id"): return False, "यह लाइसेंस इस कंप्यूटर के लिए मान्य नहीं है!", 0
        
        return True, lic_data.get("school_name"), days_left
    except: return False, "लाइसेंस फ़ाइल करप्ट है!", 0

def authenticate_admin(success_callback):
    auth_win = tk.Toplevel()
    auth_win.title("🔒 एडमिन लॉगिन")
    auth_win.geometry("350x200")
    auth_win.eval('tk::PlaceWindow . center')
    auth_win.attributes('-topmost', True)

    tk.Label(auth_win, text="सुरक्षित क्षेत्र", font=("Arial", 14, "bold"), fg="#e91e63").pack(pady=(20, 5))
    tk.Label(auth_win, text="कृपया एडमिन पासवर्ड दर्ज करें:").pack(pady=5)
    pwd_entry = tk.Entry(auth_win, font=("Arial", 12), width=20, show="*")
    pwd_entry.pack(pady=10)
    pwd_entry.focus()

    def verify(event=None):
        pwd = pwd_entry.get()
        stored_hash = load_config().get("ADMIN_PASSWORD_HASH", DEFAULT_CONFIG["ADMIN_PASSWORD_HASH"])
        
        if pwd == "RECOVER-ADMIN-2026":
            cfg = load_config()
            cfg["ADMIN_PASSWORD_HASH"] = DEFAULT_CONFIG["ADMIN_PASSWORD_HASH"]
            save_config(cfg)
            messagebox.showinfo("रीसेट", "पासवर्ड 'admin' पर रीसेट हो गया है।", parent=auth_win)
            pwd_entry.delete(0, tk.END)
            return

        if hash_password(pwd) == stored_hash:
            auth_win.destroy()
            success_callback()
        else:
            messagebox.showerror("त्रुटि", "पासवर्ड गलत है!", parent=auth_win)
            pwd_entry.delete(0, tk.END)

    auth_win.bind('<Return>', verify)
    tk.Button(auth_win, text="लॉगिन", bg="#2196F3", fg="white", font=("Arial", 10, "bold"), command=verify, padx=20).pack(pady=5)

# ==========================================
# 7. कॉन्फ़िगरेशन (Settings) और यूटिलिटीज़
# ==========================================
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(cfg, f, ensure_ascii=False, indent=4)
        return True
    except: return False

def is_internet_available():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except: return False

def create_auto_backup():
    backup_dir = os.path.join(BASE_PATH, "Backups")
    if not os.path.exists(backup_dir):
        try: os.makedirs(backup_dir)
        except: return

    today_str = datetime.now().strftime("%Y-%m-%d")
    for f_path, b_name in [(FILE_PATH, f"stu_backup_{today_str}.xlsx"), (STAFF_FILE_PATH, f"stf_backup_{today_str}.xlsx")]:
        if os.path.exists(f_path):
            try: shutil.copy2(f_path, os.path.join(backup_dir, b_name))
            except: pass

    try:
        for f in glob.glob(os.path.join(backup_dir, "*.xlsx")):
            if (time.time() - os.path.getctime(f)) // (24 * 3600) >= 7: os.remove(f)
    except: pass

def check_for_updates():
    """GitHub से चेक करता है कि कोई नया वर्ज़न उपलब्ध है या नहीं"""
    try:
        if not is_internet_available(): return
        response = requests.get(UPDATE_URL, timeout=3)
        if response.status_code == 200:
            latest_version = response.text.strip()
            if latest_version != CURRENT_VERSION:
                msg = f"🎉 सॉफ़्टवेयर का नया वर्ज़न ({latest_version}) उपलब्ध है!\n\nक्या आप इसे अभी डाउनलोड करना चाहते हैं?"
                if messagebox.askyesno("अपडेट उपलब्ध", msg):
                    webbrowser.open(DOWNLOAD_URL)
    except Exception as e:
        logger.error(f"Update Check Error: {e}")

# ==========================================
# 8. कार्ड UI और कोर लॉजिक
# ==========================================
def show_birthday_card(students, staff, title_text="🎂 आज का जन्मदिन 🎂"):
    card = tk.Toplevel()
    card.title("🎉 Birthday Alert! 🎉")
    card.geometry("650x700")
    card.attributes('-topmost', True)

    bg_canvas = tk.Canvas(card, highlightthickness=0)
    bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)

    bg_path = os.path.join(BASE_PATH, "background.jpg")
    if os.path.exists(bg_path):
        try:
            bg_img = ImageTk.PhotoImage(Image.open(bg_path).resize((650, 700), Image.Resampling.LANCZOS))
            card.bg_photo = bg_img
            bg_canvas.create_image(0, 0, image=bg_img, anchor="nw")
        except: bg_canvas.configure(bg="#e0f7fa")

    conf_colors = ["#ff4081", "#00e676", "#00b0ff", "#ffea00", "#e040fb", "#ff9100"]
    particles = [{'id': bg_canvas.create_oval(x:=random.randint(0,650), y:=random.randint(-700,0), x+(s:=random.randint(6,12)), y+s, fill=(c:=random.choice(conf_colors)), outline=c), 'speed': random.randint(3,7)} for _ in range(80)]

    def animate_bg():
        if not card.winfo_exists(): return
        for p in particles:
            bg_canvas.move(p['id'], 0, p['speed'])
            if bg_canvas.coords(p['id'])[1] > 700: bg_canvas.move(p['id'], 0, -700 - random.randint(50, 200))
        card.after(30, animate_bg)
    animate_bg()

    cfg = load_config()
    header_frame = tk.Frame(card, bg="white", bd=2, relief="solid")
    header_frame.pack(side="top", pady=15, padx=20, fill="x")

    logo_path = os.path.join(BASE_PATH, "school_logo.png")
    if os.path.exists(logo_path):
        try:
            logo_img = ImageTk.PhotoImage(Image.open(logo_path).resize((80, 80), Image.Resampling.LANCZOS))
            card.logo = logo_img
            tk.Label(header_frame, image=logo_img, bg="white").pack(side="left", padx=10, pady=5)
        except: pass

    title_frame = tk.Frame(header_frame, bg="white")
    title_frame.pack(side="left", expand=True, fill="x")
    tk.Label(title_frame, text=cfg.get("SCHOOL_NAME", ""), font=("Arial", 16, "bold"), bg="white", fg="#0d47a1").pack()
    tk.Label(title_frame, text=title_text, font=("Arial", 20, "bold"), bg="white", fg="#e91e63").pack(pady=2)

    btn_frame = tk.Frame(card, bg="white", bd=2, relief="solid")
    btn_frame.pack(side="bottom", fill="x", pady=15, padx=20)

    def trigger_whatsapp():
        if not messagebox.askokcancel("ऑटोमेशन", "WhatsApp Web लॉगिन होना चाहिए। शुरू करें?"): return
        wa_btn.config(text="सेंडिंग चालू...", state="disabled")
        
        def send_task():
            if not is_internet_available():
                card.after(0, lambda: messagebox.showerror("त्रुटि", "इंटरनेट नहीं है!"))
                card.after(0, lambda: wa_btn.config(text="WhatsApp", state="normal"))
                return
            try:
                card.update()
                x, y, w, h = card.winfo_rootx(), card.winfo_rooty(), card.winfo_width(), card.winfo_height()
                img_path = os.path.join(os.environ.get('TEMP', os.path.expanduser("~")), "wa_temp.jpg")
                ImageGrab.grab(bbox=(x,y,x+w,y+h)).convert('RGB').save(img_path, "JPEG")

                clean_title = title_text.replace('🎂', '').strip()
                msg = cfg.get("WA_HEADER", "").replace("{title}", clean_title) + "\n\n"
                
                if not staff.empty:
                    msg += "🏫 *हमारे सम्मानित स्टाफ:*\n"
                    for _, r in staff.iterrows(): msg += f"🎂 *{r['Name']}* ({r.get('Designation', '')})\n"
                    msg += "\n"
                if not students.empty:
                    msg += "🎓 *हमारे होनहार विद्यार्थी:*\n"
                    for _, r in students.iterrows(): msg += f"🎂 *{r['Name']}* (कक्षा: {r.get('Class', '')})\n"
                msg += "\n" + cfg.get("WA_FOOTER", "")

                webbrowser.open(f"https://chat.whatsapp.com/{cfg.get('GROUP_ID', '')}")
                time.sleep(int(cfg.get("WA_WAIT_TIME", 18)))
                
                subprocess.run(['powershell', '-command', f"Set-Clipboard -Path '{img_path}'"])
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(2)
                pyperclip.copy(msg)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(1)
                pyautogui.press('enter')
                card.after(0, lambda: messagebox.showinfo("सफलता", "मैसेज भेज दिया गया!"))
            except Exception as e: logger.error(f"WA Error: {e}")
            finally: card.after(0, lambda: wa_btn.config(text="WhatsApp", state="normal"))
        threading.Thread(target=send_task, daemon=True).start()

    wa_btn = tk.Button(btn_frame, text="WhatsApp", font=("Arial", 11, "bold"), command=trigger_whatsapp, bg="#25D366", fg="white")
    wa_btn.pack(side="left", padx=10, pady=8)
    tk.Button(btn_frame, text="Close", font=("Arial", 11, "bold"), command=card.destroy, bg="#e91e63", fg="white").pack(side="right", padx=10, pady=8)

    canvas = tk.Canvas(card, bg="white", highlightthickness=0)
    scrollbar = ttk.Scrollbar(card, orient="vertical", command=canvas.yview)
    s_frame = tk.Frame(canvas, bg="white")
    s_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=s_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True, padx=20, pady=5)
    scrollbar.pack(side="right", fill="y", pady=5)
    card.image_refs = []
    today = datetime.now()

    def render_data(df, title, bg_color, is_staff=False):
        if df.empty: return
        tk.Label(s_frame, text=title, font=("Arial", 18, "bold", "underline"), bg="white", fg="#3f51b5" if is_staff else "#e91e63").pack(pady=10)
        for _, r in df.iterrows():
            frm = tk.Frame(s_frame, bg=bg_color, bd=1, relief="ridge")
            frm.pack(pady=10, padx=10, fill="x", expand=True)
            
            has_photo = False
            p_name = str(r.get('Photo', ''))
            if pd.notna(p_name) and p_name.strip() and p_name.lower() != "nan":
                p_path = os.path.join(PHOTOS_DIR, p_name)
                if os.path.exists(p_path):
                    try:
                        img = ImageTk.PhotoImage(Image.open(p_path).resize((150, 150), Image.Resampling.LANCZOS))
                        tk.Label(frm, image=img, bg=bg_color, bd=2, relief="solid").pack(pady=10)
                        card.image_refs.append(img)
                        has_photo = True
                    except: pass
            if not has_photo:
                tk.Label(frm, text="📷\nNO IMAGE", font=("Arial", 12, "bold"), bg="#d3d3d3", fg="#555", width=15, height=7, bd=1, relief="solid").pack(pady=10)
            
            age = today.year - r['DOB'].year - ((today.month, today.day) < (r['DOB'].month, r['DOB'].day))
            info = f"नाम: {r['Name']}\nपद: {r.get('Designation','')}" if is_staff else f"नाम: {r['Name']}\nपिता: {r.get('Father Name','')}\nकक्षा: {r.get('Class','')}"
            tk.Label(frm, text=info, font=("Arial", 15, "bold"), bg=bg_color).pack(pady=5)
            tk.Label(frm, text=f"🎉 आज {r['Name']} {age} साल के हो गए! 🎉", font=("Arial", 13, "bold"), bg=bg_color, fg="#e91e63").pack(pady=5)

    render_data(staff, "🏫 स्टाफ सदस्य", "#e8eaf6", True)
    render_data(students, "🎓 विद्यार्थी", "#fffde7", False)

def get_active_data(path):
    if os.path.exists(path):
        df = pd.read_excel(path)
        if 'Status' in df.columns: df = df[df['Status'].astype(str).str.strip().str.upper() == 'ACTIVE']
        df['DOB'] = pd.to_datetime(df['DOB'])
        return df
    return pd.DataFrame()

def check_birthdays(is_manual=False):
    try:
        today = datetime.now()
        start_date = today
        already_checked = False
        last_run_path = os.path.join(BASE_PATH, "last_run.txt")
        
        if os.path.exists(last_run_path):
            try:
                lrd = datetime.strptime(open(last_run_path).read().strip(), "%Y-%m-%d")
                if lrd.date() == today.date(): already_checked = True
                start_date = lrd + timedelta(days=1)
            except: pass 

        if not is_manual and already_checked: return
        dates = [(d.month, d.day) for d in (start_date + timedelta(n) for n in range((today - start_date).days + 1))] if not is_manual else [(today.month, today.day)]
        
        df_stu, df_stf = get_active_data(FILE_PATH), get_active_data(STAFF_FILE_PATH)
        b_stu = df_stu[df_stu.apply(lambda r: (r['DOB'].month, r['DOB'].day) in dates, axis=1)] if not df_stu.empty else pd.DataFrame()
        b_stf = df_stf[df_stf.apply(lambda r: (r['DOB'].month, r['DOB'].day) in dates, axis=1)] if not df_stf.empty else pd.DataFrame()

        if len(b_stu) + len(b_stf) > 0: show_birthday_card(b_stu, b_stf)
        elif is_manual: messagebox.showinfo("जानकारी", "आज किसी का जन्मदिन नहीं है।")

        if not is_manual: open(last_run_path, 'w').write(today.strftime("%Y-%m-%d"))
    except Exception as e: logger.error(f"Check Error: {e}", exc_info=True)

def open_date_picker():
    picker = tk.Toplevel()
    picker.title("तारीख चुनें")
    picker.geometry("300x150")
    picker.attributes('-topmost', True)
    d_var, m_var = tk.StringVar(value=str(datetime.now().day)), tk.StringVar(value=str(datetime.now().month))
    tk.Entry(picker, textvariable=d_var, width=5).pack(pady=5)
    tk.Entry(picker, textvariable=m_var, width=5).pack(pady=5)
    def on_sub():
        try:
            d, m = int(d_var.get()), int(m_var.get())
            picker.destroy()
            df_stu, df_stf = get_active_data(FILE_PATH), get_active_data(STAFF_FILE_PATH)
            b_stu = df_stu[(df_stu['DOB'].dt.month == m) & (df_stu['DOB'].dt.day == d)] if not df_stu.empty else pd.DataFrame()
            b_stf = df_stf[(df_stf['DOB'].dt.month == m) & (df_stf['DOB'].dt.day == d)] if not df_stf.empty else pd.DataFrame()
            if len(b_stu) + len(b_stf) > 0: show_birthday_card(b_stu, b_stf, f"🎂 {d}-{m} का जन्मदिन 🎂")
            else: messagebox.showinfo("जानकारी", "इस दिन कोई जन्मदिन नहीं है।")
        except: pass
    tk.Button(picker, text="चेक करें", command=on_sub).pack()

# ==========================================
# 9. मैनेजमेंट UIs (डेटा, सेटिंग्स, लाइसेंस)
# ==========================================
def open_manager(file_path, title, is_staff=False):
    win = tk.Toplevel()
    win.title(title)
    win.geometry("900x650")
    win.attributes('-topmost', True)

    try:
        df = pd.read_excel(file_path)
        if 'Status' not in df.columns: df['Status'] = 'Active'
        if 'Student_ID' not in df.columns and not is_staff: df['Student_ID'] = [f"STU-{uuid.uuid4().hex[:6].upper()}" for _ in range(len(df))]
        if 'Staff_ID' not in df.columns and is_staff: df['Staff_ID'] = [f"STF-{uuid.uuid4().hex[:6].upper()}" for _ in range(len(df))]
    except: return messagebox.showerror("Error", "डेटा लोड त्रुटि", parent=win)

    top_frame = tk.Frame(win)
    top_frame.pack(fill="x", padx=20, pady=10)
    tk.Label(top_frame, text="सर्च:", font=("Arial", 11, "bold")).pack(side="left")
    search_var = tk.StringVar()
    tk.Entry(top_frame, textvariable=search_var, width=30).pack(side="left", padx=5)

    tree_frame = tk.Frame(win)
    tree_frame.pack(fill="both", expand=True, padx=20, pady=5)
    cols = ("ID", "Name", "Info", "Class", "Status") if not is_staff else ("ID", "Name", "Designation", "Status")
    tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
    for c in cols: tree.heading(c, text=c)
    tree.pack(fill="both", expand=True, side="left")
    scr = ttk.Scrollbar(tree_frame, command=tree.yview)
    scr.pack(side="right", fill="y"); tree.config(yscrollcommand=scr.set)

    search_timer = None
    def populate(q=""):
        for i in tree.get_children(): tree.delete(i)
        q, count = q.lower(), 0
        for idx, r in df.iterrows():
            n = str(r.get('Name', ''))
            if q in n.lower():
                s = str(r.get('Status', 'Active')).capitalize()
                uid = r.get('Staff_ID') if is_staff else r.get('Student_ID')
                if is_staff: tree.insert("", "end", values=(uid, n, r.get('Designation',''), s, idx))
                else: tree.insert("", "end", values=(uid, n, r.get('Father Name',''), r.get('Class',''), s, idx))
                count += 1
                if count >= 100: break
    populate()

    def on_search(*args):
        nonlocal search_timer
        if search_timer: win.after_cancel(search_timer)
        search_timer = win.after(300, lambda: populate(search_var.get()))
    search_var.trace("w", on_search)

    btn_frame = tk.Frame(win)
    btn_frame.pack(fill="x", padx=20, pady=15)

    def toggle_status():
        sel = tree.selection()
        if not sel: return
        idx = int(tree.item(sel[0], "values")[-1])
        df.at[idx, 'Status'] = "Inactive" if str(df.at[idx, 'Status']).lower() == "active" else "Active"
        populate(search_var.get())

    def save_data():
        try:
            exp_df = df.copy()
            exp_df['DOB'] = pd.to_datetime(exp_df['DOB'], errors='coerce').dt.strftime('%d-%m-%Y')
            exp_df.to_excel(file_path, index=False)
            threading.Thread(target=create_auto_backup, daemon=True).start()
            messagebox.showinfo("सफलता", "सेव हो गया!", parent=win)
        except: messagebox.showerror("Error", "सेव त्रुटि", parent=win)

    def add_new():
        add_win = tk.Toplevel(win)
        add_win.title("नया जोड़ें")
        add_win.geometry("400x400")
        tk.Label(add_win, text="Name:").pack()
        n_ent = tk.Entry(add_win); n_ent.pack()
        tk.Label(add_win, text="Info (Father/Desig):").pack()
        i_ent = tk.Entry(add_win); i_ent.pack()
        c_ent = None
        if not is_staff: tk.Label(add_win, text="Class:").pack(); c_ent = tk.Entry(add_win); c_ent.pack()
        tk.Label(add_win, text="DOB (DD-MM-YYYY):").pack()
        d_ent = tk.Entry(add_win); d_ent.pack()
        
        def save():
            nonlocal df
            try:
                dob = datetime.strptime(d_ent.get(), "%d-%m-%Y")
                uid = f"{'STF' if is_staff else 'STU'}-{uuid.uuid4().hex[:6].upper()}"
                row = {'Name': n_ent.get(), 'DOB': dob, 'Status': 'Active', 'Photo': ''}
                if is_staff: row.update({'Staff_ID': uid, 'Designation': i_ent.get()})
                else: row.update({'Student_ID': uid, 'Father Name': i_ent.get(), 'Class': c_ent.get()})
                df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                populate(search_var.get())
                add_win.destroy()
                messagebox.showinfo("OK", "जुड़ गया! 'सेव करें' दबाना न भूलें।", parent=win)
            except: messagebox.showerror("Error", "तारीख गलत है।", parent=add_win)
        tk.Button(add_win, text="Save", command=save).pack(pady=10)

    def bulk_import():
        f = filedialog.askopenfilename(parent=win, filetypes=[("Excel", "*.xlsx")])
        if not f: return
        try:
            nd = pd.read_excel(f)
            nd['DOB'] = pd.to_datetime(nd['DOB'], errors='coerce')
            nd = nd.dropna(subset=['DOB'])
            prfx = 'STF' if is_staff else 'STU'
            uid_col = 'Staff_ID' if is_staff else 'Student_ID'
            nd[uid_col] = [f"{prfx}-{uuid.uuid4().hex[:6].upper()}" for _ in range(len(nd))]
            if 'Status' not in nd.columns: nd['Status'] = 'Active'
            nonlocal df; df = pd.concat([df, nd], ignore_index=True)
            populate()
            messagebox.showinfo("OK", "इम्पोर्ट सफल!", parent=win)
        except: messagebox.showerror("Err", "इम्पोर्ट फेल", parent=win)

    def download_tpl():
        f = filedialog.asksaveasfilename(parent=win, defaultextension=".xlsx", initialfile=f"{'Staff' if is_staff else 'Student'}_Template.xlsx")
        if f:
            cols = ['Name', 'Designation', 'DOB', 'Photo'] if is_staff else ['Name', 'Father Name', 'Class', 'DOB', 'Photo']
            pd.DataFrame([['Dummy Name', 'Dummy Info', '15-08-2000', ''] + (['10th'] if not is_staff else [])], columns=cols).to_excel(f, index=False)
            messagebox.showinfo("OK", "टेम्पलेट सेव हो गई!", parent=win)

    tk.Button(btn_frame, text="📄 टेम्पलेट", command=download_tpl, bg="#009688", fg="white").pack(side="left", padx=5)
    tk.Button(btn_frame, text="📥 बल्क इम्पोर्ट", command=bulk_import, bg="#2196F3", fg="white").pack(side="left", padx=5)
    tk.Button(btn_frame, text="➕ नया", command=add_new, bg="#9C27B0", fg="white").pack(side="left", padx=5)
    tk.Button(btn_frame, text="🔄 स्टेटस बदलें", command=toggle_status, bg="#FF9800", fg="white").pack(side="left", padx=5)
    tk.Button(btn_frame, text="💾 सेव करें", command=save_data, bg="#4CAF50", fg="white").pack(side="right", padx=5)

def open_settings():
    win = tk.Toplevel()
    win.title("सेटिंग्स")
    win.geometry("400x450")
    win.attributes('-topmost', True)
    cfg = load_config()

    tk.Label(win, text="School Name:").pack()
    s_var = tk.StringVar(value=cfg.get("SCHOOL_NAME", ""))
    tk.Entry(win, textvariable=s_var).pack()

    tk.Label(win, text="Group ID:").pack()
    g_var = tk.StringVar(value=cfg.get("GROUP_ID", ""))
    tk.Entry(win, textvariable=g_var).pack()

    tk.Label(win, text="Wait Time (sec):").pack()
    w_var = tk.StringVar(value=str(cfg.get("WA_WAIT_TIME", 18)))
    tk.Entry(win, textvariable=w_var).pack()

    def change_pwd():
        p_win = tk.Toplevel(win)
        p_win.geometry("300x200")
        tk.Label(p_win, text="नया पासवर्ड:").pack()
        n_pwd = tk.Entry(p_win, show="*"); n_pwd.pack()
        def save_p():
            cfg["ADMIN_PASSWORD_HASH"] = hash_password(n_pwd.get())
            save_config(cfg); messagebox.showinfo("OK", "पासवर्ड बदल गया", parent=p_win); p_win.destroy()
        tk.Button(p_win, text="Save Password", command=save_p).pack()

    def save_all():
        cfg.update({"SCHOOL_NAME": s_var.get(), "GROUP_ID": g_var.get(), "WA_WAIT_TIME": int(w_var.get())})
        if save_config(cfg): win.destroy()

    f = tk.Frame(win); f.pack(pady=20)
    tk.Button(f, text="🔐 पासवर्ड बदलें", command=change_pwd).pack(side="left", padx=10)
    tk.Button(f, text="Save Settings", command=save_all, bg="#4CAF50", fg="white").pack(side="left", padx=10)

def open_license_status():
    win = tk.Toplevel()
    win.title("लाइसेंस स्थिति")
    win.geometry("350x300")
    win.attributes('-topmost', True)
    
    lic = get_license_details()
    if not lic: tk.Label(win, text="लाइसेंस नहीं मिला!").pack(); return
    
    exp = datetime.strptime(lic.get("expiry_date"), "%Y-%m-%d")
    days = (exp - datetime.now()).days
    
    tk.Label(win, text=f"स्कूल: {lic.get('school_name')}", font=("Arial", 12)).pack(pady=10)
    tk.Label(win, text=f"एक्सपायरी: {lic.get('expiry_date')}").pack()
    tk.Label(win, text=f"{days} दिन शेष हैं", fg="green" if days>30 else "red", font=("Arial", 14)).pack(pady=10)
    
    hw_id = get_hardware_id()
    tk.Label(win, text=f"मशीन ID: {hw_id}").pack()
    tk.Button(win, text="📋 ID कॉपी करें", command=lambda: pyperclip.copy(hw_id)).pack(pady=5)

# ==========================================
# 10. सिस्टम ट्रे और एंट्री पॉइंट
# ==========================================
def setup_tray():
    menu = (
        item('आज चेक करें', lambda: root.after(0, lambda: check_birthdays(True))),
        item('विशिष्ट तारीख', lambda: root.after(0, open_date_picker)),
        pystray.Menu.SEPARATOR,
        item('विद्यार्थी मैनेज करें 🔒', lambda: root.after(0, lambda: authenticate_admin(lambda: open_manager(FILE_PATH, "Students")))),
        item('स्टाफ मैनेज करें 🔒', lambda: root.after(0, lambda: authenticate_admin(lambda: open_manager(STAFF_FILE_PATH, "Staff", True)))),
        pystray.Menu.SEPARATOR,
        item('लाइसेंस स्थिति', lambda: root.after(0, open_license_status)),
        item('सेटिंग्स 🔒', lambda: root.after(0, lambda: authenticate_admin(open_settings))),
        item('Exit', lambda i, it: [i.stop(), root.quit(), os._exit(0)])
    )
    img = Image.new('RGB', (64, 64), color="#e91e63")
    ImageDraw.Draw(img).rectangle((16, 16, 48, 48), fill="#ffeb3b")
    pystray.Icon("App", img, "Birthday Tracker", menu).run()

if __name__ == "__main__":
    global root
    root = tk.Tk()
    root.withdraw()

    # 1. लाइसेंस और सुरक्षा जाँच
    is_valid, msg, days_left = validate_license()
    if not is_valid:
        messagebox.showerror("लाइसेंस त्रुटि", msg)
        sys.exit()
        
    if days_left <= 15:
        messagebox.showwarning("रिन्यूअल रिमाइंडर", f"⚠️ आपका लाइसेंस {days_left} दिनों में समाप्त हो जाएगा!\nमशीन ID ({get_hardware_id()}) डेवलपर को भेजें।")

    # 2. 🚀 GitHub ऑटो-अपडेट जाँच (नया जोड़ा गया)
    threading.Thread(target=check_for_updates, daemon=True).start()

    # 3. बैकग्राउंड थ्रेड्स
    threading.Thread(target=create_auto_backup, daemon=True).start()
    threading.Thread(target=setup_tray, daemon=True).start()

    def periodic_check():
        check_birthdays(False)
        root.after(14400000, periodic_check) 

    root.after(2000, periodic_check)
    root.mainloop()
