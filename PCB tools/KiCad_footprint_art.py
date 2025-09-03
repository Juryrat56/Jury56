# trace.py — PNG -> KiCad footprint (no pyvips, no potrace)
# Deps: pillow, opencv-python, numpy, gdstk

from PIL import Image
import numpy as np
import cv2
import gdstk
from pathlib import Path
import os

# Colour Codes
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
PURPLE = '\033[95m'
CYAN = '\033[96m'
UNDERLINE = '\033[4m'
BOLD = '\033[1m'
RESET = '\033[0m'

# Script Variables
NEWLN = "\n"
AUTHOR = "Zane Henry - OneBigCircle"
SCRIPT_NAME = os.path.basename(__file__)
EX_USAGE = f"""Usage: Convert Image into Kicad footprint.{NEWLN}
   Example: Image -> monotone KiCad footprint file. {NEWLN}
   Import .kicad_mod file into KiCad footprint editor and place on PCB. {NEWLN}
   KiCad PCB files can be imported into Altium using the KiCad Importer extension. {NEWLN}"""

LOGO = "                     +                                     " + NEWLN + \
       "                ++++++                                     " + NEWLN + \
       "             ++++++++++                    +++             " + NEWLN + \
       "           +++++++++++                    ++++++           " + NEWLN + \
       "         +++++++++    %%%%%%%%%%%%       +++++++++         " + NEWLN + \
       "        +++++++   %%%%%%%%%%%%%%%%         ++++++++        " + NEWLN + \
       "      +++++++   %%%%%%%%%%%%%%%%%             +++++++      " + NEWLN + \
       "     +++++++  %%%%%%%%%                        +++++++     " + NEWLN + \
       "     +++++   %%%%%%%         %%%%%%%             ++++++    " + NEWLN + \
       "      +++  %%%%%%%           %%%%%%%%%            +++++    " + NEWLN + \
       "           %%%%%             %%%%%%%%%%%           +++++   " + NEWLN + \
       "          %%%%%                   %%%%%%%          ++++++  " + NEWLN + \
       "          %%%%%                     %%%%%%          +++++  " + NEWLN + \
       "            %%                       %%%%%          +++++  " + NEWLN + \
       "                                      %%%%%         +++++  " + NEWLN + \
       "                %%%%%                 %%%%%         +++++  " + NEWLN + \
       "                %%%%%%               %%%%%%  %%     +++++  " + NEWLN + \
       "                 %%%%%%             %%%%%%  %%%%%   +++++  " + NEWLN + \
       "      ++          %%%%%%           %%%%%%   %%%%%   ++++   " + NEWLN + \
       "   +++++           %%%%%%%%%%%%%%%%%%%%%   %%%%%      ++   " + NEWLN + \
       "    +++++           %%%%%%%%%%%%%%%%%%   %%%%%%            " + NEWLN + \
       "    ++++++             %%%%%%%%%%%%%   %%%%%%%             " + NEWLN + \
       "     ++++++                         %%%%%%%%%              " + NEWLN + \
       "      +++++++             %%%%%%%%%%%%%%%%%                " + NEWLN + \
       "        +++++++          %%%%%%%%%%%%%%%%                  " + NEWLN + \
       "         +++++++++       %%%%%%%%%%%%                      " + NEWLN + \
       "           +++++++++++                                     " + NEWLN + \
       "             ++++++++++++++                                " + NEWLN + \
       "                ++++++++++                                 " + NEWLN + \
       "                     +++++                                 "

def print_header(message):
    print(f"{PURPLE}{BOLD}{message}{RESET}", flush=True)

def print_fatal_error(message):
    print(f"{RED}{BOLD}Fatal Error: {message}{RESET}", flush=True)
    sys.exit(1)

def print_error(message):
    print(f"{RED}{BOLD}Error: {message}{RESET}", flush=True)

def print_warning(message):
    print(f"{YELLOW}{BOLD}Warning: {message}{RESET}", flush=True)

def print_success(message):
    print(f"{GREEN}{BOLD}{message}{RESET}", flush=True)

def print_info(message):
    print(f"{BLUE}{message}{RESET}", flush=True)

def print_separator():
    print(f"{CYAN}------------------------------------{RESET}", flush=True)

# ---------- CONFIG ----------

# Threshold: pixels < THRESHOLD => filled (True)
THRESHOLD = 127

# DPI used to convert pixels -> millimetres
DPI = 300

# Simplify contours: 0 = no simplification. Try 0.5 to reduce points.
# Value is a percentage of contour perimeter (e.g., 0.5 => 0.5% of perimeter).
SIMPLIFY_EPSILON_PERCENT = 0.0

# Flip vertically so the resulting footprint isn't upside-down (common for image coords).
INVERT_Y = True

# KiCad layer for polygons
KICAD_LAYER = "F.Mask" #F.Mask for exposed copper designs
# ---------------------------


