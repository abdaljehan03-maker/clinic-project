import os
import datetime
import re
import tkinter as tk
import tkinter.simpledialog as simpledialog
import tkinter.messagebox as messagebox
import tempfile
import platform
import subprocess

from abc import ABC, abstractmethod

# -------------------------
# Abstraction: Base class
# -------------------------
class Billable(ABC):
    @abstractmethod
    def calculate_total(self):
        pass

# -------------------------
# Encapsulation & Inheritance: Clinic
# -------------------------
class Clinic:
    def __init__(self, name):
        self._name = name

    def get_clinic_name(self):
        return self._name

# -------------------------
# DentalClinic: treatments
# -------------------------
class DentalClinic(Clinic):
    def __init__(self, name):
        super().__init__(name)
        self._treatments = {
            1: ("Dental Check-up & Consultation", 2000),
            2: ("Teeth Cleaning (Scaling & Polishing)", 7000),
            3: ("Tooth Extraction", 2500),
            4: ("Dental Fillings (Cavity Treatment)", 5000),
            5: ("Root Canal Treatment", 15000),      
            6: ("Teeth Whitening", 12000),           
            7: ("Braces Consultation", 5000)         
        }

    def get_treatments(self):
        return self._treatments

# -------------------------
# Patient class (encapsulation)
# -------------------------
class Patient(Billable):
    def __init__(self, name, phone):
        self._name = name.strip()
        self._phone = phone.strip()
        self._treatments = []  # list of tuples (treatment_name, cost)

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
        combined_path = os.path.join(script_dir, combined_filename)
        individual_path = None

        # Write combined (append)
        try:
            with open(combined_path, "a", encoding="utf-8") as f:
                f.write(bill_text + "\n\n")
        except Exception as e:
            print(f"Error saving combined bill file ({combined_path}): {e}")

        # Write individual file (overwrite just this bill)
        if make_individual:
            safe_name = re.sub(r'[^A-Za-z0-9_\-]+', '_', self._name) or "patient"
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            individual_name = f"{safe_name}_bill_{timestamp}.txt"
            individual_path = os.path.join(script_dir, individual_name)
            try:
                with open(individual_path, "w", encoding="utf-8") as f:
                    f.write(bill_text + "\n")
            except Exception as e:
                print(f"Error saving individual bill file ({individual_path}): {e}")

        return combined_path, individual_path

# -------------------------
# VIPPatient (polymorphism)
# -------------------------
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

