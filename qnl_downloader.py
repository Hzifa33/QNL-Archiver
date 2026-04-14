import requests
import os
import time
import sys
import img2pdf
import urllib.parse
import threading
import itertools
import shutil
import signal

RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"

C_GOLD  = "\033[38;2;255;189;46m"
C_AMBER = "\033[38;2;210;120;20m"
C_TEAL  = "\033[38;2;56;210;190m"
C_ROSE  = "\033[38;2;240;80;100m"
C_WHITE = "\033[38;2;230;230;240m"
C_GREY  = "\033[38;2;100;100;120m"
C_GREEN = "\033[38;2;80;220;130m"

W = shutil.get_terminal_size((80, 20)).columns

_interrupted = threading.Event()

def _sigint_handler(sig, frame):
    _interrupted.set()

def clr():
    os.system('cls' if os.name == 'nt' else 'clear')

def center(text, width=None):
    return text.center(width or W)

def rule(char="-", color=C_AMBER):
    return f"{color}{char * W}{RESET}"

def spinner_frames():
    return itertools.cycle(["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"])

def info(msg):
    print(f"  {C_TEAL}*{RESET}  {C_WHITE}{msg}{RESET}")

def warn(msg):
    print(f"  {C_GOLD}!{RESET}  {C_GOLD}{msg}{RESET}")

def error_msg(msg):
    print(f"  {C_ROSE}x{RESET}  {C_ROSE}{BOLD}{msg}{RESET}")

def success_msg(msg):
    print(f"  {C_GREEN}+{RESET}  {C_GREEN}{BOLD}{msg}{RESET}")

