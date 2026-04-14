# QNL Archiver 📚

![Python](https://img.shields.io/badge/python-3.6%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**QNL Archiver** is a powerful, multi-threaded Command Line Interface (CLI) tool designed to download digitized books and manuscripts from the Qatar National Library (QNL) and compile them seamlessly into high-quality PDF files. 

Built with user experience in mind, it features live progress tracking, asynchronous background tasks, and graceful error handling.

## ✨ Features

* **Smart Page Detection:** Utilizes binary search to quickly and accurately determine the total number of pages in a book without downloading them.
* **Live Progress UI:** Beautiful, color-coded terminal output with live progress bars, spinners, and detailed status updates.
* **Resilient Downloading:** Includes fallback server logic and automatic retries for missing or corrupted images.
* **Graceful Interruption:** Press `Ctrl+C` at any time to pause the process. You can choose to save the pages downloaded so far into a partial PDF or discard them cleanly.
* **Auto-Assembly:** Automatically merges downloaded JPEG2000/JPG files into a single, optimized PDF using `img2pdf`.
* **Resource Cleanup:** Automatically cleans up temporary directories and downloaded image fragments after PDF generation.

## ⚙️ Prerequisites
* **Python 3.6+**
* **System Package:** `qpdf` (Required for PDF processing)

## 🚀 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Hzifa33/QNL-Archiver.git
   cd QNL-Archiver
   ```

2. **Install System Dependencies (Termux):**
   ```bash
   pkg update && pkg install python qpdf -y 
   ```

3. **Install Python Requirements:**
   ```bash
   pip install -r requirements.txt
   ```

## 🛠️ Usage

1. **Run the script:**

   ```bash
   python qnl_downloader.py
   ```

2. **Follow the interactive prompts:**

   * **Book ID:** Enter the QNL Book ID (e.g., `QNL:00022881`). You can find this ID in the URL of the book on the QNL digital archive website.

  **How to find the Book ID:** You can find the Book ID among the book's information on the website, specifically located in the "**رقم التصنيف**" box, as illustrated below:
     <img src="https://i.postimg.cc/85DxNZ46/Screenshot-2026-04-14-14-19-35-13-40deb401b9ffe8e1df2f1cc5ba480b12.jpg" width="719" height="110" alt="Where to find the Book ID">
     
   * **Output filename:** Enter your desired name for the final PDF file (without the `.pdf` extension).

### Example Workflow

```text
  >  Book ID  e.g. QNL:00022881
  > QNL:00022881

  >  Output filename  (no extension)
  > History_of_Qatar
```

*The tool will calculate the estimated size, ask for confirmation, and begin the download process while displaying a live progress bar.*

## ⚠️ Disclaimer

This tool is intended for personal, educational, and research purposes only. Please respect the Qatar National Library's Terms of Service and copyright policies when downloading and using their digital materials. Do not use this tool to overwhelm their servers.

## 👨‍💻 Author

Developed with ♥ by **Hzifa33**

## 📄 License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT) - see the LICENSE file for details.
