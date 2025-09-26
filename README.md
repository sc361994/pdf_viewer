# Zen PDF Viewer
A lightweight, standalone PDF viewer and annotation tool for Windows and Linux, inspired by the dual-pane layout of modern code editors like VS Code. This application was built to provide a simple, efficient workflow for users who need to browse a folder of PDFs and make quick annotations without the overhead of heavy, commercial software.

This entire application was created and iteratively developed by Google Gemini.
The icon is downloaded from https://icon-icons.com/icon/pdf-page-folded/30485

## Features
This application combines a file browser and a PDF annotation tool into a single, seamless interface with a rich set of features:

### Core Interface
- Dual-Pane View: A VS Code-inspired layout with a file list on the left and the document viewer on the right.

- Movable Divider: Easily resize the file list and viewer panels by dragging the separator.

- Automatic Folder Reloading: The application remembers and automatically reloads the last folder you were working in on startup.

### File & Page Navigation
Folder Browser: Open an entire folder of PDFs at once.

Numbered File List: All PDFs are displayed in a numbered list with full scrollbar support.

Keyboard & Mouse Navigation:

Select files with a mouse click or by navigating with arrow keys and pressing Enter.

Turn pages using the Next/Prev buttons or the Left/Right arrow keys.

Jump to the top or bottom of the current page with the Home and End keys.

In-Page Scrolling: Scroll through long pages using the mouse wheel or the Up/Down arrow keys.

## Annotation & Editing Tools
Multi-Color Highlighting: Select any color to highlight text.

Multi-Line Text Boxes: Add text notes with a resizable, multi-line input dialog.

Text Selection: Select and copy text directly to your clipboard.

Eraser Tool: Easily remove any highlight or text box with a single click.

Undo/Redo System: Full undo (Ctrl+Z) and redo (Ctrl+Y) support for all annotation actions.

Direct Save: All changes (annotations) are held in memory and only written to the original file when you press Save (Ctrl+S). An asterisk (*) in the title bar indicates unsaved changes.

File Renaming: Right-click a file in the list to rename it. The application handles saving current work and reloading the file list seamlessly.

## Prerequisites
Before running the script, you need to have Python and a few libraries installed.

Python 3.x

pip (Python's package installer, usually included with Python)

Tkinter: On some Linux distributions, you may need to install the Tkinter library separately.

On Debian/Ubuntu: sudo apt-get install python3-tk

On Fedora: sudo dnf install python3-tkinter

Installation & Setup
Clone the repository:

git clone [https://github.com/sc361994/pdf_viewer.git](https://github.com/sc361994/pdf_viewer.git)
cd pdf_viewer

Install the required libraries:
Open a command prompt or terminal and run the following command:

pip install PyMuPDF Pillow

How to Run
To run the application directly from the Python script, execute the following command in your terminal from the project's root directory:

python pdf_viewer_app.py

Building the Executable
You can package the application into a single executable file for easy distribution.

For Windows
Run the following command from the project's root directory. Make sure you have an icon file (e.g., icon.ico) in the same folder if you wish to use the --icon option.

python -m PyInstaller --onefile --windowed --name="Zen PDF Viewer" --icon="your_icon.ico" pdf_viewer_app.py

--onefile: Bundles everything into a single executable.

--windowed: Prevents the command prompt from appearing behind the app.

--name: Sets the name of your final .exe file.

--icon: (Optional) Sets the application's icon.

Your standalone executable, Zen PDF Viewer.exe, will be located in the newly created dist folder.

For Linux
The process is very similar. Run the following command from the project's root directory:

python -m PyInstaller --onefile --name="Zen-PDF-Viewer" pdf_viewer_app.py

The --windowed and --icon flags are generally not needed for Linux builds, as desktop environments handle icons and windowing differently.

Your standalone executable, Zen-PDF-Viewer, will be located in the newly created dist folder. You can run it directly from your terminal:

./dist/Zen-PDF-Viewer