def section(title, icon="*"):
    inner = f"  {icon}  {title}  "
    side  = max(0, (W - len(inner) - 4) // 2)
    print()
    print(f"{C_AMBER}{'-' * W}{RESET}")
    print(f"{C_AMBER}{'-' * side}  {C_GOLD}{BOLD}{icon}  {title}  {RESET}{C_AMBER}{'-' * side}{RESET}")
    print(f"{C_AMBER}{'-' * W}{RESET}")
    print()

def _pct(found, total, done=False):
    if total == 0: return 0.0
    raw = found / total * 100
    if done:
        return 100.0
    return min(raw, 99.0)

def _draw_bar(pct, width=38):
    filled = int(width * pct / 100)
    empty  = width - filled
    bar    = (
        f"\033[38;2;56;210;190m{'#' * filled}{RESET}"
        f"{C_GREY}{'-' * empty}{RESET}"
    )
    color = C_GREEN if pct >= 100 else C_GOLD
    label = f"{color}{BOLD}{pct:5.1f}%{RESET}"
    return f"[{bar}] {label}"

# ==========================================
# الحسابات المسبقة (الصفحات والحجم التقريبي)
# ==========================================
def _page_exists(book_id, page_num):
    url_book_id = book_id.replace(':', '%3A')
    page_str = f"{page_num:04d}"
    url = f"http://ediscovery.qnl.qa/ar/islandora/object/{url_book_id}-{page_str}/datastream/JPG/view"
    try:
        with requests.get(url, stream=True, timeout=5) as resp:
            if resp.status_code == 200 and 'image' in resp.headers.get('Content-Type', '').lower():
                return True
    except requests.exceptions.RequestException:
        pass
    return False

def _find_total_pages_logic(book_id, result):
    low = 1
    high = 50
    while _page_exists(book_id, high):
        if _interrupted.is_set(): return
        low = high
        high *= 2

    last_valid = low
    while low <= high:
        if _interrupted.is_set(): return
        mid = (low + high) // 2
        if _page_exists(book_id, mid):
            last_valid = mid
            low = mid + 1
        else:
            high = mid - 1
            
    result.append(last_valid)

def find_total_pages_with_spinner(book_id):
    result = []
    t = threading.Thread(target=_find_total_pages_logic, args=(book_id, result), daemon=True)
    t.start()
    
    spin = spinner_frames()
    clear_line = "\033[2K\r"
    
    while t.is_alive():
        sp = next(spin)
        sys.stdout.write(f"{clear_line}  {C_TEAL}*{RESET}  {C_WHITE}Total pages   :  {C_GOLD}{sp}{RESET} ")
        sys.stdout.flush()
        t.join(0.08)
        
    if not result:
        return 0
        
    total = result[0]
    sys.stdout.write(f"{clear_line}  {C_TEAL}*{RESET}  {C_WHITE}Total pages   :  {C_GOLD}{total}{RESET}\n")
    sys.stdout.flush()
    return total

def format_size(size_in_bytes):
    if size_in_bytes == 0: return "Unknown"
    size_kb = size_in_bytes / 1024
    size_mb = size_kb / 1024
    if size_mb >= 1024:
        return f"{size_mb / 1024:.2f} GB"
    if size_mb >= 1:
        return f"{size_mb:.2f} MB"
    return f"{size_kb:.1f} KB"

def estimate_total_size(book_id, total_pages):
    if total_pages == 0: return 0
    url_book_id = book_id.replace(':', '%3A')
    url = f"http://ediscovery.qnl.qa/ar/islandora/object/{url_book_id}-0001/datastream/JPG/view"
    try:
        with requests.get(url, stream=True, timeout=5) as resp:
            if resp.status_code == 200:
                content_length = resp.headers.get('Content-Length')
                if content_length and content_length.isdigit():
                    return int(content_length) * total_pages
                else:
                    resp_full = requests.get(url, timeout=10)
                    return len(resp_full.content) * total_pages
    except Exception:
        pass
    return 300 * 1024 * total_pages
# ==========================================

class LiveProgress:
    def __init__(self, total_pages):
        self._stop   = threading.Event()
        self._lock   = threading.Lock()
        self.page    = 0
        self.found   = 0
        self.errors  = 0
        self.status  = "Initialising..."
        self.done    = False
        self.total_pages = total_pages
        self._spin   = spinner_frames()
        self._thread = threading.Thread(target=self._render, daemon=True)

    def start(self):
        self._thread.start()

    def update(self, page, found, errors, status="", done=False):
        with self._lock:
            self.page   = page
            self.found  = found
            self.errors = errors
            self.done   = done
            if status:
                self.status = status

    def stop(self, clear=True):
        self._stop.set()
        self._thread.join()
        if clear:
            sys.stdout.write("\033[2K\r")
            sys.stdout.flush()

    def _render(self):
        clear_line = "\033[2K\r"
        while not self._stop.is_set():
            sp = next(self._spin)
            with self._lock:
                pg, fd, er, st, dn, total = (
                    self.page, self.found,
                    self.errors, self.status, self.done, self.total_pages
                )

            pct  = _pct(fd, total, done=dn)
            bar  = _draw_bar(pct, width=32)
            flag = f"  {C_ROSE}{BOLD}[PAUSED]{RESET}" if _interrupted.is_set() else ""

            line = (
                f"  {C_TEAL}{sp}{RESET} "
                f"{C_GOLD}Pg {pg:>4}{RESET}  "
                f"{bar}  "
                f"{C_GREEN}+{fd}{RESET} "
                f"{C_ROSE}x{er}{RESET}  "
                f"{C_GREY}{st[:22]}{RESET}"
                f"{flag}"
            )
            sys.stdout.write(clear_line + line[:W + 120])
            sys.stdout.flush()
            time.sleep(0.08)

def assemble_pdf(downloaded_files, pdf_path):
    total = len(downloaded_files)
    info(f"Merging {C_GOLD}{total}{RESET} pages  ->  {C_GOLD}{pdf_path}{RESET}")
    print()

    steps = 60
    clear_line = "\033[2K\r"
    
    for i in range(steps):
        pct = i / steps * 99.0
        bar = _draw_bar(pct, width=38)
        sys.stdout.write(f"{clear_line}  {bar}  {C_GREY}preparing...{RESET}")
        sys.stdout.flush()
        time.sleep(0.012)

    with open(pdf_path, "wb") as f:
        f.write(img2pdf.convert(downloaded_files))

    bar = _draw_bar(100.0, width=38)
    sys.stdout.write(f"{clear_line}  {bar}  {C_GREY}{total}/{total} pages{RESET}\n")
    sys.stdout.flush()
    print()

def _cleanup(temp_dir, files):
    for fp in files:
        try:
            os.remove(fp)
        except OSError:
            pass
    if os.path.exists(temp_dir):
        try:
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)
        except OSError:
            pass