# -------------------------
# GUI Application
# -------------------------
class DentalClinicGUI:
    def __init__(self, root, clinic):
        self.root = root
        self.clinic = clinic
        self.patient = None

        # Modern color palette
        bg_color = "#2E3741"          # Dark blue-gray background
        fg_color = "#D8DEE9"          # Light text color
        accent_color = "#5E81AC"      # Blue accent for buttons and ribbons
        button_bg = "#4C566A"         # Button background
        button_fg = "#ECEFF4"         # Button text color
        entry_bg = "#3B4252"          # Entry background
        entry_fg = "#D8DEE9"          # Entry text color
        text_bg = "#3B4252"           # Text widget background
        text_fg = "#D8DEE9"           # Text widget text color

        root.title("Bright Smile Dental Clinic Billing System")
        root.geometry("700x850")
        root.resizable(True, True)
        root.configure(bg=bg_color)

        # Ribbon bar frame at the top
        self.ribbon_frame = tk.Frame(root, bg=accent_color, height=50)
        self.ribbon_frame.grid(row=0, column=0, columnspan=5, sticky="ew")
        self.ribbon_frame.grid_propagate(False)  # Fix height

        # Clinic name label in ribbon
        self.ribbon_label = tk.Label(self.ribbon_frame, text=self.clinic.get_clinic_name(),
                                     font=("Arial", 20, "bold"), fg=fg_color, bg=accent_color)
        self.ribbon_label.pack(expand=True)

        # Patient Type (row 1)
        self.patient_type_var = tk.StringVar(value="normal")
        tk.Label(root, text="Patient Type:", font=("Arial", 12, "bold"), fg=fg_color, bg=bg_color).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        tk.Radiobutton(root, text="Normal", variable=self.patient_type_var, value="normal", command=self.toggle_discount,
                       bg=bg_color, fg=fg_color, selectcolor=bg_color, activebackground=bg_color, activeforeground=fg_color).grid(row=1, column=1, sticky="w")
        tk.Radiobutton(root, text="VIP", variable=self.patient_type_var, value="vip", command=self.toggle_discount,
                       bg=bg_color, fg=fg_color, selectcolor=bg_color, activebackground=bg_color, activeforeground=fg_color).grid(row=1, column=2, sticky="w")

        # Patient Name (row 2)
        tk.Label(root, text="Patient Name:", font=("Arial", 12, "bold"), fg=fg_color, bg=bg_color).grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.name_entry = tk.Entry(root, width=40, bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)
        self.name_entry.grid(row=2, column=1, columnspan=2, sticky="w")

        # Patient Phone (row 3)
        tk.Label(root, text="Phone:", font=("Arial", 12, "bold"), fg=fg_color, bg=bg_color).grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.phone_entry = tk.Entry(root, width=40, bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)
        self.phone_entry.grid(row=3, column=1, columnspan=2, sticky="w")

        # VIP Discount (row 4)
        tk.Label(root, text="VIP Discount (%):", font=("Arial", 12, "bold"), fg=fg_color, bg=bg_color).grid(row=4, column=0, sticky="w", padx=10, pady=5)
        self.discount_entry = tk.Entry(root, width=10, bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)
        self.discount_entry.grid(row=4, column=1, sticky="w")
        self.discount_entry.insert(0, "10")
        self.discount_entry.config(state="disabled")  # Disabled by default

        # Treatments Label (row 5)
        tk.Label(root, text="Select Treatments:", font=("Arial", 12, "bold"), fg=fg_color, bg=bg_color).grid(row=5, column=0, sticky="w", padx=10, pady=5)

        # Treatments Listbox with scrollbar (row 6)
        self.treatment_listbox = tk.Listbox(root, selectmode=tk.MULTIPLE, width=50, height=8,
                                            bg=text_bg, fg=text_fg, selectbackground=accent_color, selectforeground=fg_color,
                                            highlightbackground=bg_color, relief="flat")
        self.treatment_listbox.grid(row=6, column=0, columnspan=3, padx=10, sticky="nsew")

        scrollbar = tk.Scrollbar(root, orient="vertical", command=self.treatment_listbox.yview, bg=bg_color)
        scrollbar.grid(row=6, column=3, sticky="nsw", pady=5)
        self.treatment_listbox.config(yscrollcommand=scrollbar.set)

        # Populate treatments
        self.refresh_treatment_list()

        # Buttons row (row 7)
        btn_params = {"font": ("Arial", 12, "bold"), "bg": button_bg, "fg": button_fg, "activebackground": accent_color, "activeforeground": fg_color, "relief": "flat"}

        self.generate_button = tk.Button(root, text="Generate Bill", command=self.generate_bill, **btn_params)
        self.generate_button.grid(row=7, column=0, pady=15, sticky="ew", padx=(10,5))

        self.clear_button = tk.Button(root, text="Clear Form", command=self.clear_inputs, **btn_params)
        self.clear_button.grid(row=7, column=1, pady=15, sticky="ew", padx=5)

        self.edit_treatment_button = tk.Button(root, text="Edit Treatments", command=self.edit_treatments, **btn_params)
        self.edit_treatment_button.grid(row=7, column=2, pady=15, sticky="ew", padx=5)

        self.edit_price_button = tk.Button(root, text="Edit Prices", command=self.edit_prices, **btn_params)
        self.edit_price_button.grid(row=7, column=3, pady=15, sticky="ew", padx=5)

        self.print_button = tk.Button(root, text="Print Bill & Prescription ", command=self.print_bill_and_prescription, **btn_params)
        self.print_button.grid(row=7, column=4, pady=15, sticky="ew", padx=(5,10))

        # Bill Text Box with border frame (row 8)
        self.bill_frame = tk.Frame(root, bd=1, relief="solid", bg=bg_color)
        self.bill_frame.grid(row=8, column=0, columnspan=5, padx=10, pady=10, sticky="nsew")

        self.bill_text = tk.Text(self.bill_frame, width=80, height=15, font=("Courier", 10),
                                 wrap="none", borderwidth=0, bg=text_bg, fg=text_fg, insertbackground=fg_color)
        self.bill_text.pack(side="left", fill="both", expand=True)

        # Scrollbars for bill text
        self.bill_scroll_y = tk.Scrollbar(self.bill_frame, orient="vertical", command=self.bill_text.yview, bg=bg_color)
        self.bill_scroll_y.pack(side="right", fill="y")
        self.bill_text.config(yscrollcommand=self.bill_scroll_y.set)

        self.bill_scroll_x = tk.Scrollbar(root, orient="horizontal", command=self.bill_text.xview, bg=bg_color)
        self.bill_scroll_x.grid(row=9, column=0, columnspan=5, sticky="ew", padx=10)
        self.bill_text.config(xscrollcommand=self.bill_scroll_x.set)

        # Add edge lines on right and bottom by adding thin frames
        self.right_edge = tk.Frame(self.bill_frame, width=2, bg=accent_color)
        self.right_edge.pack(side="right", fill="y")

        self.bottom_edge = tk.Frame(root, height=2, bg=accent_color)
        self.bottom_edge.grid(row=10, column=0, columnspan=5, sticky="ew", padx=10)

        # Prescription Label (row 11)
        tk.Label(root, text="Prescription (manual entry):", font=("Arial", 12, "bold"), fg=fg_color, bg=bg_color).grid(row=11, column=0, sticky="w", padx=10, pady=5)

        # Prescription Text Box with border frame (row 12)
        self.prescription_frame = tk.Frame(root, bd=1, relief="solid", bg=bg_color)
        self.prescription_frame.grid(row=12, column=0, columnspan=5, padx=10, pady=5, sticky="nsew")

        self.prescription_text = tk.Text(self.prescription_frame, width=80, height=8, font=("Courier", 10),
                                         wrap="word", borderwidth=0, bg=text_bg, fg=text_fg, insertbackground=fg_color)
        self.prescription_text.pack(side="left", fill="both", expand=True)

        self.prescription_scroll_y = tk.Scrollbar(self.prescription_frame, orient="vertical", command=self.prescription_text.yview, bg=bg_color)
        self.prescription_scroll_y.pack(side="right", fill="y")
        self.prescription_text.config(yscrollcommand=self.prescription_scroll_y.set)

        # Configure grid weights for resizing
        root.grid_rowconfigure(6, weight=1)   # Treatments listbox row
        root.grid_rowconfigure(8, weight=3)   # Bill text row
        root.grid_rowconfigure(12, weight=3)  # Prescription text row

        for col in range(5):
            root.grid_columnconfigure(col, weight=1)

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

        # Add current date and time at the top of the bill text
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_text = f"Date & Time: {now_str}\n{bill_text}"

        self.bill_text.delete(1.0, tk.END)
        self.bill_text.insert(tk.END, full_text)

        self.patient.save_bill_to_files(full_text)

    def edit_treatments(self):
        treatments = self.clinic.get_treatments()
        edit_win = tk.Toplevel(self.root)
        edit_win.title("Edit Treatments")
        edit_win.geometry("400x300")
        tk.Label(edit_win, text="Treatments (one per line):", font=("Arial", 12, "bold")).pack(pady=5)

        text_box = tk.Text(edit_win, width=40, height=10)
        text_box.pack(padx=10, pady=5)

        for key in sorted(treatments.keys()):
            text_box.insert(tk.END, treatments[key][0] + "\n")

        def save_treatments():
            lines = text_box.get(1.0, tk.END).strip().split("\n")
            if not lines:
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
            edit_win.destroy()

        save_btn = tk.Button(edit_win, text="Save", command=save_treatments)
        save_btn.pack(pady=10)

    def edit_prices(self):
        treatments = self.clinic.get_treatments()
        edit_win = tk.Toplevel(self.root)
        edit_win.title("Edit Prices")
        edit_win.geometry("400x300")

        tk.Label(edit_win, text="Edit Prices (treatment: price):", font=("Arial", 12, "bold")).pack(pady=5)       
        text_box = tk.Text(edit_win, width=40, height=10)
        text_box.pack(padx=10, pady=5)

        for key in sorted(treatments.keys()):
            name, price = treatments[key]
            text_box.insert(tk.END, f"{name}: {price}\n")

        def save_prices():
            lines = text_box.get(1.0, tk.END).strip().split("\n")
            new_treatments = {}
            for i, line in enumerate(lines, 1):
                if ':' not in line:
                    messagebox.showwarning("Input Error", f"Line {i} is invalid. Use 'Treatment: price' format.")
                    return
                name, price_str = line.split(':', 1)
                name = name.strip()
                price_str = price_str.strip()
                if not name:
                    messagebox.showwarning("Input Error", f"Line {i} has empty treatment name.")
                    return
                try:
                    price = float(price_str)
                    if price < 0:
                        messagebox.showwarning("Input Error", f"Line {i} has negative price.")
                        return
                except ValueError:
                    messagebox.showwarning("Input Error", f"Line {i} has invalid price.")
                    return
                new_treatments[i] = (name, price)
            if not new_treatments:
                messagebox.showwarning("Input Error", "At least one valid treatment is required.")
                return
            self.clinic._treatments = new_treatments
            self.refresh_treatment_list()
            edit_win.destroy()

        save_btn = tk.Button(edit_win, text="Save", command=save_prices)
        save_btn.pack(pady=10)

    def print_bill_and_prescription(self):
        bill_content = self.bill_text.get(1.0, tk.END).strip()
        prescription_content = self.prescription_text.get(1.0, tk.END).strip()

        if not bill_content:
            messagebox.showwarning("Print Error", "No bill to print. Please generate a bill first.")
            return

        combined_text = bill_content + "\n\n===== Prescription =====\n" + (prescription_content if prescription_content else "(No prescription entered)")

        # Save combined text to a temporary file
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp_file:
                tmp_file.write(combined_text)
                temp_filename = tmp_file.name
        except Exception as e:
            messagebox.showerror("Print Error", f"Failed to create temporary file for printing: {e}")
            return

        # Platform-specific print command
        system_name = platform.system()
        try:
            if system_name == "Windows":
                # Use os.startfile with "print" operation on Windows
                os.startfile(temp_filename, "print")
            elif system_name == "Darwin":
                # macOS: use 'lp' command
                subprocess.run(["lp", temp_filename])
            else:
                # Linux and others: use 'lp' command
                subprocess.run(["lp", temp_filename])
        except Exception as e:
            messagebox.showerror("Print Error", f"Failed to send file to printer: {e}")
            return

        messagebox.showinfo("Print", "The bill and prescription have been sent to the printer.")


if __name__ == "__main__":
    root = tk.Tk()
    clinic = DentalClinic("Bright Smile Dental Clinic")
    app = DentalClinicGUI(root, clinic)
    root.mainloop()
