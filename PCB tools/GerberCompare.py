#!/usr/bin/env python3

import os
import sys

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
AUTHOR = "James Marsden/Zane Henry - OneBigCircle"
SCRIPT_NAME = os.path.basename(__file__)
EX_USAGE = f"""Usage: Compare two Gerber files visually.{NEWLN}
   Example: python {SCRIPT_NAME} file1 file2"""

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

# Try to import dependencies
try:
    from pygerber.gerberx3.api import ColorScheme, Rasterized2DLayer, Rasterized2DLayerParams
except ImportError:
    print_fatal_error(f"'pygerber' module missing or outdated.{NEWLN} Please install via `pip install pygerber`.")

try:
    from PIL import Image, ImageChops
except ImportError:
    print_fatal_error(f"'Pillow' not installed.{NEWLN} Please install via `pip install pillow`.")


def get_output_filenames(file_path):
    base_name = os.path.splitext(os.path.basename(file_path))[0]  # e.g. Main_Board_PCB.GBL → 'Main_Board_PCB'
    extension = os.path.splitext(file_path)[1].upper().replace('.', '')  # e.g. '.GBL' → 'GBL'
    
    # If the base_name includes the extension already (e.g. "VGS_Main_Board_PCB.GBL"), strip it:
    # This handles cases where the base_name might still have extension in it.
    
    if base_name.endswith(extension):
        base_name = base_name[:-len(extension)].rstrip('_').rstrip('.')

    side_by_side_name = f"{base_name}_{extension}_side_by_side.png"
    diff_name = f"{base_name}_{extension}_diff.png"
    
    return side_by_side_name, diff_name



def compare_gerber_layers(file1, file2, side_by_side_name, diff_name, output_dir, display = True, dpi=600):

    # Temporary file names
    out1 = "temp1.png"
    out2 = "temp2.png"

    # Render both sources to image files
    Rasterized2DLayer(
        options=Rasterized2DLayerParams(source_path=file1, colors=ColorScheme.SILK_ALPHA, dpi=dpi)
    ).render().save(out1)

    Rasterized2DLayer(
        options=Rasterized2DLayerParams(source_path=file2, colors=ColorScheme.SILK_ALPHA, dpi=dpi)
    ).render().save(out2)

    img1 = Image.open(out1).convert("RGB")
    img2 = Image.open(out2).convert("RGB")

    # Create a side-by-side composite
    side_by_side = Image.new('RGB', (img1.width + img2.width, max(img1.height, img2.height)))
    side_by_side.paste(img1, (0, 0))
    side_by_side.paste(img2, (img1.width, 0))
    side_by_side_path = os.path.join(output_dir, side_by_side_name)
    side_by_side.save(side_by_side_path)
    print_info(f"Gerbers shown side by side: {side_by_side_path}")
    if display:
        side_by_side.show()

    # Create a differential image
    diff = ImageChops.difference(img1, img2)
    if diff.getbbox() is None:
        print("Layers are identical.")
        return True
    else:
        diff_path = os.path.join(output_dir, diff_name)
        diff.save(diff_path)
        print_warning("Gerber layers differ! A diff image has been saved:")
        print_info(f"Difference shown here: {diff_path}")
        if display:
            diff.show()
        return False

def main():
    print_header(f"GerberCompare by {AUTHOR}")
    print_separator()
    
    # Input protection
    if len(sys.argv) != 5:
        print_fatal_error(EX_USAGE)

    file1, file2, output_dir, display_str = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

    if not os.path.isdir(output_dir):
        print_fatal_error(f"Output directory '{output_dir}' does not exist.")

    for f in (file1, file2):
        if not os.path.isfile(f):
            print_fatal_error(f"File not found: {f}")
            
    display = True if display_str != "False" else False
    
    print_info(f"Comparing:\n - {file1}\n - {file2}")
    print_separator()

    # Output filename and save directory
    name = get_output_filenames(file1)
    result = compare_gerber_layers(file1, file2, name[0], name[1], output_dir, display = display)
    print_separator()
    if result:
        print_success("Comparison complete: No differences found.")
    else:
        print_warning("Comparison complete: Differences were found.")

if __name__ == "__main__":
    main()
