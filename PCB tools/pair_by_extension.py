import os
import re
import sys
import subprocess
from collections import defaultdict
from pathlib import Path

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
EX_USAGE = f"""Usage: Compare two Gerber file directories visually.{NEWLN}
Example: python {SCRIPT_NAME} dir1 dir2 output_dir"""

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

# Determine the absolute path to GerberCompare.py (adjust if it's in a subfolder)
SCRIPT_TO_RUN = Path(__file__).parent / "GerberCompare.py"

# Check if it exists
if not SCRIPT_TO_RUN.exists():
    raise FileNotFoundError(f"Cannot find GerberCompare.py at: {SCRIPT_TO_RUN.resolve()}")


# Matches .G followed by 1 or 2 alphanumeric characters -> Copper layers
INCLUDE_PATTERN = re.compile(r'^\.g[a-zA-Z0-9]{1,2}$', re.IGNORECASE)

# Exclude: .GM0–.GM9 -> Mechanical layers
EXCLUDE_PATTERN_1 = re.compile(r'^\.gm[0-9]$', re.IGNORECASE)

# Exclude: .GTO, .GTS, .GTP, .GBO, .GBP, .GBS -> Silk, Mask and Drill layers
EXCLUDE_PATTERN_2 = re.compile(r'^\.g[tbg][osp]$', re.IGNORECASE)
EXCLUDE_PATTERN_3 = re.compile(r'^\.gg[0-9]$', re.IGNORECASE)
EXCLUDE_PATTERN_4 = re.compile(r'^\.gd[0-9]$', re.IGNORECASE)

Kicad_STATIC_EXCLUDE = ["aste" , "mask" , "cuts" , "reen"]

def get_user_preference():
    while True:
        choice = input("Do you want to open generated images for each comparison? (y/n): ").strip().lower()
        if choice in ('y', 'n'):
            return choice == 'y'
        print("Invalid input. Please enter 'y' or 'n'.")

# Filter unwanted file/layer types based on above ^
def get_files_by_extension(directory):
    files_by_ext = defaultdict(list)

    for filename in os.listdir(directory):
        path = os.path.join(directory, filename)
        if os.path.isfile(path):
            file , ext = os.path.splitext(filename)
            ext = ext.lower()
            file = file.lower()

            if any(bad_word in file[-4:] for bad_word in Kicad_STATIC_EXCLUDE):
                continue
            
            if INCLUDE_PATTERN.fullmatch(ext):
                
                if not any(pattern.fullmatch(ext) for pattern in [
                    EXCLUDE_PATTERN_1,
                    EXCLUDE_PATTERN_2,
                    EXCLUDE_PATTERN_3,
                    EXCLUDE_PATTERN_4,
                ]):
                    
                    files_by_ext[ext].append(path)

    return files_by_ext


# Pair file/layer types between directories 
def pair_files(dir1, dir2):
    dir1_files = get_files_by_extension(dir1)
    dir2_files = get_files_by_extension(dir2)

    common_extensions = set(dir1_files.keys()) & set(dir2_files.keys())

    paired = []

    for ext in common_extensions:
        files1 = dir1_files[ext]
        files2 = dir2_files[ext]
        for f1, f2 in zip(files1, files2):
            paired.append((f1, f2))

    return paired, len(paired)

# Run GerberCompare on each file/layer pair
def run_script_on_pairs(pairs, save_dir, count, display):
    for i, (f1, f2) in enumerate(pairs, 1):
        print_info(f"Running script on Pair {i}/{count}:")
        print(f"  {f1}")
        print(f"  {f2}")
        try:
            subprocess.run([sys.executable, str(SCRIPT_TO_RUN.resolve()), f1, f2, save_dir, str(display)], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running script on pair {i}/{count}: {e}")
        print_separator()

if __name__ == "__main__":
    print_header(f"Pair by extension by {AUTHOR}")
    print_header(LOGO)
    print_separator()

    # Input protection
    if len(sys.argv) != 4:
        print_error(EX_USAGE)
        sys.exit(1)

    dir1 = sys.argv[1]
    dir2 = sys.argv[2]
    dir3 = sys.argv[3]

    if not os.path.isdir(dir1) or not os.path.isdir(dir2):
        print_error("Both arguments must be directories.")
        print_info(EX_USAGE)
        sys.exit(1)

    if not os.path.isdir(dir3):
        print_error(f"Output directory '{dir3}' does not exist.")
        print_info(EX_USAGE)
        sys.exit(1)

    pairs, count = pair_files(dir1, dir2)

    if not pairs:
        print_error("No matching file pairs found.")
        sys.exit(0)

    print_info("\n Matched File Pairs:")
    print_separator()
    for i, (f1, f2) in enumerate(pairs, 1):
        print(f"{i:02}.")
        print(f"  {f1}")
        print(f"  {f2}")
        print()
        
    print_separator()
    
    display = get_user_preference()
    
    print_separator()
    input("Press Enter to continue and run the script on each pair...")

    run_script_on_pairs(pairs, dir3, count, display)

    print_success(f"Process complete, all pairs compared and images saved to: '{dir3}'")
