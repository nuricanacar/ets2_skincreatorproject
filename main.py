import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
from wand.image import Image as WandImage
import struct
import zipfile
import os
import tempfile
import threading
import json
import concurrent.futures
import multiprocessing

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DLC_DIR = os.path.join(_SCRIPT_DIR, "dlc_valentine")
JSON_FILE = os.path.join(_SCRIPT_DIR, "extracted_coords.json")

# 1. Load dynamic JSON coords
try:
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        JSON_COORDS = json.load(f)
except FileNotFoundError:
    JSON_COORDS = {}
except json.JSONDecodeError:
    JSON_COORDS = {}

def place_logo_in_box(canvas, logo_img, bbox, alignment):
    """
    Places logo within bounding box defined by {"x": x, "y": y, "w": w, "h": h}.
    Scale: fits the bounding box scaling without breaking aspect ratio.
    Alignment:
      'bottom-left'  -> Left Door
      'bottom-right' -> Right Door
      'center'       -> Hood, Roof, C-Pillars, Side Skirts
    """
    x1 = bbox["x"]
    y1 = bbox["y"]
    box_w = bbox["w"]
    box_h = bbox["h"]
    x2 = x1 + box_w
    y2 = y1 + box_h

    orig_w, orig_h = logo_img.size

    # Target height = 100% of bounding box height to maximize the Safe Zone usage
    target_h = int(box_h * 1.0)
    if target_h < 1:
        return

    # Scale logo maintaining aspect ratio
    scale = target_h / orig_h
    target_w = int(orig_w * scale)
    
    # If scaled width exceeds box width, shrink to fit width instead
    if target_w > box_w:
        target_w = box_w
        scale = target_w / orig_w
        target_h = int(orig_h * scale)

    if target_w < 1 or target_h < 1:
        return

    resized = logo_img.resize((target_w, target_h), Image.LANCZOS)

    if alignment == 'bottom-left':
        # Near bottom-left corner
        px = x1
        py = y2 - target_h
    elif alignment == 'bottom-right':
        # Near bottom-right corner
        px = x2 - target_w
        py = y2 - target_h
    elif alignment == 'center':
        # Dead-center within the bounding box
        px = x1 + (box_w - target_w) // 2
        py = y1 + (box_h - target_h) // 2
    else:
        return

    # Safety clamp
    px = max(px, x1)
    py = max(py, y1)
    if px + target_w > x2:
        px = x2 - target_w
    if py + target_h > y2:
        py = y2 - target_h

    canvas.paste(resized, (px, py), mask=resized)

def apply_concrete_alpha_fix(img):
    """
    Ensures that any pixel belonging to the logo (Alpha > 0)
    is forced to full opacity (Alpha = 255) to prevent faded logos in-game.
    Transparent backgrounds remain transparent (Alpha = 0).
    """
    img = img.convert("RGBA")
    r, g, b, a = img.split()
    a = a.point(lambda p: 255 if p > 0 else 0)
    return Image.merge("RGBA", (r, g, b, a))

def extract_tobj_header(dlc_base_dir):
    """
    Dynamically extracts the TRUE binary header from an official SCS .tobj file.
    """
    for root, dirs, files in os.walk(dlc_base_dir):
        for fname in files:
            if fname.endswith('.tobj'):
                fpath = os.path.join(root, fname)
                with open(fpath, 'rb') as f:
                    data = f.read()
                marker_idx = data.find(b'/vehicle/')
                if marker_idx != -1 and marker_idx >= 8:
                    header = data[:marker_idx - 8]
                    return header
    raise FileNotFoundError(f"Could not find any valid .tobj file with '/vehicle/' path in: {dlc_base_dir}")

try:
    _TRUE_TOBJ_HEADER = extract_tobj_header(_DLC_DIR)
except FileNotFoundError:
    _TRUE_TOBJ_HEADER = (
        b'\x01\x0A\xB1\x70'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x01\x00\x00\x00'
        b'\x02\x00\x01\x01\x01\x00\x02\x02'
        b'\x00\x00\x00\x00\x00\x01\x00\x00'
    )

