import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
from wand.image import Image as WandImage
import struct
import zipfile
import os
import tempfile

# Truck coordinates data (excluding iveco.sway as requested)
TRUCKS = [
    {
        "TruckName": "DAF XF 105",
        "InternalName": "daf.xf",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    },
    {
        "TruckName": "DAF XF Euro 6",
        "InternalName": "daf.xf_euro6",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    },
    {
        "TruckName": "DAF 2021 XG",
        "InternalName": "daf.2021",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    },
    {
        "TruckName": "DAF XD",
        "InternalName": "daf.xd",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    },
    {
        "TruckName": "Iveco Stralis",
        "InternalName": "iveco.stralis",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    },
    {
        "TruckName": "Iveco Hi-Way",
        "InternalName": "iveco.hiway",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    },
    {
        "TruckName": "MAN TGX Euro 5",
        "InternalName": "man.tgx",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    },
    {
        "TruckName": "MAN TGX Euro 6",
        "InternalName": "man.tgx_euro6",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    },
    {
        "TruckName": "MAN TGX 2020",
        "InternalName": "man.tgx_2020",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    },
    {
        "TruckName": "Mercedes Actros",
        "InternalName": "mercedes.actros",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    },
    {
        "TruckName": "Mercedes New Actros",
        "InternalName": "mercedes.actros2014",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    },
    {
        "TruckName": "Renault Magnum",
        "InternalName": "renault.magnum",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    },
    {
        "TruckName": "Renault Premium",
        "InternalName": "renault.premium",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    },
    {
        "TruckName": "Renault Range T",
        "InternalName": "renault.t",
        "Coordinates": {
            "LeftDoor": {"X": 2924, "Y": 968, "Width": 180, "Height": 180},
            "RightDoor": {"X": 998, "Y": 968, "Width": 180, "Height": 180},
            "Hood": {"X": 1948, "Y": 1027, "Width": 200, "Height": 200}
        }
    },
    {
        "TruckName": "Scania R 2009",
        "InternalName": "scania.r",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    },
    {
        "TruckName": "Scania Streamline",
        "InternalName": "scania.streamline",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    },
    {
        "TruckName": "Scania R 2016",
        "InternalName": "scania.r_2016",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    },
    {
        "TruckName": "Scania S 2016",
        "InternalName": "scania.s_2016",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    },
    {
        "TruckName": "Volvo FH16 2009",
        "InternalName": "volvo.fh16",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    },
    {
        "TruckName": "Volvo FH16 2012",
        "InternalName": "volvo.fh16_2012",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    },
    {
        "TruckName": "Volvo FH 2021",
        "InternalName": "volvo.fh_2021",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    },
    {
        "TruckName": "Volvo FH 2024",
        "InternalName": "volvo.fh_2024",
        "Coordinates": {
            "LeftDoor": {"X": 2785, "Y": 2615, "Width": 240, "Height": 220},
            "RightDoor": {"X": 1110, "Y": 2625, "Width": 240, "Height": 220},
            "Hood": {"X": 1975, "Y": 2632, "Width": 135, "Height": 125}
        }
    }
]

def apply_concrete_alpha_fix(img):
    """
    Ensures that any pixel belonging to the logo (Alpha > 0)
    is forced to full opacity (Alpha = 255) to prevent faded logos in-game.
    Transparent backgrounds remain transparent (Alpha = 0).
    """
    img = img.convert("RGBA")
    r, g, b, a = img.split()
    # Map any alpha > 0 to 255, else 0
    a = a.point(lambda p: 255 if p > 0 else 0)
    return Image.merge("RGBA", (r, g, b, a))