def interrupted_menu(downloaded_files, temp_dir, output_filename):
    print()
    print()
    print(rule("=", C_ROSE))
    print(f"{C_ROSE}{BOLD}{center('!   Download Interrupted  -  What would you like to do?   !')}{RESET}")
    print(rule("=", C_ROSE))
    print()
    info(f"Pages downloaded so far  :  {C_GOLD}{BOLD}{len(downloaded_files)}{RESET}")
    print()

    if not downloaded_files:
        warn("No pages were downloaded yet - nothing to save.")
        _cleanup(temp_dir, [])
        _footer()
        sys.exit(0)

    pad = "  "
    print(f"{pad}{C_AMBER}{'-' * (W - 4)}{RESET}")
    print()
    print(f"{pad}{C_TEAL}{BOLD}[1]{RESET}  {C_WHITE}{BOLD}Save partial PDF{RESET}")
    print(f"{pad}     {C_GREY}Assemble the {len(downloaded_files)} downloaded pages into a PDF right now.{RESET}")
    print(f"{pad}     {C_GREY}The file will be saved as:  {C_GOLD}{output_filename}_partial.pdf{RESET}")
    print()
    print(f"{pad}{C_ROSE}{BOLD}[2]{RESET}  {C_WHITE}{BOLD}Discard & exit{RESET}")
    print(f"{pad}     {C_GREY}Delete all {len(downloaded_files)} temporary image files and quit cleanly.{RESET}")
    print()
    print(f"{pad}{C_AMBER}{'-' * (W - 4)}{RESET}")
    print()

    while True:
        sys.stdout.write(
            f"{pad}{C_AMBER}>{RESET}  {C_WHITE}Your choice{RESET}  "
            f"{C_GREY}[1 / 2]{RESET}\n{pad}{C_TEAL}> {RESET}"
        )
        sys.stdout.flush()

        try:
            choice = input().strip()
        except (EOFError, KeyboardInterrupt):
            choice = "2"

        if choice == "1":
            section("Saving Partial PDF", "-")
            pdf_path = f"{output_filename}_partial.pdf"
            try:
                assemble_pdf(downloaded_files, pdf_path)
                _cleanup(temp_dir, downloaded_files)

                print(rule("=", C_GREEN))
                print(f"{C_GREEN}{BOLD}{center(f'* Partial PDF Saved  -  {pdf_path}  *')}{RESET}")
                size_kb = os.path.getsize(pdf_path) / 1024
                size_mb = size_kb / 1024
                size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{size_kb:.1f} KB"
                print(f"{C_GREY}{center(f'Pages: {len(downloaded_files)}   |   Size: {size_str}')}{RESET}")
                print(rule("=", C_GREEN))

            except Exception as e:
                error_msg(f"Failed to create PDF: {e}")
            break

        elif choice == "2":
            print()
            warn("Discarding all temporary downloaded files...")
            _cleanup(temp_dir, downloaded_files)
            print()
            success_msg("All temporary files deleted. Goodbye!")
            break

        else:
            print()
            warn("Invalid input - please type  1  or  2")
            print()

    _footer()
    sys.exit(0)

