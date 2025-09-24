import os
import datetime
import re
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as messagebox
import tempfile
import platform
import subprocess
import json

# Optional: For PDF generation (install via: pip install fpdf2)
try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("Warning: fpdf2 not installed. Install with 'pip install fpdf2' for PDF bill support.")

from abc import ABC, abstractmethod

class Billable(ABC):
    @abstractmethod
    def calculate_total(self):
        pass

class Clinic:
    def __init__(self, name):
        self._name = name

    def get_clinic_name(self):
        return self._name

class DentalClinic(Clinic):
    def __init__(self, name):
        super().__init__(name)
        self._treatments = {
           
           }

    def get_treatments(self):
        return self._treatments

class Patient(Billable):
    def __init__(self, name, phone):
        self._name = name.strip()
        self._phone = phone.strip()
        self._treatments = []  

    def add_treatment(self, treatment):
        if treatment and isinstance(treatment, tuple):
            self._treatments.append(treatment)
        else:
            raise ValueError("Invalid treatment value")

    def get_patient_name(self):
        return self._name

    def get_phone(self):
        return self._phone

    def calculate_total(self):
        return sum(cost for _, cost in self._treatments)

    def _build_bill_text(self, clinic, title="BILL RECEIPT"):
        lines = []
        lines.append(f"\n===== {title} =====")
        lines.append(f"Clinic: {clinic.get_clinic_name()}")
        lines.append(f"Patient Name: {self.get_patient_name()}")
        lines.append(f"Phone: {self.get_phone()}")
        lines.append("---------------------------")
        lines.append("Treatments:")
        if self._treatments:
            for t, cost in self._treatments:
                lines.append(f"- {t}: Rs. {cost}")
        else:
            lines.append("- (No treatments selected)")
        lines.append("---------------------------")
        total = self.calculate_total()
        lines.append(f"Total Amount: Rs. {total}")
        lines.append("===========================")
        return "\n".join(lines)

    def _get_script_dir(self):
        if "__file__" in globals():
            return os.path.abspath(os.path.dirname(__file__))
        return os.getcwd()

    def save_bill_to_files(self, bill_text, combined_filename="patient_bills.txt", make_individual=True):
        script_dir = self._get_script_dir()
        bills_dir = os.path.join(script_dir, "bills")
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        date_folder = os.path.join(bills_dir, today_str)
        
        os.makedirs(date_folder, exist_ok=True)
        
        combined_path = os.path.join(script_dir, combined_filename)
        individual_txt_path = None
        individual_pdf_path = None

        try:
            with open(combined_path, "a", encoding="utf-8") as f:
                f.write(bill_text + "\n\n")
        except Exception as e:
            print(f"Error saving combined bill file ({combined_path}): {e}")

        if make_individual:
            safe_name = re.sub(r'[^A-Za-z0-9_\-]+', '_', self._name) or "patient"
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            individual_txt_name = f"{safe_name}_bill_{timestamp}.txt"
            individual_pdf_name = f"{safe_name}_bill_{timestamp}.pdf"
            individual_txt_path = os.path.join(date_folder, individual_txt_name)
            individual_pdf_path = os.path.join(date_folder, individual_pdf_name)
            
            try:
                with open(individual_txt_path, "w", encoding="utf-8") as f:
                    f.write(bill_text + "\n")
            except Exception as e:
                print(f"Error saving individual TXT file ({individual_txt_path}): {e}")

            if PDF_AVAILABLE:
                try:
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    
                    pdf.set_font("Arial", 'B', 16)
                    pdf.cell(200, 10, txt="BILL RECEIPT", ln=1, align='C')
                    pdf.ln(10)
                    
                    pdf.set_font("Arial", size=12)
                    for line in bill_text.split('\n'):
                        if line.strip():
                            pdf.cell(200, 8, txt=line, ln=1)
                    
                    pdf.output(individual_pdf_path)
                except Exception as e:
                    print(f"Error saving individual PDF file ({individual_pdf_path}): {e}")
            else:
                print("PDF saving skipped: fpdf2 not installed.")

        return combined_path, individual_txt_path, individual_pdf_path

class VIPPatient(Patient):
    def __init__(self, name, phone, discount=10):
        super().__init__(name, phone)
        self.discount = discount

    def calculate_total(self):
        total = super().calculate_total()
        discounted = total * (1 - (self.discount / 100.0))
        return round(discounted, 2)

    def _build_bill_text(self, clinic, title="VIP BILL RECEIPT"):
        lines = []
        lines.append(f"\n===== {title} =====")
        lines.append(f"Clinic: {clinic.get_clinic_name()}")
        lines.append(f"VIP Patient Name: {self.get_patient_name()}")
        lines.append(f"Phone: {self.get_phone()}")
        lines.append("---------------------------")
        lines.append("Treatments:")
        if self._treatments:
            for t, cost in self._treatments:
                lines.append(f"- {t}: Rs. {cost}")
        else:
            lines.append("- (No treatments selected)")
        lines.append("---------------------------")
        original_total = sum(cost for _, cost in self._treatments)
        lines.append(f"Original Total: Rs. {original_total}")
        lines.append(f"Discount: {self.discount}%")
        lines.append(f"Total Amount after Discount: Rs. {self.calculate_total()}")
        lines.append("===========================")
        return "\n".join(lines)