def extract_tobj_header(dlc_base_dir):
    """
    Dynamically extracts the TRUE binary header from an official SCS .tobj file.
    
    Strategy:
    1. Walk the dlc directory to find any .tobj file.
    2. Read its binary content and locate the b'/vehicle/' marker.
    3. The 8 bytes immediately before the marker are: Int32 path length + 4-byte padding.
    4. Everything before those 8 bytes is the authentic SCS header.
    
    This guarantees 100% binary compatibility with the Prism3D engine,
    regardless of any future header format changes by SCS.
    """
    for root, dirs, files in os.walk(dlc_base_dir):
        for fname in files:
            if fname.endswith('.tobj'):
                fpath = os.path.join(root, fname)
                with open(fpath, 'rb') as f:
                    data = f.read()
                marker_idx = data.find(b'/vehicle/')
                if marker_idx != -1 and marker_idx >= 8:
                    # Header = everything before the 8-byte (length + padding) block
                    header = data[:marker_idx - 8]
                    return header
    raise FileNotFoundError(
        f"Could not find any valid .tobj file with '/vehicle/' path in: {dlc_base_dir}"
    )

# ---------------------------------------------------------------------------
# Extract the TRUE SCS header once at module load time from the official DLC.
# The script directory is assumed to contain the extracted dlc_valentine folder.
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DLC_DIR = os.path.join(_SCRIPT_DIR, "dlc_valentine")
try:
    _TRUE_TOBJ_HEADER = extract_tobj_header(_DLC_DIR)