def download_and_pdf_book(book_id, output_filename):
    signal.signal(signal.SIGINT, _sigint_handler)
    
    url_book_id        = book_id.replace(':', '%3A')
    temp_dir           = f"temp_{url_book_id}"
    os.makedirs(temp_dir, exist_ok=True)

    downloaded_files   = []
    page_num           = 1
    consecutive_errors = 0
    max_errors         = 5

    section("Book Information", "*")
    info(f"Book ID       :  {C_GOLD}{book_id}{RESET}")
    info(f"Output file   :  {C_GOLD}{output_filename}.pdf{RESET}")
    info(f"Temp dir      :  {C_GOLD}{temp_dir}{RESET}")
    
    total_pages = find_total_pages_with_spinner(book_id)
    
    if total_pages == 0:
        print()
        error_msg("Could not find any pages or process was interrupted.")
        _cleanup(temp_dir, [])
        return

    sys.stdout.write(f"  {C_TEAL}*{RESET}  {C_WHITE}Estimated size:  {C_GREY}calculating...{RESET}")
    sys.stdout.flush()
    total_bytes = estimate_total_size(book_id, total_pages)
    size_str = format_size(total_bytes)
    
    clear_line = "\033[2K\r"
    sys.stdout.write(f"{clear_line}  {C_TEAL}*{RESET}  {C_WHITE}Estimated size:  {C_GOLD}{size_str}{RESET}\n")
    sys.stdout.flush()

    print()
    # رسالة التأكيد الاحترافية المحدثة
    sys.stdout.write(f"  {C_AMBER}>{RESET}  {C_WHITE}Would you like to initiate the download process? {C_GREY}[Y/n]{RESET}\n  {C_TEAL}> {RESET}")
    sys.stdout.flush()
    
    try:
        user_choice = input().strip().lower()
    except (KeyboardInterrupt, EOFError):
        user_choice = 'n'
        
    if user_choice in ['n', 'no']:
        print()
        warn("Download cancelled by user.")
        _cleanup(temp_dir, [])
        return

    section("Download Phase", "*")
    info(f"{C_ROSE}Tip: Press  Ctrl+C  to save up to here or cancel completely.{RESET}")
    print()

    progress = LiveProgress(total_pages)
    progress.start()

    try:
        while True:
            if _interrupted.is_set():
                progress.stop()
                interrupted_menu(downloaded_files, temp_dir, output_filename)
                return

            if page_num > total_pages or consecutive_errors >= max_errors:
                progress.update(page_num, len(downloaded_files),
                                consecutive_errors, "End of book", done=True)
                break

            page_str     = f"{page_num:04d}"
            url_server_1 = (
                f"http://ediscovery.qnl.qa/ar/islandora/object/"
                f"{url_book_id}-{page_str}/datastream/JPG/view"
            )
            encoded      = urllib.parse.quote(url_server_1, safe='')
            url_server_2 = (
                f"https://imageservice.qnl.qa/adore-djatoka/resolver"
                f"?rft_id={encoded}&url_ver=Z39.88-2004"
                f"&svc_id=info%3Alanl-repo%2Fsvc%2FgetRegion"
                f"&svc_val_fmt=info%3Aofi%2Ffmt%3Akev%3Amtx%3Ajpeg2000"
                f"&svc.format=image%2Fjpeg&svc.level=4&svc.rotate=0"
            )

            saved = False
            for url in [url_server_1, url_server_2]:
                try:
                    resp = requests.get(url, stream=True, timeout=10)
                    if resp.status_code == 200:
                        ct = resp.headers.get('Content-Type', '').lower()
                        if 'image' in ct:
                            fp = os.path.join(temp_dir, f"page_{page_str}.jpg")
                            with open(fp, 'wb') as f:
                                for chunk in resp.iter_content(1024):
                                    f.write(chunk)
                            downloaded_files.append(fp)
                            saved = True
                            break
                except requests.exceptions.RequestException:
                    continue

            if saved:
                consecutive_errors = 0
                progress.update(page_num, len(downloaded_files), 0,
                                f"Pg {page_num} saved")
            else:
                consecutive_errors += 1
                progress.update(page_num, len(downloaded_files), consecutive_errors,
                                f"Missing ({consecutive_errors}/{max_errors})")

            page_num += 1
            time.sleep(0.4)

    except KeyboardInterrupt:
        _interrupted.set()
        progress.stop()
        interrupted_menu(downloaded_files, temp_dir, output_filename)
        return

    progress.stop()
    print()
    print(rule("-", C_TEAL))
    scanned = page_num - 1
    print(f"  {C_TEAL}Pages scanned   {RESET}: {C_WHITE}{scanned}{RESET}")
    print(f"  {C_GREEN}Images saved    {RESET}: {C_WHITE}{len(downloaded_files)}{RESET}")
    print(f"  {C_ROSE}Missing / skip  {RESET}: {C_WHITE}{scanned - len(downloaded_files)}{RESET}")
    print(rule("-", C_TEAL))

    section("PDF Assembly", "-")

    if not downloaded_files:
        warn("No images were downloaded - nothing to assemble.")
        warn("Please verify the Book ID and your network connection.")
        _cleanup(temp_dir, [])
        return

    pdf_path = f"{output_filename}.pdf"
    try:
        assemble_pdf(downloaded_files, pdf_path)
        _cleanup(temp_dir, downloaded_files)

        print(rule("=", C_GREEN))
        print(f"{C_GREEN}{BOLD}{center(f'* PDF Created Successfully  -  {pdf_path}  *')}{RESET}")
        size_kb = os.path.getsize(pdf_path) / 1024
        size_mb = size_kb / 1024
        size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{size_kb:.1f} KB"
        print(f"{C_GREY}{center(f'Pages: {len(downloaded_files)}   |   File size: {size_str}')}{RESET}")
        print(rule("=", C_GREEN))
        print()

    except Exception as e:
        print()
        error_msg(f"PDF generation failed: {e}")