def write_tobj(tobj_path, target_path_str):
    """
    Generates a valid ETS2 binary TOBJ file mapping to the texture path.
    """
    path_bytes = target_path_str.encode('ascii')
    with open(tobj_path, 'wb') as f:
        f.write(_TRUE_TOBJ_HEADER)
        f.write(struct.pack('<I', len(path_bytes)))
        f.write(b'\x00\x00\x00\x00')
        f.write(path_bytes)

def generate_base_sii_content(truck_internal_name, tex_name):
    """
    Generates the dynamic base .sii definition file content for a specific truck.
    Points to the first cabin's .tobj as the default texture.
    """
    content = "SiiNunit\n{\n"
    content += f"accessory_paint_job_data : unisk.{truck_internal_name}.paint_job\n"
    content += "{\n"
    content += '    name: "Custom Logo Skin"\n'
    content += "    price: 1000\n"
    content += "    unlock: 1\n"
    content += '    icon: "paintjob_default"\n'
    content += "    airbrush: true\n"
    content += "    base_color: (1.0, 1.0, 1.0)\n"
    content += f'    paint_job_mask: "/vehicle/truck/upgrade/paintjob/my_mod/{tex_name}.tobj"\n'
    content += "}\n}\n"
    return content

def generate_override_sii_content(truck_internal_name, cabin_internal_name, tex_name):
    """
    Generates the accessory override .sii file specific to a cabin.
    """
    content = "SiiNunit\n{\n"
    content += "simple_paint_job_data : .ovr0\n"
    content += "{\n"
    content += f'    paint_job_mask: "/vehicle/truck/upgrade/paintjob/my_mod/{tex_name}.tobj"\n'
    content += f'    suitable_for[]: "{cabin_internal_name}.{truck_internal_name}.cabin"\n'
    content += "}\n}\n"
    return content

def generate_cabin_assets(args):
    """
    Multiprocessing worker function that builds the 4096x4096 texture,
    applies Wand compression, and generates the tobj for a single cabin.
    """
    truck_internal_name, cabin_internal_name, coords, ui_states, logo_path, tmp_dir = args
    do_doors, do_hood, do_roof, do_cpillar_upper, do_cpillar_lower = ui_states
    
    tex_name = f"{truck_internal_name}_{cabin_internal_name}"
    temp_png = os.path.join(tmp_dir, f"{tex_name}.png")
    temp_dds = os.path.join(tmp_dir, f"{tex_name}.dds")
    temp_tobj = os.path.join(tmp_dir, f"{tex_name}.tobj")
    
    logo_img = Image.open(logo_path).convert("RGBA")
    canvas = Image.new("RGBA", (4096, 4096), (0, 0, 0, 0))

    if do_doors:
        if "left_door" in coords:
            place_logo_in_box(canvas, logo_img, coords["left_door"], 'bottom-left')
        if "right_door" in coords:
            place_logo_in_box(canvas, logo_img, coords["right_door"], 'bottom-right')
            
    if do_hood and "hood" in coords:
        place_logo_in_box(canvas, logo_img, coords["hood"], 'center')

    if do_roof and "roof" in coords:
        place_logo_in_box(canvas, logo_img, coords["roof"], 'center')

    if do_cpillar_upper:
        if "left_c_pillar_upper" in coords:
            place_logo_in_box(canvas, logo_img, coords["left_c_pillar_upper"], 'center')
        if "right_c_pillar_upper" in coords:
            place_logo_in_box(canvas, logo_img, coords["right_c_pillar_upper"], 'center')

    if do_cpillar_lower:
        if "left_c_pillar_lower" in coords:
            place_logo_in_box(canvas, logo_img, coords["left_c_pillar_lower"], 'center')
        if "right_c_pillar_lower" in coords:
            place_logo_in_box(canvas, logo_img, coords["right_c_pillar_lower"], 'center')

    final_texture = apply_concrete_alpha_fix(canvas)
    final_texture.save(temp_png, format="PNG")

    with WandImage(filename=temp_png) as wand_img:
        wand_img.compression = 'dxt5'
        wand_img.save(filename=temp_dds)

    tobj_in_game_path = f"/vehicle/truck/upgrade/paintjob/my_mod/{tex_name}.dds"
    write_tobj(temp_tobj, tobj_in_game_path)

    return {
        'truck': truck_internal_name,
        'cabin': cabin_internal_name,
        'tex_name': tex_name,
        'dds_path': temp_dds,
        'tobj_path': temp_tobj,
        'png_path': temp_png
    }


class SkinGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ETS2 Universal Skin Generator")
        self.root.geometry("450x420")
        
        self.logo_path = tk.StringVar()
        
        self.var_all = tk.BooleanVar(value=True)
        self.var_doors = tk.BooleanVar(value=True)
        self.var_hood = tk.BooleanVar(value=True)
        self.var_roof = tk.BooleanVar(value=True)
        self.var_cpillar_upper = tk.BooleanVar(value=True)
        self.var_cpillar_lower = tk.BooleanVar(value=True)
        
        self.part_vars = [
            self.var_doors, self.var_hood, self.var_roof, 
            self.var_cpillar_upper, self.var_cpillar_lower
        ]
        
        self.create_widgets()
        
        if not JSON_COORDS:
            messagebox.showerror("Error", "Could not load extracted_coords.json!\nPlease ensure the coordinate_hunter.py script has been run.")

    def create_widgets(self):
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(frame, text="ETS2 Mod Tool", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=(0, 10))

        logo_frame = ttk.Frame(frame)
        logo_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(logo_frame, text="Logo (.png):").pack(side=tk.LEFT)
        ttk.Entry(logo_frame, textvariable=self.logo_path, state="readonly", width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(logo_frame, text="Browse", command=self.browse_logo).pack(side=tk.LEFT)

        # New UI Section (Part Selection Checkboxes)
        parts_frame = ttk.LabelFrame(frame, text="Parts to Paint", padding=10)
        parts_frame.pack(fill=tk.X, pady=15)
        
        ttk.Checkbutton(parts_frame, text="All Parts", variable=self.var_all, command=self.toggle_all).pack(anchor=tk.W)
        ttk.Separator(parts_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        ttk.Checkbutton(parts_frame, text="Doors (Left & Right)", variable=self.var_doors, command=self.check_part_state).pack(anchor=tk.W)
        ttk.Checkbutton(parts_frame, text="Hood", variable=self.var_hood, command=self.check_part_state).pack(anchor=tk.W)
        ttk.Checkbutton(parts_frame, text="Roof", variable=self.var_roof, command=self.check_part_state).pack(anchor=tk.W)
        ttk.Checkbutton(parts_frame, text="Upper C-Pillars", variable=self.var_cpillar_upper, command=self.check_part_state).pack(anchor=tk.W)
        ttk.Checkbutton(parts_frame, text="Lower Side Skirts", variable=self.var_cpillar_lower, command=self.check_part_state).pack(anchor=tk.W)

        self.generate_btn = ttk.Button(frame, text="Create Mod (.scs)", command=self.create_mod)
        self.generate_btn.pack(pady=10)

    def toggle_all(self):
        state = self.var_all.get()
        for var in self.part_vars:
            var.set(state)

    def check_part_state(self):
        if all(var.get() for var in self.part_vars):
            self.var_all.set(True)
        else:
            self.var_all.set(False)

    def browse_logo(self):
        filepath = filedialog.askopenfilename(
            title="Select Logo",
            filetypes=[("PNG Images", "*.png")]
        )
        if filepath:
            self.logo_path.set(filepath)

    def create_mod(self):
        if not JSON_COORDS:
            messagebox.showerror("Error", "Missing extracted_coords.json! Cannot build mod.")
            return

        logo_file = self.logo_path.get()
        if not logo_file:
            messagebox.showerror("Error", "Please select a logo PNG file.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Save SCS Mod",
            defaultextension=".scs",
            filetypes=[("SCS Mod", "*.scs")]
        )
        if not save_path:
            return

        self.generate_btn.config(state=tk.DISABLED)
        
        self.progress_win = tk.Toplevel(self.root)
        self.progress_win.title("Generating Mod...")
        self.progress_win.geometry("350x120")
        self.progress_win.transient(self.root)
        self.progress_win.grab_set()
        
        ttk.Label(self.progress_win, text="Processing textures on all CPU cores...").pack(pady=(15, 5))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_win, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=20, pady=5)
        
        self.status_var = tk.StringVar(value="Starting...")
        ttk.Label(self.progress_win, textvariable=self.status_var).pack()

        # The thread keeps the GUI completely responsive during execution
        thread = threading.Thread(target=self._run_process_mod, args=(logo_file, save_path))
        thread.daemon = True
        thread.start()

    def _run_process_mod(self, logo_file, save_path):
        try:
            self.process_mod(logo_file, save_path)
            self.root.after(0, self._on_process_success, save_path)
        except Exception as e:
            self.root.after(0, self._on_process_error, str(e))

    def _on_process_success(self, save_path):
        self.progress_win.destroy()
        self.generate_btn.config(state=tk.NORMAL)
        messagebox.showinfo("Success", f"Mod successfully created at:\n{save_path}")

    def _on_process_error(self, error_msg):
        self.progress_win.destroy()
        self.generate_btn.config(state=tk.NORMAL)
        messagebox.showerror("Error", f"Failed to generate mod:\n{error_msg}")

    def process_mod(self, logo_path, out_scs_path):
        ui_states = (
            self.var_doors.get(),
            self.var_hood.get(),
            self.var_roof.get(),
            self.var_cpillar_upper.get(),
            self.var_cpillar_lower.get()
        )
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Count total cabins to process for the progress bar
            total_cabins = sum(len(cabins) for cabins in JSON_COORDS.values())
            if total_cabins == 0:
                raise ValueError("JSON file contains no truck/cabin data!")

            tasks = []
            for truck_internal_name, cabins in JSON_COORDS.items():
                for cabin_internal_name, coords in cabins.items():
                    tasks.append((truck_internal_name, cabin_internal_name, coords, ui_states, logo_path, tmp_dir))

            cabin_count = 0
            processed_trucks = set()

            with zipfile.ZipFile(out_scs_path, 'w', zipfile.ZIP_STORED) as scs:
                
                # Multiprocessing significantly speeds up the Wand DXT5 compression bounds.
                # max_workers caps threads to available CPUs, ensuring efficient CPU load mapping.
                max_workers = max(1, multiprocessing.cpu_count() - 1)
                
                with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
                    futures = {executor.submit(generate_cabin_assets, task): task for task in tasks}
                    
                    for future in concurrent.futures.as_completed(futures):
                        result = future.result()
                        
                        truck = result['truck']
                        cabin = result['cabin']
                        tex_name = result['tex_name']
                        
                        # Read generated files from tmp_dir
                        with open(result['dds_path'], 'rb') as f:
                            dds_bytes = f.read()
                        with open(result['tobj_path'], 'rb') as f:
                            tobj_bytes = f.read()
                            
                        # Clean up temp files immediately to free up disk space during parallel runs
                        try:
                            os.remove(result['dds_path'])
                            os.remove(result['tobj_path'])
                            os.remove(result['png_path'])
                        except OSError:
                            pass

                        # Write the individual assets to the .scs
                        scs.writestr(f"vehicle/truck/upgrade/paintjob/my_mod/{tex_name}.dds", dds_bytes)
                        scs.writestr(f"vehicle/truck/upgrade/paintjob/my_mod/{tex_name}.tobj", tobj_bytes)

                        # Write the specific .sii definitions
                        # Create the Base Paintjob (universal_skin.sii) using the FIRST cabin's texture
                        if truck not in processed_trucks:
                            base_sii_content = generate_base_sii_content(truck, tex_name)
                            base_sii_path = f"def/vehicle/truck/{truck}/paint_job/universal_skin.sii"
                            scs.writestr(base_sii_path, base_sii_content.encode('utf-8'))
                            processed_trucks.add(truck)

                        # Create the Accessory Override (.sii) specifically for this cabin
                        override_sii_content = generate_override_sii_content(truck, cabin, tex_name)
                        override_sii_path = f"def/vehicle/truck/{truck}/paint_job/unisk/{cabin}.sii"
                        scs.writestr(override_sii_path, override_sii_content.encode('utf-8'))
                        
                        cabin_count += 1
                        
                        # Use .after to safely communicate back to the Main Tkinter Thread
                        def update_status(t=truck, c=cabin, i=cabin_count):
                            self.status_var.set(f"Processed: {t} ({c}) - {i}/{total_cabins}")
                            self.progress_var.set((i / total_cabins) * 100)
                        self.root.after(0, update_status)


if __name__ == "__main__":
    # Required for Windows multiprocessing to work correctly!
    multiprocessing.freeze_support()
    root = tk.Tk()
    app = SkinGeneratorApp(root)
    root.mainloop()