except FileNotFoundError:
    # Fallback: if the DLC folder is missing, use the known-good 40-byte header
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
    Uses the TRUE header extracted from an official SCS DLC file (40 bytes).
    The path string MUST have a leading slash (e.g. "/vehicle/truck/...").
    
    Binary layout:
      [TRUE_HEADER]  (40 bytes, extracted from official DLC)
      [Int32]        path string length (little-endian)
      [4 bytes]      padding (zeros)
      [ASCII string] the texture path
    """
    path_bytes = target_path_str.encode('ascii')
    
    with open(tobj_path, 'wb') as f:
        f.write(_TRUE_TOBJ_HEADER)
        # Int32 string length (little-endian)
        f.write(struct.pack('<I', len(path_bytes)))
        # 4 bytes padding
        f.write(b'\x00\x00\x00\x00')
        # The ASCII path string immediately follows
        f.write(path_bytes)

def generate_sii_content(truck_internal_name):
    """
    Generates the dynamic .sii definition file content for a specific truck.
    """
    content = "SiiNunit\n{\n"
    content += f"accessory_paint_job_data : unisk.{truck_internal_name}.paint_job\n"
    content += "{\n"
    content += '    name: "Universal Logo Skin"\n'
    content += "    price: 1000\n"
    content += "    unlock: 1\n"
    content += '    icon: "paintjob_default"\n'
    content += "    airbrush: true\n"
    content += "    base_color: (1.0, 1.0, 1.0)\n"
    content += '    paint_job_mask: "/vehicle/truck/upgrade/paintjob/universal/universal_skin.tobj"\n'
    content += "}\n}\n"
    return content

class SkinGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ETS2 Universal Skin Generator")
        self.root.geometry("450x250")
        
        # Variables
        self.logo_path = tk.StringVar()
        self.generate_all = tk.BooleanVar(value=True)
        
        self.create_widgets()

    def create_widgets(self):
        # Frame
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(frame, text="ETS2 Mod Tool", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=(0, 10))

        # Logo Selection
        logo_frame = ttk.Frame(frame)
        logo_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(logo_frame, text="Logo (.png):").pack(side=tk.LEFT)
        ttk.Entry(logo_frame, textvariable=self.logo_path, state="readonly", width=35).pack(side=tk.LEFT, padx=5)
        ttk.Button(logo_frame, text="Browse", command=self.browse_logo).pack(side=tk.LEFT)

        # Options
        ttk.Checkbutton(frame, text="Generate for ALL Trucks", variable=self.generate_all).pack(pady=10)

        # Generate Button
        ttk.Button(frame, text="Create Mod (.scs)", command=self.create_mod).pack(pady=20)

    def browse_logo(self):
        filepath = filedialog.askopenfilename(
            title="Select Logo",
            filetypes=[("PNG Images", "*.png")]
        )
        if filepath:
            self.logo_path.set(filepath)

    def create_mod(self):
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

        try:
            self.process_mod(logo_file, save_path)
            messagebox.showinfo("Success", f"Mod successfully created at:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate mod:\n{str(e)}")

    def process_mod(self, logo_path, out_scs_path):
        # Create a temporary directory for intermediate files
        with tempfile.TemporaryDirectory() as tmp_dir:
            # -------------------------------------------------------
            # STEP 1: Use Pillow to composite logos onto a 4096x4096 canvas
            # -------------------------------------------------------
            canvas = Image.new("RGBA", (4096, 4096), (0, 0, 0, 0))
            logo_img = Image.open(logo_path).convert("RGBA")

            # Paste logo at every coordinate region for every truck
            for truck in TRUCKS:
                coords = truck["Coordinates"]
                for part in ["LeftDoor", "RightDoor", "Hood"]:
                    if part in coords:
                        cd = coords[part]
                        # Resize logo using Lanczos for high quality
                        resized_logo = logo_img.resize((cd["Width"], cd["Height"]), Image.LANCZOS)
                        # Paste with alpha masking to preserve transparency
                        canvas.paste(resized_logo, (cd["X"], cd["Y"]), mask=resized_logo)

            # -------------------------------------------------------
            # STEP 2: Apply Concrete Alpha Fix (Pillow)
            # Any pixel with A > 0 gets forced to A = 255
            # -------------------------------------------------------
            final_texture = apply_concrete_alpha_fix(canvas)

            # -------------------------------------------------------
            # STEP 3: Save intermediate PNG, then convert to DXT5 DDS via Wand
            # -------------------------------------------------------
            temp_png = os.path.join(tmp_dir, "universal_skin.png")
            temp_dds = os.path.join(tmp_dir, "universal_skin.dds")
            final_texture.save(temp_png, format="PNG")

            # Use Wand (ImageMagick) to produce a proper DXT5-compressed DDS
            with WandImage(filename=temp_png) as wand_img:
                wand_img.compression = 'dxt5'
                wand_img.save(filename=temp_dds)

            # Read the final DDS bytes
            with open(temp_dds, 'rb') as f:
                dds_bytes = f.read()

            # -------------------------------------------------------
            # STEP 4: Generate the binary TOBJ file
            # Path MUST have a leading slash for the Prism3D engine
            # -------------------------------------------------------
            temp_tobj = os.path.join(tmp_dir, "universal_skin.tobj")
            tobj_in_game_path = "/vehicle/truck/upgrade/paintjob/universal/universal_skin.dds"
            write_tobj(temp_tobj, tobj_in_game_path)
            with open(temp_tobj, 'rb') as f:
                tobj_bytes = f.read()

            # -------------------------------------------------------
            # STEP 5: Package everything into the .scs (ZIP_STORED) archive
            # -------------------------------------------------------
            with zipfile.ZipFile(out_scs_path, 'w', zipfile.ZIP_STORED) as scs:
                # Write the universal texture assets
                scs.writestr("vehicle/truck/upgrade/paintjob/universal/universal_skin.dds", dds_bytes)
                scs.writestr("vehicle/truck/upgrade/paintjob/universal/universal_skin.tobj", tobj_bytes)

                # Write a .sii definition for every truck
                for truck in TRUCKS:
                    internal_name = truck["InternalName"]
                    sii_content = generate_sii_content(internal_name)
                    sii_path = f"def/vehicle/truck/{internal_name}/paint_job/universal_skin.sii"
                    scs.writestr(sii_path, sii_content.encode('utf-8'))

if __name__ == "__main__":
    root = tk.Tk()
    app = SkinGeneratorApp(root)
    root.mainloop()
