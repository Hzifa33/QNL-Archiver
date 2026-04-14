# QNL Archiver 📚

![Python](https://img.shields.io/badge/python-3.6%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**QNL Archiver** is a powerful, multi-threaded Command Line Interface (CLI) tool designed to download digitized books and manuscripts from the Qatar National Library (QNL) and compile them seamlessly into high-quality PDF files. 

## ✨ Features
* **Smart Page Detection:** Accurate total page count using binary search.
* **Live Progress UI:** Color-coded terminal output with live progress bars.
* **Auto-Assembly:** Automatically merges downloaded files into a single PDF.
* **Resource Cleanup:** Cleans up temporary files after generation.

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
   pkg update && pkg install qpdf -y
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
   * Enter the **Book ID** (e.g., `QNL:00022881`).
   * Enter the **Output filename**.

## ⚠️ Disclaimer
This tool is for personal and educational use only. Please respect the QNL copyright policies.

## 👨‍💻 Author
Developed with ♥ by **Hzifa33**

## 📄 License
This project is licensed under the [MIT License](https://opensource.org/licenses/MIT) - see the LICENSE file for details.