# Load and convert image to bitmap
def load_and_threshold(path: str, threshold: int) -> tuple[np.ndarray, tuple[int, int]]:
    """Load image with Pillow, flatten alpha to white, grayscale, and threshold to boolean bitmap."""
    img = Image.open(path)
    img = img.transpose(Image.FLIP_TOP_BOTTOM)
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])  # use alpha as mask
        img = bg
    else:
        img = img.convert("RGB")

    img = img.convert("L")  # grayscale
    arr = np.array(img)     # uint8 [0..255]
    bitmap = arr < threshold
    h, w = bitmap.shape
    return bitmap, (w, h)


def contours_with_holes(bitmap: np.ndarray, simplify_eps_percent: float):
    """
    Find external contours and their holes using OpenCV.
    Returns a list of (outer_contour, [hole_contours, ...]),
    where each contour is an Nx2 float array of (x, y) points.
    """
    # OpenCV expects 0/255 uint8 image; we want filled=255
    mask = bitmap.astype(np.uint8) * 255

    # Find contours with 2-level hierarchy: external + holes
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)

    if hierarchy is None:
        return []

    hierarchy = hierarchy[0]  # shape (N, 4): [next, prev, first_child, parent]

    # Optional simplification
    simplified = []
    for cnt in contours:
        if simplify_eps_percent and simplify_eps_percent > 0:
            peri = cv2.arcLength(cnt, True)
            eps = (simplify_eps_percent / 100.0) * peri
            cnt = cv2.approxPolyDP(cnt, eps, True)
        simplified.append(cnt.reshape(-1, 2).astype(float))

    # Build (outer, holes) pairs
    pairs = []
    for i, cnt in enumerate(simplified):
        parent = hierarchy[i][3]
        if parent == -1:
            # It's an outer contour — gather direct children as holes
            holes = []
            child = hierarchy[i][2]
            while child != -1:
                holes.append(simplified[child])
                child = hierarchy[child][0]  # iterate siblings via 'next'
            pairs.append((cnt, holes))
    return pairs


# Physical size of image
def mm_per_pixel(dpi: float) -> float:
    return 25.4 / dpi

# Build KiCad polygon
def to_kicad_fp_poly(points_px: np.ndarray, img_h: int, mm_per_px: float, invert_y: bool, layer: str) -> str:
    """Build a KiCad (fp_poly ...) S-expression for a single polygon."""
    if invert_y:
        pts = [(float(x) * mm_per_px, (img_h - float(y)) * mm_per_px) for x, y in points_px]
    else:
        pts = [(float(x) * mm_per_px, float(y) * mm_per_px) for x, y in points_px]

    pts_sexpr = "\n            ".join(f"(xy {x:.4f} {y:.4f})" for x, y in pts)
    return f"""\
    (fp_poly
        (pts {pts_sexpr})
        (layer "{layer}")
        (width 0)
        (fill solid)
    )"""


def main():
    print_header(f"{SCRIPT_NAME} by {AUTHOR}")
    print_header(LOGO)
    print_info(EX_USAGE)

    
    IMAGE_PATH = input("Enter Image path: ").strip().strip('"').strip("'")
    
    
    default_name = "footprint"
    default_folder = r"C:\Users\Public\Documents"

    # Ask user what to call the footprint
    file_name = input("Enter the desired name of the footprint (without .kicad_mod): ").strip()
    if not file_name:
        file_name = default_name

    # Ask user where to save the footprint
    save_folder = input(f"Enter folder to save footprint, [Default location: {default_folder}]: ").strip().strip('"').strip("'")
    if not save_folder:
        save_folder = default_folder
        
    # Ensure folder exists
    os.makedirs(save_folder, exist_ok=True)

    # Combine folder + filename + extension
    save_path = os.path.join(save_folder, file_name + ".kicad_mod")

    bitmap, (w, h) = load_and_threshold(IMAGE_PATH, THRESHOLD)
    pairs = contours_with_holes(bitmap, SIMPLIFY_EPSILON_PERCENT)

    if not pairs:
        raise print_fatal_error("No contours found. Try lowering THRESHOLD or check the image.")

    mm_px = mm_per_pixel(DPI)
    all_fp_polys = []

    for outer_px, holes_px in pairs:
        outer = gdstk.Polygon([tuple(p) for p in outer_px])
        holes = [gdstk.Polygon([tuple(p) for p in hp]) for hp in holes_px] if holes_px else []

        if holes:
            result_polys = gdstk.boolean(outer, holes, "not") or []
        else:
            result_polys = [outer]

        for poly in result_polys:
            pts_px = np.array(poly.points, dtype=float)
            all_fp_polys.append(to_kicad_fp_poly(pts_px, h, mm_px, INVERT_Y, KICAD_LAYER))

    poly_block = "\n  ".join(all_fp_polys)
    footprint = f"""\
(footprint "Library:ImageTrace"
  (layer "{KICAD_LAYER}")
  (at 0 0)
  (attr board_only exclude_from_pos_files exclude_from_bom)
  {poly_block}
)"""

    Path(save_path).write_text(footprint, encoding="utf-8")
    print_success(f"\nCreated footprint in: {Path(save_path).resolve()}")

if __name__ == "__main__":
    main()