LOGO = r"""
      ██████╗ ███╗   ██╗██╗     
     ██╔═══██╗████╗  ██║██║     
     ██║   ██║██╔██╗ ██║██║     
     ██║▄▄ ██║██║╚██╗██║██║     
     ╚██████╔╝██║ ╚████║███████╗
      ╚══▀▀═╝ ╚═╝  ╚═══╝╚══════╝
"""

def splash():
    clr()
    print()
    for line in LOGO.strip("\n").split("\n"):
        print(f"{C_GOLD}{center(line)}{RESET}")
    print()
    print(rule("-", C_AMBER))
    print(f"{C_TEAL}{BOLD}{center('* Qatar National Library  -  Book-to-PDF Archival Suite  *')}{RESET}")
    print(f"{C_GREY}{center('Developed with ♥  by  Hzifa33')}{RESET}")
    print(rule("-", C_AMBER))
    print()

def _footer():
    print()
    print(rule("-", C_AMBER))
    print(f"{C_GOLD}{DIM}{center('* Thank you for using QNL Downloader  -  Hzifa33  *')}{RESET}")
    print(rule("-", C_AMBER))
    print()

if __name__ == "__main__":
    splash()

    def prompt(label, example=""):
        hint = f"  {C_GREY}e.g. {example}{RESET}" if example else ""
        sys.stdout.write(
            f"  {C_AMBER}>{RESET}  {C_WHITE}{label}{RESET}{hint}\n"
            f"  {C_TEAL}> {RESET}"
        )
        sys.stdout.flush()
        return input().strip()

    print(rule("-", C_GREY))
    try:
        target_book_id = prompt("Book ID", "QNL:00022881")
        print()
        output_name    = prompt("Output filename  (no extension)")
        print()
    except (KeyboardInterrupt, EOFError):
        print()
        success_msg("Exited successfully. Thank you!")
        _footer()
        sys.exit(0)

    if target_book_id and output_name:
        download_and_pdf_book(target_book_id, output_name)
    else:
        error_msg("Both Book ID and output filename are required.")
        print()

    _footer()