class Appointment:
    def __init__(self, patient_name, phone, date, time_slot, treatments):
        self.patient_name = patient_name.strip()
        self.phone = phone.strip()
        self.date = date  # YYYY-MM-DD string
        self.time_slot = time_slot  # HH:MM string
        self.treatments = treatments  # list of (name, cost) tuples

    def to_dict(self):
        return {
            'patient_name': self.patient_name,
            'phone': self.phone,
            'date': self.date,
            'time_slot': self.time_slot,
            'treatments': [(name, float(cost)) for name, cost in self.treatments]
        }

    @classmethod
    def from_dict(cls, data):
        treatments = [(name, cost) for name, cost in data['treatments']]
        return cls(data['patient_name'], data['phone'], data['date'], data['time_slot'], treatments)

    def is_upcoming(self):
        try:
            appt_date = datetime.datetime.strptime(self.date, "%Y-%m-%d").date()
            today = datetime.date.today()
            return appt_date >= today
        except ValueError:
            return False

    def __str__(self):
        treatments_str = ", ".join([name for name, _ in self.treatments]) if self.treatments else "None"
        return f"{self.patient_name} - {self.date} {self.time_slot} ({treatments_str})"

def load_appointments(script_dir):
    appointments_file = os.path.join(script_dir, "appointments.json")
    if os.path.exists(appointments_file):
        try:
            with open(appointments_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [Appointment.from_dict(appt) for appt in data]
        except Exception as e:
            print(f"Error loading appointments: {e}")
    return []

def save_appointments(appointments, script_dir):
    appointments_file = os.path.join(script_dir, "appointments.json")
    try:
        with open(appointments_file, "w", encoding="utf-8") as f:
            json.dump([appt.to_dict() for appt in appointments], f, indent=4)
    except Exception as e:
        print(f"Error saving appointments: {e}")

# GUI Application
class DentalClinicGUI:
    def __init__(self, root, clinic):
        self.root = root
        self.clinic = clinic
        self.patient = None
        self.appointments = []
        self.script_dir = self._get_script_dir()
        self.load_appointments()

        # Theme colors
        self.bg_color = "#E8F4FD"
        self.fg_color = "#212121"
        self.button_bg = "#1976D2"
        self.button_fg = "#FFFFFF"
        self.entry_bg = "#FFFFFF"
        self.entry_fg = "#212121"
        self.listbox_bg = "#FFFFFF"
        self.listbox_fg = "#212121"
        self.accent_color = "#0D47A1"

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background=self.bg_color)
        style.configure('TNotebook.Tab', background=self.button_bg, foreground=self.button_fg, padding=[12, 8])
        style.map('TNotebook.Tab', background=[('selected', self.accent_color)], foreground=[('selected', self.button_fg)])

        root.title("Bright Smile Dental Clinic Management System")
        root.geometry("800x1000")  # Increased height for new tab
        root.resizable(True, True)
        root.configure(bg=self.bg_color)

        self.ribbon_frame = tk.Frame(root, bg=self.accent_color, height=50)
        self.ribbon_frame.grid(row=0, column=0, sticky="ew")
        self.ribbon_frame.grid_propagate(False)
        self.ribbon_label = tk.Label(self.ribbon_frame, text=self.clinic.get_clinic_name(),
                                     font=("Arial", 20, "bold"), fg=self.button_fg, bg=self.accent_color)
        self.ribbon_label.pack(expand=True)

        self.notebook = ttk.Notebook(root)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        self.billing_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.billing_frame, text="Billing")
        self.setup_billing_tab()

        self.appointments_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.appointments_frame, text="Appointments")
        self.setup_appointments_tab()

        self.search_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.search_frame, text="Search Records")
        self.setup_search_tab()

        root.grid_rowconfigure(1, weight=1)
        root.grid_columnconfigure(0, weight=1)

    def _get_script_dir(self):
        if "__file__" in globals():
            return os.path.abspath(os.path.dirname(__file__))
        return os.getcwd()

    def load_appointments(self):
        self.appointments = load_appointments(self.script_dir)
        if hasattr(self, 'appointments_listbox'):
            self.refresh_appointments_list()

    def save_appointments(self):
        save_appointments(self.appointments, self.script_dir)

    def setup_billing_tab(self):
        bg_color = self.bg_color
        fg_color = self.fg_color
        button_bg = self.button_bg
        button_fg = self.button_fg
        entry_bg = self.entry_bg
        entry_fg = self.entry_fg
        listbox_bg = self.listbox_bg
        listbox_fg = self.listbox_fg

        self.patient_type_var = tk.StringVar(value="normal")
        tk.Label(self.billing_frame, text="Patient Type:", font=("Arial", 12, "bold"), fg=fg_color, bg=bg_color).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        tk.Radiobutton(self.billing_frame, text="Normal", variable=self.patient_type_var, value="normal", command=self.toggle_discount,
                       bg=bg_color, fg=fg_color, selectcolor=bg_color, activebackground=bg_color, activeforeground=fg_color).grid(row=0, column=1, sticky="w")
        tk.Radiobutton(self.billing_frame, text="VIP", variable=self.patient_type_var, value="vip", command=self.toggle_discount,
                       bg=bg_color, fg=fg_color, selectcolor=bg_color, activebackground=bg_color, activeforeground=fg_color).grid(row=0, column=2, sticky="w")

        tk.Label(self.billing_frame, text="Patient Name:", font=("Arial", 12, "bold"), fg=fg_color, bg=bg_color).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.name_entry = tk.Entry(self.billing_frame, width=40, bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)
        self.name_entry.grid(row=1, column=1, columnspan=2, sticky="w")

        tk.Label(self.billing_frame, text="Phone:", font=("Arial", 12, "bold"), fg=fg_color, bg=bg_color).grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.phone_entry = tk.Entry(self.billing_frame, width=40, bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)
        self.phone_entry.grid(row=2, column=1, columnspan=2, sticky="w")

        tk.Label(self.billing_frame, text="VIP Discount (%):", font=("Arial", 12, "bold"), fg=fg_color, bg=bg_color).grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.discount_entry = tk.Entry(self.billing_frame, width=10, bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)
        self.discount_entry.grid(row=3, column=1, sticky="w")
        self.discount_entry.insert(0, "10")
        self.discount_entry.config(state="disabled")  

        tk.Label(self.billing_frame, text="Select Treatments:", font=("Arial", 12, "bold"), fg=fg_color, bg=bg_color).grid(row=4, column=0, sticky="w", padx=10, pady=5)

        self.treatment_listbox = tk.Listbox(self.billing_frame, selectmode=tk.MULTIPLE, width=50, height=8,
                                            bg=listbox_bg, fg=listbox_fg, selectbackground=button_bg, selectforeground=button_fg,
                                            highlightbackground=bg_color, relief="flat")
        self.treatment_listbox.grid(row=5, column=0, columnspan=3, padx=10, sticky="nsew")

        scrollbar = tk.Scrollbar(self.billing_frame, orient="vertical", command=self.treatment_listbox.yview)
        scrollbar.grid(row=5, column=3, sticky="nsw", pady=5)
        self.treatment_listbox.config(yscrollcommand=scrollbar.set)

        self.refresh_treatment_list()

        btn_params = {"font": ("Arial", 12, "bold"), "bg": button_bg, "fg": button_fg, "activebackground": "#1565C0", "activeforeground": button_fg, "relief": "flat"}

        self.generate_button = tk.Button(self.billing_frame, text="Generate Bill", command=self.generate_bill, **btn_params)
        self.generate_button.grid(row=6, column=0, pady=15, sticky="ew", padx=(10,5))

        self.clear_button = tk.Button(self.billing_frame, text="Clear Form", command=self.clear_inputs, **btn_params)
        self.clear_button.grid(row=6, column=1, pady=15, sticky="ew", padx=5)

        self.edit_treatment_button = tk.Button(self.billing_frame, text="Edit Treatments", command=self.edit_treatments, **btn_params)
        self.edit_treatment_button.grid(row=6, column=2, pady=15, sticky="ew", padx=5)

        self.edit_price_button = tk.Button(self.billing_frame, text="Edit Prices", command=self.edit_prices, **btn_params)
        self.edit_price_button.grid(row=6, column=3, pady=15, sticky="ew", padx=5)

        self.print_button = tk.Button(self.billing_frame, text="Print Bill & Prescription", command=self.print_bill_and_prescription, **btn_params)
        self.print_button.grid(row=6, column=4, pady=15, sticky="ew", padx=(5,10))

        # Bill Display Frame
        self.bill_frame = tk.Frame(self.billing_frame, bd=1, relief="solid", bg=bg_color)
        self.bill_frame.grid(row=7, column=0, columnspan=5, padx=10, pady=10, sticky="nsew")

        self.bill_text = tk.Text(self.bill_frame, width=80, height=12, font=("Courier", 10),
                                 wrap="none", borderwidth=0, bg="#FFFFFF", fg=fg_color, insertbackground=fg_color)
        self.bill_text.pack(side="left", fill="both", expand=True)

        self.bill_scroll_y = tk.Scrollbar(self.bill_frame, orient="vertical", command=self.bill_text.yview)
        self.bill_scroll_y.pack(side="right", fill="y")
        self.bill_text.config(yscrollcommand=self.bill_scroll_y.set)

        self.bill_scroll_x = tk.Scrollbar(self.billing_frame, orient="horizontal", command=self.bill_text.xview)
        self.bill_scroll_x.grid(row=8, column=0, columnspan=5, sticky="ew", padx=10)
        self.bill_text.config(xscrollcommand=self.bill_scroll_x.set)

        tk.Label(self.billing_frame, text="Prescription (manual entry):", font=("Arial", 12, "bold"), fg=fg_color, bg=bg_color).grid(row=9, column=0, sticky="w", padx=10, pady=(20,5))

        self.prescription_frame = tk.Frame(self.billing_frame, bd=1, relief="solid", bg=bg_color)
        self.prescription_frame.grid(row=10, column=0, columnspan=5, padx=10, pady=5, sticky="nsew")

        self.prescription_text = tk.Text(self.prescription_frame, width=80, height=8, font=("Courier", 10),
                                         wrap="word", borderwidth=0, bg="#FFFFFF", fg=fg_color, insertbackground=fg_color)
        self.prescription_text.pack(side="left", fill="both", expand=True)

        self.prescription_scroll_y = tk.Scrollbar(self.prescription_frame, orient="vertical", command=self.prescription_text.yview)
        self.prescription_scroll_y.pack(side="right", fill="y")
        self.prescription_text.config(yscrollcommand=self.prescription_scroll_y.set)

        self.billing_frame.grid_rowconfigure(5, weight=1)
        self.billing_frame.grid_rowconfigure(7, weight=3)
        self.billing_frame.grid_rowconfigure(10, weight=2)
        for col in range(5):
            self.billing_frame.grid_columnconfigure(col, weight=1)

    def refresh_treatment_list(self):
        self.treatment_listbox.delete(0, tk.END)
        self.treatment_keys = []
        for key, (treatment, cost) in self.clinic.get_treatments().items():
            self.treatment_listbox.insert(tk.END, f"{treatment} - Rs. {cost}")
            self.treatment_keys.append(key)

    def toggle_discount(self):
        if self.patient_type_var.get() == "vip":
            self.discount_entry.config(state="normal")
        else:
            self.discount_entry.delete(0, tk.END)
            self.discount_entry.insert(0, "10")
            self.discount_entry.config(state="disabled")

    def clear_inputs(self):
        self.patient_type_var.set("normal")
        self.toggle_discount()
        self.name_entry.delete(0, tk.END)
        self.phone_entry.delete(0, tk.END)
        self.treatment_listbox.selection_clear(0, tk.END)
        self.bill_text.delete(1.0, tk.END)
        self.prescription_text.delete(1.0, tk.END)

    def generate_bill(self):
        name = self.name_entry.get().strip()
        phone = self.phone_entry.get().strip()
        if not name:
            messagebox.showwarning("Input Error", "Please enter patient name.")
            return
        if not phone:
            messagebox.showwarning("Input Error", "Please enter phone number.")
            return

        patient_type = self.patient_type_var.get()
        if patient_type == "vip":
            try:
                discount = float(self.discount_entry.get())
                if discount < 0 or discount > 100:
                    messagebox.showwarning("Input Error", "Discount must be between 0 and 100.")
                    return
            except ValueError:
                messagebox.showwarning("Input Error", "Invalid discount value.")
                return
            self.patient = VIPPatient(name, phone, discount=discount)
        else:
            self.patient = Patient(name, phone)

        selected_indices = self.treatment_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Input Error", "Please select at least one treatment.")
            return

        self.patient._treatments.clear()
        for idx in selected_indices:
            key = self.treatment_keys[idx]
            treatment = self.clinic.get_treatments()[key]
            self.patient.add_treatment(treatment)

        if patient_type == "vip":
            bill_text = self.patient._build_bill_text(self.clinic, title="VIP BILL RECEIPT")
        else:
            bill_text = self.patient._build_bill_text(self.clinic, title="BILL RECEIPT")

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_text = f"Date & Time: {now_str}\n{bill_text}"

        self.bill_text.delete(1.0, tk.END)
        self.bill_text.insert(tk.END, full_text)

        combined_path, txt_path, pdf_path = self.patient.save_bill_to_files(full_text)
        pdf_msg = f"PDF: {pdf_path}" if PDF_AVAILABLE and pdf_path else "PDF: Skipped (install fpdf2)"
        messagebox.showinfo("Success", f"Bill generated and saved!\nCombined TXT: {combined_path}\nIndividual TXT: {txt_path}\n{pdf_msg}")

    def edit_treatments(self):
        treatments = self.clinic.get_treatments()
        edit_win = tk.Toplevel(self.root)
        edit_win.title("Edit Treatments")
        edit_win.geometry("400x300")
        edit_win.configure(bg=self.bg_color)
        tk.Label(edit_win, text="Treatments (one per line):", font=("Arial", 12, "bold"), fg=self.fg_color, bg=self.bg_color).pack(pady=5)

        text_box = tk.Text(edit_win, width=40, height=10, bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg)
        text_box.pack(padx=10, pady=5)

        for key in sorted(treatments.keys()):
            text_box.insert(tk.END, treatments[key][0] + "\n")

        def save_treatments():
            lines = text_box.get(1.0, tk.END).strip().split("\n")
            if not lines or all(not line.strip() for line in lines):
                messagebox.showwarning("Input Error", "At least one treatment is required.")
                return
            new_treatments = {}
            old_treatments = {v[0]: v[1] for v in treatments.values()}
            for i, name in enumerate(lines, 1):
                name = name.strip()
                if not name:
                    continue
                price = old_treatments.get(name, 1000)
                new_treatments[i] = (name, price)
            if not new_treatments:
                messagebox.showwarning("Input Error", "At least one valid treatment is required.")
                return
            self.clinic._treatments = new_treatments
            self.refresh_treatment_list()
            self.refresh_appt_treatment_list()
            edit_win.destroy()
            messagebox.showinfo("Success", "Treatments updated!")

        save_btn = tk.Button(edit_win, text="Save", command=save_treatments,
                             bg=self.button_bg, fg=self.button_fg, font=("Arial", 12, "bold"), relief="flat",
                             activebackground="#1565C0", activeforeground=self.button_fg)
        save_btn.pack(pady=10)

    def edit_prices(self):
        treatments = self.clinic.get_treatments()
        edit_win = tk.Toplevel(self.root)
        edit_win.title("Edit Prices")
        edit_win.geometry("400x300")
        edit_win.configure(bg=self.bg_color)

        tk.Label(edit_win, text="Edit Prices (treatment: price, one per line):", font=("Arial", 12, "bold"), fg=self.fg_color, bg=self.bg_color).pack(pady=5)       
        text_box = tk.Text(edit_win, width=40, height=10, bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg)
        text_box.pack(padx=10, pady=5)

        for key in sorted(treatments.keys()):
            name, price = treatments[key]
            text_box.insert(tk.END, f"{name}: {price}\n")

        def save_prices():
            lines = text_box.get(1.0, tk.END).strip().split("\n")
            new_treatments = {}
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if not line or ':' not in line:
                    continue
                name, price_str = [part.strip() for part in line.split(':', 1)]
                if not name:
                    continue
                try:
                    price = float(price_str)
                    if price < 0:
                        messagebox.showwarning("Input Error", f"Line {i}: Price cannot be negative.")
                        return
                except ValueError:
                    messagebox.showwarning("Input Error", f"Line {i}: Invalid price '{price_str}'.")
                    return
                new_treatments[i] = (name, price)
            if not new_treatments:
                messagebox.showwarning("Input Error", "At least one valid treatment:price is required.")
                return
            self.clinic._treatments = new_treatments
            self.refresh_treatment_list()
            self.refresh_appt_treatment_list()
            edit_win.destroy()
            messagebox.showinfo("Success", "Prices updated!")

        save_btn = tk.Button(edit_win, text="Save", command=save_prices,
                             bg=self.button_bg, fg=self.button_fg, font=("Arial", 12, "bold"), relief="flat",
                             activebackground="#1565C0", activeforeground=self.button_fg)
        save_btn.pack(pady=10)

    def print_bill_and_prescription(self):
        bill_content = self.bill_text.get(1.0, tk.END).strip()
        prescription_content = self.prescription_text.get(1.0, tk.END).strip()

        if not bill_content:
            messagebox.showwarning("Print Error", "No bill to print. Please generate a bill first.")
            return

        combined_text = bill_content + "\n\n===== Prescription =====\n" + (prescription_content if prescription_content else "(No prescription entered)")

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp_file:
                tmp_file.write(combined_text)
                temp_filename = tmp_file.name
        except Exception as e:
            messagebox.showerror("Print Error", f"Failed to create temporary file: {e}")
            return

        system_name = platform.system()
        try:
            if system_name == "Windows":
                os.startfile(temp_filename, "print")
            elif system_name == "Darwin":  # macOS
                subprocess.run(["lp", temp_filename], check=True)
            else:  # Linux/Unix
                subprocess.run(["lp", temp_filename], check=True)
        except Exception as e:
            messagebox.showerror("Print Error", f"Failed to print: {e}. Check your printer setup.")
            try:
                os.unlink(temp_filename)
            except:
                pass
            return

        try:
            os.unlink(temp_filename)
        except:
            pass

        messagebox.showinfo("Print Success", "Bill and prescription sent to printer!")

    def setup_search_tab(self):
        bg_color = self.bg_color
        fg_color = self.fg_color
        button_bg = self.button_bg
        button_fg = self.button_fg
        entry_bg = self.entry_bg
        entry_fg = self.entry_fg

        tk.Label(self.search_frame, text="Search Patient Records (by Name or Phone)", font=("Arial", 14, "bold"), fg=fg_color, bg=bg_color).grid(row=0, column=0, columnspan=3, pady=10, sticky="w")

        tk.Label(self.search_frame, text="Search Query:", font=("Arial", 12, "bold"), fg=fg_color, bg=bg_color).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.search_tab_entry = tk.Entry(self.search_frame, width=50, bg=entry_bg, fg=entry_fg, insertbackground=entry_fg, font=("Arial", 10))
        self.search_tab_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        self.search_tab_entry.insert(0, "Enter name or phone (partial match)...")

        btn_params = {"font": ("Arial", 12, "bold"), "bg": button_bg, "fg": button_fg, "activebackground": "#1565C0", "activeforeground": button_fg, "relief": "flat"}

        self.search_tab_button = tk.Button(self.search_frame, text="Search", command=self.search_bills, **btn_params)
        self.search_tab_button.grid(row=1, column=2, pady=5, padx=(10,5), sticky="ew")

        self.clear_search_tab_button = tk.Button(self.search_frame, text="Clear Search", command=self.clear_search, **btn_params)
        self.clear_search_tab_button.grid(row=2, column=1, pady=5, sticky="ew", padx=5)

        self.refresh_search_button = tk.Button(self.search_frame, text="Refresh Records", command=self.refresh_search_records, **btn_params)
        self.refresh_search_button.grid(row=2, column=2, pady=5, padx=(5,10), sticky="ew")

        tk.Label(self.search_frame, text="Search Results", font=("Arial", 14, "bold"), fg=fg_color, bg=bg_color).grid(row=3, column=0, columnspan=3, pady=(20,5), sticky="w")

        self.search_results_frame = tk.Frame(self.search_frame, bd=1, relief="solid", bg=bg_color)
        self.search_results_frame.grid(row=4, column=0, columnspan=3, padx=10, pady=5, sticky="nsew")

        self.search_results_text = tk.Text(self.search_results_frame, width=80, height=15, font=("Courier", 10),
                                           wrap="word", borderwidth=0, bg="#FFFFFF", fg=fg_color, insertbackground=fg_color)
        self.search_results_text.pack(side="left", fill="both", expand=True)

        self.search_scroll_y = tk.Scrollbar(self.search_results_frame, orient="vertical", command=self.search_results_text.yview)
        self.search_scroll_y.pack(side="right", fill="y")
        self.search_results_text.config(yscrollcommand=self.search_scroll_y.set)

        self.search_scroll_x = tk.Scrollbar(self.search_frame, orient="horizontal", command=self.search_results_text.xview)
        self.search_scroll_x.grid(row=5, column=0, columnspan=3, sticky="ew", padx=10)
        self.search_results_text.config(xscrollcommand=self.search_scroll_x.set)

        self.search_results_text.insert(tk.END, "Enter a search query (name or phone) and click 'Search' to view patient bill records.\nGenerate bills first if no records exist.")

        self.search_frame.grid_rowconfigure(4, weight=3)
        self.search_frame.grid_rowconfigure(1, weight=1)
        for col in range(3):
            self.search_frame.grid_columnconfigure(col, weight=1)

    def search_bills(self):
        query = self.search_tab_entry.get().strip().lower()
        if not query or query == "enter name or phone (partial match)...":
            messagebox.showwarning("Search Error", "Please enter a valid search term (name or phone).")
            return

        script_dir = self._get_script_dir()
        combined_path = os.path.join(script_dir, "patient_bills.txt")
        if not os.path.exists(combined_path):
            self.search_results_text.delete(1.0, tk.END)
            self.search_results_text.insert(tk.END, "No bill records found. Please generate some bills in the Billing tab first.")
            messagebox.showinfo("No Records", "No bill records exist yet. Generate bills to create the search database.")
            return

        try:
            with open(combined_path, "r", encoding="utf-8") as f:
                content = f.read()

            bills = re.split(r'(?=={5,}|\n{3,})', content)
            matching_bills = [bill.strip() for bill in bills if bill.strip() and re.search(re.escape(query), bill.lower())]

            self.search_results_text.delete(1.0, tk.END)
            if matching_bills:
                results_text = f"Found {len(matching_bills)} matching record(s):\n\n"
                for i, bill in enumerate(matching_bills[:10], 1):  # Limit to 10 for UI
                    results_text += f"--- Record {i} ---\n{bill}\n{'='*50}\n\n"
                if len(matching_bills) > 10:
                    results_text += f"... and {len(matching_bills) - 10} more matches (refine search for more).\n"
                self.search_results_text.insert(tk.END, results_text)
                messagebox.showinfo("Search Results", f"Found {len(matching_bills)} matches. Full details shown below (limited to 10).")
            else:
                self.search_results_text.insert(tk.END, "No matching records found. Try a different name or phone (partial matches work).")
                messagebox.showinfo("Search Results", "No matches found. Try broadening your search term.")

        except Exception as e:
            self.search_results_text.delete(1.0, tk.END)
            self.search_results_text.insert(tk.END, f"Error during search: {str(e)}\nPlease ensure patient_bills.txt is accessible.")
            messagebox.showerror("Search Error", f"Failed to search bills: {e}")

    def clear_search(self):
        self.search_tab_entry.delete(0, tk.END)
        self.search_tab_entry.insert(0, "Enter name or phone (partial match)...")
        self.search_results_text.delete(1.0, tk.END)
        self.search_results_text.insert(tk.END, "Enter a search query (name or phone) and click 'Search' to view patient bill records.\nGenerate bills first if no records exist.")

    def refresh_search_records(self):
        self.clear_search()
        messagebox.showinfo("Refresh Complete", "Records refreshed. Perform a new search to view updated results.")

    def setup_appointments_tab(self):
        bg_color = self.bg_color
        fg_color = self.fg_color
        button_bg = self.button_bg
        button_fg = self.button_fg
        entry_bg = self.entry_bg
        entry_fg = self.entry_fg
        listbox_bg = self.listbox_bg
        listbox_fg = self.listbox_fg

        tk.Label(self.appointments_frame, text="Book New Appointment", font=("Arial", 14, "bold"), fg=fg_color, bg=bg_color).grid(row=0, column=0, columnspan=4, pady=10, sticky="w")

        tk.Label(self.appointments_frame, text="Patient Name:", font=("Arial", 12, "bold"), fg=fg_color, bg=bg_color).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.appt_name_entry = tk.Entry(self.appointments_frame, width=30, bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)
        self.appt_name_entry.grid(row=1, column=1, sticky="w", padx=5)

        tk.Label(self.appointments_frame, text="Phone:", font=("Arial", 12, "bold"), fg=fg_color, bg=bg_color).grid(row=1, column=2, sticky="w", padx=10, pady=5)
        self.appt_phone_entry = tk.Entry(self.appointments_frame, width=30, bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)
        self.appt_phone_entry.grid(row=1, column=3, sticky="w", padx=5)

        tk.Label(self.appointments_frame, text="Date (YYYY-MM-DD):", font=("Arial", 12, "bold"), fg=fg_color, bg=bg_color).grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.appt_date_entry = tk.Entry(self.appointments_frame, width=30, bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)
        self.appt_date_entry.grid(row=2, column=1, sticky="w", padx=5)
        self.appt_date_entry.insert(0, datetime.date.today().strftime("%Y-%m-%d"))  # Default to today

        tk.Label(self.appointments_frame, text="Time (HH:MM):", font=("Arial", 12, "bold"), fg=fg_color, bg=bg_color).grid(row=2, column=2, sticky="w", padx=10, pady=5)
        self.appt_time_entry = tk.Entry(self.appointments_frame, width=30, bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)
        self.appt_time_entry.grid(row=2, column=3, sticky="w", padx=5)

        tk.Label(self.appointments_frame, text="Select Treatments:", font=("Arial", 12, "bold"), fg=fg_color, bg=bg_color).grid(row=3, column=0, sticky="w", padx=10, pady=5)

        self.appt_treatment_listbox = tk.Listbox(self.appointments_frame, selectmode=tk.MULTIPLE, width=50, height=6,
                                                 bg=listbox_bg, fg=listbox_fg, selectbackground=button_bg, selectforeground=button_fg,
                                                 highlightbackground=bg_color, relief="flat")
        self.appt_treatment_listbox.grid(row=4, column=0, columnspan=4, padx=10, sticky="nsew")

        appt_scrollbar = tk.Scrollbar(self.appointments_frame, orient="vertical", command=self.appt_treatment_listbox.yview)
        appt_scrollbar.grid(row=4, column=4, sticky="nsw", pady=5)
        self.appt_treatment_listbox.config(yscrollcommand=appt_scrollbar.set)

        self.refresh_appt_treatment_list()

        btn_params = {"font": ("Arial", 12, "bold"), "bg": button_bg, "fg": button_fg, "activebackground": "#1565C0", "activeforeground": button_fg, "relief": "flat"}
        self.book_button = tk.Button(self.appointments_frame, text="Book Appointment", command=self.book_appointment, **btn_params)
        self.book_button.grid(row=5, column=0, pady=10, sticky="ew", padx=(10,5))

        tk.Label(self.appointments_frame, text="Upcoming Appointments", font=("Arial", 14, "bold"), fg=fg_color, bg=bg_color).grid(row=6, column=0, columnspan=4, pady=(20,5), sticky="w")

        self.appointments_listbox = tk.Listbox(self.appointments_frame, width=80, height=10,
                                              bg=listbox_bg, fg=listbox_fg, selectbackground=button_bg, selectforeground=button_fg,
                                              highlightbackground=bg_color, relief="flat")
        self.appointments_listbox.grid(row=7, column=0, columnspan=4, padx=10, pady=5, sticky="nsew")

        appts_scrollbar = tk.Scrollbar(self.appointments_frame, orient="vertical", command=self.appointments_listbox.yview)
        appts_scrollbar.grid(row=7, column=4, sticky="nsw", pady=5)
        self.appointments_listbox.config(yscrollcommand=appts_scrollbar.set)

        self.refresh_appointments_list()

        self.edit_appt_button = tk.Button(self.appointments_frame, text="Edit Selected", command=self.edit_appointment, **btn_params)
        self.edit_appt_button.grid(row=8, column=0, pady=10, sticky="ew", padx=(10,5))

        self.delete_appt_button = tk.Button(self.appointments_frame, text="Delete Selected", command=self.delete_appointment, **btn_params)
        self.delete_appt_button.grid(row=8, column=1, pady=10, sticky="ew", padx=5)

        self.refresh_button = tk.Button(self.appointments_frame, text="Refresh List", command=self.refresh_appointments_list, **btn_params)
        self.refresh_button.grid(row=8, column=2, pady=10, sticky="ew", padx=5)

        self.appointments_frame.grid_rowconfigure(4, weight=1)
        self.appointments_frame.grid_rowconfigure(7, weight=2)
        for col in range(5):
            self.appointments_frame.grid_columnconfigure(col, weight=1)

    def refresh_appt_treatment_list(self):
        self.appt_treatment_listbox.delete(0, tk.END)
        self.appt_treatment_keys = []
        for key, (treatment, cost) in self.clinic.get_treatments().items():
            self.appt_treatment_listbox.insert(tk.END, f"{treatment} - Rs. {cost}")
            self.appt_treatment_keys.append(key)

    def book_appointment(self):
        name = self.appt_name_entry.get().strip()
        phone = self.appt_phone_entry.get().strip()
        date = self.appt_date_entry.get().strip()
        time_slot = self.appt_time_entry.get().strip()

        if not all([name, phone, date, time_slot]):
            messagebox.showwarning("Input Error", "Please fill all fields.")
            return

        try:
            parsed_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            if parsed_date < datetime.date.today():
                messagebox.showwarning("Input Error", "Date must be today or in the future.")
                return
        except ValueError:
            messagebox.showwarning("Input Error", "Invalid date format. Use YYYY-MM-DD (e.g., 2024-10-15).")
            return

        try:
            parsed_time = datetime.datetime.strptime(time_slot, "%H:%M")
            if not (0 <= parsed_time.hour < 24 and 0 <= parsed_time.minute < 60):
                raise ValueError
        except ValueError:
            messagebox.showwarning("Input Error", "Invalid time format. Use HH:MM (e.g., 14:30).")
            return

        selected_indices = self.appt_treatment_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Input Error", "Please select at least one treatment.")
            return

        treatments = []
        for idx in selected_indices:
            key = self.appt_treatment_keys[idx]
            treatment = self.clinic.get_treatments()[key]
            treatments.append(treatment)

        appointment = Appointment(name, phone, date, time_slot, treatments)
        self.appointments.append(appointment)
        self.save_appointments()
        self.refresh_appointments_list()

        self.appt_name_entry.delete(0, tk.END)
        self.appt_phone_entry.delete(0, tk.END)
        self.appt_date_entry.delete(0, tk.END)
        self.appt_date_entry.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        self.appt_time_entry.delete(0, tk.END)
        self.appt_treatment_listbox.selection_clear(0, tk.END)

        messagebox.showinfo("Success", "Appointment booked successfully!")

    def refresh_appointments_list(self):
        self.appointments_listbox.delete(0, tk.END)
        upcoming = [appt for appt in self.appointments if appt.is_upcoming()]
        upcoming.sort(key=lambda x: datetime.datetime.strptime(x.date, "%Y-%m-%d"))  # Sort by date
        for appt in upcoming:
            self.appointments_listbox.insert(tk.END, str(appt))

    def edit_appointment(self):
        selected = self.appointments_listbox.curselection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select an appointment to edit.")
            return

        index = selected[0]
        upcoming = [appt for appt in self.appointments if appt.is_upcoming()]
        if index >= len(upcoming):
            messagebox.showwarning("Selection Error", "Invalid selection.")
            return

        appt = upcoming[index]
        full_index = self.appointments.index(appt)  # Original index in self.appointments

        edit_win = tk.Toplevel(self.root)
        edit_win.title("Edit Appointment")
        edit_win.geometry("500x450")
        edit_win.configure(bg=self.bg_color)
        edit_win.resizable(True, True)

        tk.Label(edit_win, text="Patient Name:", font=("Arial", 12, "bold"), fg=self.fg_color, bg=self.bg_color).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        name_entry = tk.Entry(edit_win, width=40, bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg)
        name_entry.grid(row=0, column=1, sticky="w", padx=5)
        name_entry.insert(0, appt.patient_name)

        tk.Label(edit_win, text="Phone:", font=("Arial", 12, "bold"), fg=self.fg_color, bg=self.bg_color).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        phone_entry = tk.Entry(edit_win, width=40, bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg)
        phone_entry.grid(row=1, column=1, sticky="w", padx=5)
        phone_entry.insert(0, appt.phone)

        tk.Label(edit_win, text="Date (YYYY-MM-DD):", font=("Arial", 12, "bold"), fg=self.fg_color, bg=self.bg_color).grid(row=2, column=0, sticky="w", padx=10, pady=5)
        date_entry = tk.Entry(edit_win, width=40, bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg)
        date_entry.grid(row=2, column=1, sticky="w", padx=5)
        date_entry.insert(0, appt.date)

        tk.Label(edit_win, text="Time (HH:MM):", font=("Arial", 12, "bold"), fg=self.fg_color, bg=self.bg_color).grid(row=3, column=0, sticky="w", padx=10, pady=5)
        time_entry = tk.Entry(edit_win, width=40, bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg)
        time_entry.grid(row=3, column=1, sticky="w", padx=5)
        time_entry.insert(0, appt.time_slot)

        tk.Label(edit_win, text="Select Treatments:", font=("Arial", 12, "bold"), fg=self.fg_color, bg=self.bg_color).grid(row=4, column=0, sticky="w", padx=10, pady=5)

        edit_treat_listbox = tk.Listbox(edit_win, selectmode=tk.MULTIPLE, width=50, height=6,
                                        bg=self.listbox_bg, fg=self.listbox_fg, selectbackground=self.button_bg, selectforeground=self.button_fg,
                                        highlightbackground=self.bg_color, relief="flat")
        edit_treat_listbox.grid(row=5, column=0, columnspan=2, padx=10, sticky="nsew")

        edit_treat_scrollbar = tk.Scrollbar(edit_win, orient="vertical", command=edit_treat_listbox.yview)
        edit_treat_scrollbar.grid(row=5, column=2, sticky="nsw", pady=5)
        edit_treat_listbox.config(yscrollcommand=edit_treat_scrollbar.set)

        edit_treat_keys = []
        for key, (treatment, cost) in self.clinic.get_treatments().items():
            edit_treat_listbox.insert(tk.END, f"{treatment} - Rs. {cost}")
            edit_treat_keys.append(key)

        current_treat_names = {name for name, _ in appt.treatments}
        for i, (name, _) in enumerate(self.clinic.get_treatments().values()):
            if name in current_treat_names:
                edit_treat_listbox.selection_set(i)

        def save_edit():
            new_name = name_entry.get().strip()
            new_phone = phone_entry.get().strip()
            new_date = date_entry.get().strip()
            new_time = time_entry.get().strip()

            if not all([new_name, new_phone, new_date, new_time]):
                messagebox.showwarning("Input Error", "Please fill all fields.")
                return

            try:
                parsed_date = datetime.datetime.strptime(new_date, "%Y-%m-%d").date()
                if parsed_date < datetime.date.today():
                    messagebox.showwarning("Input Error", "Date must be today or in the future.")
                    return
            except ValueError:
                messagebox.showwarning("Input Error", "Invalid date format. Use YYYY-MM-DD.")
                return

            try:
                parsed_time = datetime.datetime.strptime(new_time, "%H:%M")
                if not (0 <= parsed_time.hour < 24 and 0 <= parsed_time.minute < 60):
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Input Error", "Invalid time format. Use HH:MM (e.g., 14:30).")
                return

            selected_treat_indices = edit_treat_listbox.curselection()
            if not selected_treat_indices:
                messagebox.showwarning("Input Error", "Please select at least one treatment.")
                return

            new_treatments = []
            for idx in selected_treat_indices:
                key = edit_treat_keys[idx]
                treatment = self.clinic.get_treatments()[key]
                new_treatments.append(treatment)

            self.appointments[full_index].patient_name = new_name
            self.appointments[full_index].phone = new_phone
            self.appointments[full_index].date = new_date
            self.appointments[full_index].time_slot = new_time
            self.appointments[full_index].treatments = new_treatments

            self.save_appointments()
            self.refresh_appointments_list()
            edit_win.destroy()
            messagebox.showinfo("Success", "Appointment updated successfully!")

        save_btn = tk.Button(edit_win, text="Save Changes", command=save_edit,
                             bg=self.button_bg, fg=self.button_fg, font=("Arial", 12, "bold"), relief="flat",
                             activebackground="#1565C0", activeforeground=self.button_fg)
        save_btn.grid(row=6, column=0, columnspan=3, pady=10)

        edit_win.grid_rowconfigure(5, weight=1)
        edit_win.grid_columnconfigure(1, weight=1)

    def delete_appointment(self):
        selected = self.appointments_listbox.curselection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select an appointment to delete.")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected appointment? This cannot be undone."):
            index = selected[0]
            upcoming = [appt for appt in self.appointments if appt.is_upcoming()]
            if index < len(upcoming):
                full_index = self.appointments.index(upcoming[index])
                del self.appointments[full_index]
                self.save_appointments()
                self.refresh_appointments_list()
                messagebox.showinfo("Success", "Appointment deleted successfully!")
            else:
                messagebox.showwarning("Error", "Invalid selection. Please try again.")


if __name__ == "__main__":
    root = tk.Tk()
    clinic = DentalClinic("Bright Smile Dental Clinic")
    app = DentalClinicGUI(root, clinic)
    root.mainloop()