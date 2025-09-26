import tkinter as tk
from tkinter import filedialog, ttk, simpledialog, messagebox
from tkinter.colorchooser import askcolor
import fitz  # PyMuPDF
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os
import copy

class TextInputDialog(simpledialog.Dialog):
    """A custom dialog to get multi-line text input from the user."""
    def body(self, master):
        self.text = tk.Text(master, width=50, height=10, wrap=tk.WORD)
        self.text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
        return self.text # initial focus

    def apply(self):
        self.result = self.text.get("1.0", "end-1c")

class RenameDialog(simpledialog.Dialog):
    """A custom dialog to get a new filename with a wider input box."""
    def __init__(self, parent, title=None, initialvalue=None):
        self.initialvalue = initialvalue
        super().__init__(parent, title=title)

    def body(self, master):
        self.entry = tk.Entry(master, width=50) # Increased width for better visibility
        if self.initialvalue:
            self.entry.insert(0, self.initialvalue)
            self.entry.select_range(0, tk.END)
        self.entry.pack(padx=10, pady=10)
        return self.entry

    def apply(self):
        self.result = self.entry.get()

class PDFViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Viewer Application")
        self.root.geometry("1200x800")

        # --- Class variables ---
        self.pdf_document = None
        self.pdf_files = []
        self.current_folder = ""
        self.current_file_path = ""
        self.rendered_pdf_image = None
        self._resize_job = None
        self.current_page = 0
        self.config_path = os.path.join(os.path.expanduser("~"), ".pdf_annotator_config.txt")
        
        # Annotation Management
        self.highlight_mode = False
        self.text_mode = False
        self.select_mode = False 
        self.eraser_mode = False # New mode for deleting annotations
        self.drag_start_pos = None
        self.word_cache = {}
        self.current_color = (1, 1, 0)
        self.temp_annots = {}
        self.undo_stack = []
        self.redo_stack = []

        # --- Main Layout using PanedWindow ---
        self.main_pane = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        # Left Panel (File List)
        left_frame = tk.Frame(self.main_pane, bg="white")
        self.main_pane.add(left_frame, weight=1)

        # Right Panel (PDF Viewer)
        right_frame = tk.Frame(self.main_pane, bg="gray")
        self.main_pane.add(right_frame, weight=4)
        right_frame.bind("<Configure>", self.on_resize)

        # --- Widgets for Left Panel ---
        select_button = ttk.Button(left_frame, text="Select Folder", command=self.select_folder)
        select_button.pack(pady=10, padx=10, fill=tk.X)
        
        list_frame = tk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.file_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE, exportselection=False, font=("Arial", 11))
        
        v_scroll_list = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        h_scroll_list = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.file_listbox.xview)
        self.file_listbox.configure(yscrollcommand=v_scroll_list.set, xscrollcommand=h_scroll_list.set)
        v_scroll_list.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll_list.pack(side=tk.BOTTOM, fill=tk.X)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)
        self.file_listbox.bind("<Button-3>", self.show_context_menu)
        self.file_listbox.bind("<Return>", self.on_enter_press)


        # --- Widgets for Right Panel ---
        top_bar = tk.Frame(right_frame, bg="white")
        top_bar.pack(fill=tk.X)
        
        self.select_button = ttk.Button(top_bar, text="Select Text", command=self.toggle_select_mode)
        self.select_button.pack(side=tk.LEFT, padx=(10, 2), pady=5)
        self.highlight_button = ttk.Button(top_bar, text="Highlight", command=self.toggle_highlight_mode)
        self.highlight_button.pack(side=tk.LEFT, padx=(2, 2), pady=5)
        self.text_button = ttk.Button(top_bar, text="Add Text", command=self.toggle_text_mode)
        self.text_button.pack(side=tk.LEFT, padx=(2, 2), pady=5)
        self.eraser_button = ttk.Button(top_bar, text="Eraser", command=self.toggle_eraser_mode)
        self.eraser_button.pack(side=tk.LEFT, padx=(2, 2), pady=5)

        self.color_swatch = tk.Frame(top_bar, width=20, height=20, relief="sunken", borderwidth=1)
        self.color_swatch.pack(side=tk.LEFT, pady=5)
        self.update_color_swatch()

        color_button = ttk.Button(top_bar, text="Color", command=self.choose_color, width=5)
        color_button.pack(side=tk.LEFT, padx=(2, 10), pady=5)

        self.save_button = ttk.Button(top_bar, text="Save (Ctrl+S)", command=self.save_pdf, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.undo_button = ttk.Button(top_bar, text="Undo", command=self.undo, state=tk.DISABLED)
        self.undo_button.pack(side=tk.LEFT, padx=(10, 2), pady=5)
        self.redo_button = ttk.Button(top_bar, text="Redo", command=self.redo, state=tk.DISABLED)
        self.redo_button.pack(side=tk.LEFT, padx=2, pady=5)

        self.zoom_var = tk.StringVar(value="Page Width")
        zoom_options = ["Page Width", "50%", "75%", "100%", "125%", "150%", "200%", "250%", "300%", "400%"]
        self.zoom_menu = ttk.Combobox(top_bar, textvariable=self.zoom_var, values=zoom_options, state="readonly", width=12)
        self.zoom_menu.pack(side=tk.LEFT, padx=5, pady=5)
        self.zoom_menu.bind("<<ComboboxSelected>>", lambda e: self.render_current_page(reset_scroll=False))
        
        self.prev_page_button = ttk.Button(top_bar, text="< Prev", command=self.prev_page, state=tk.DISABLED)
        self.prev_page_button.pack(side=tk.LEFT, padx=(10, 2), pady=5)
        self.page_label = tk.Label(top_bar, text="Page 0 of 0", bg="white", font=("Arial", 11))
        self.page_label.pack(side=tk.LEFT, padx=2, pady=5)
        self.next_page_button = ttk.Button(top_bar, text="Next >", command=self.next_page, state=tk.DISABLED)
        self.next_page_button.pack(side=tk.LEFT, padx=(2, 10), pady=5)

        canvas_frame = tk.Frame(right_frame, bg="lightgray", bd=0, highlightthickness=0)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg="lightgray")
        self.v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- Bind global events ---
        self.root.bind("<Control-s>", lambda event: self.save_pdf())
        self.root.bind("<Control-z>", lambda event: self.undo())
        self.root.bind("<Control-y>", lambda event: self.redo())
        self.root.bind("<Left>", lambda event: self.prev_page())
        self.root.bind("<Right>", lambda event: self.next_page())
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self._on_mousewheel)
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_drag_release)
        self.canvas.bind("<Up>", self._on_key_scroll)
        self.canvas.bind("<Down>", self._on_key_scroll)
        self.canvas.bind("<Home>", self.scroll_page_top)
        self.canvas.bind("<End>", self.scroll_page_bottom)
        
        self.root.after(100, self.load_last_folder)

    def _on_mousewheel(self, event):
        if event.state & 0x1:
            scroll_dir = -1 if (event.num == 5 or event.delta < 0) else 1
            self.canvas.xview_scroll(scroll_dir, "units")
        else:
            scroll_dir = 1 if (event.num == 5 or event.delta < 0) else -1
            self.canvas.yview_scroll(scroll_dir, "units")

    def _on_key_scroll(self, event):
        if event.keysym == 'Up': self.canvas.yview_scroll(-2, "units")
        elif event.keysym == 'Down': self.canvas.yview_scroll(2, "units")

    def on_resize(self, event):
        if self._resize_job: self.root.after_cancel(self._resize_job)
        if self.zoom_var.get() == "Page Width":
            self._resize_job = self.root.after(300, lambda: self.render_current_page(reset_scroll=False))

    def select_folder(self, folder_path=None, file_to_select=None):
        if folder_path is None: folder_path = filedialog.askdirectory()
        if not folder_path: return
        
        self.save_last_folder(folder_path)
        self.current_folder = folder_path
        self.pdf_files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")])
        self.file_listbox.delete(0, tk.END)
        for i, pdf_file in enumerate(self.pdf_files):
            self.file_listbox.insert(tk.END, f"{i + 1}. {pdf_file}")
        
        if self.pdf_files:
            index_to_select = 0
            if file_to_select:
                try: index_to_select = self.pdf_files.index(file_to_select)
                except ValueError: pass
            
            self.file_listbox.selection_set(index_to_select)
            self.file_listbox.focus_set()
            self.on_file_select(None)
        else:
            self.canvas.delete("all")

    def on_enter_press(self, event):
        """Selects the focused item when Enter is pressed."""
        self.on_file_select(event, use_active_item=True)

    def on_file_select(self, event, use_active_item=False):
        selected_indices = self.file_listbox.curselection()
        
        if use_active_item:
            try:
                active_index = self.file_listbox.index(tk.ACTIVE)
                if active_index is not None: selected_indices = (active_index,)
            except tk.TclError: return
        
        if not selected_indices: return

        self.file_listbox.selection_clear(0, tk.END)
        self.file_listbox.selection_set(selected_indices[0])
        selected_item = self.file_listbox.get(selected_indices[0])

        try: selected_file = selected_item.split('. ', 1)[1]
        except IndexError: return

        new_file_path = os.path.join(self.current_folder, selected_file)
        if new_file_path == self.current_file_path and self.pdf_document: return
        
        self.current_file_path = new_file_path
        self.root.title("PDF Viewer Application")

        try:
            if self.pdf_document: self.pdf_document.close()
            self.pdf_document = fitz.open(self.current_file_path)
            self.current_page = 0
            self.word_cache = {}
            self.temp_annots.clear()
            for page in self.pdf_document:
                self.temp_annots[page.number] = []
                for annot in page.annots():
                    if annot.type[0] == 8: # Highlight
                        color = annot.colors.get("stroke", (1,1,0)) or (1,1,0)
                        quads = []
                        try: quads = annot.quads()
                        except AttributeError:
                            vertices = annot.vertices
                            if vertices and len(vertices) % 4 == 0:
                                for i in range(0, len(vertices), 4):
                                    quads.append(fitz.Quad(vertices[i], vertices[i+1], vertices[i+2], vertices[i+3]))
                        if quads:
                            bounding_rect = fitz.Rect()
                            for q in quads: bounding_rect.include_rect(q.rect)
                            self.temp_annots[page.number].append({'type': 'highlight', 'quads': quads, 'color': color, 'rect': bounding_rect})
                    elif annot.type[0] == 0: # Text
                        self.temp_annots[page.number].append({'type': 'text', 'rect': annot.rect, 'text': annot.info.get('content', ''), 'color': annot.colors.get('fill', (0,0,0)) or (0,0,0)})
            
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.update_undo_redo_state()
            self.render_current_page(reset_scroll=True)
            self.save_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", f"Error opening PDF {selected_file}:\n{e}")
            self.canvas.delete("all")
            self.save_button.config(state=tk.DISABLED)

    def render_current_page(self, reset_scroll=False):
        if not self.pdf_document: return
        
        current_y_view = self.canvas.yview()
        self.canvas.delete("all")
        canvas_width = self.canvas.winfo_width()
        if canvas_width <= 1: return

        page = self.pdf_document.load_page(self.current_page)
        if self.current_page not in self.word_cache: self.word_cache[self.current_page] = page.get_text("words")
        
        zoom = self.get_current_zoom()
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        base_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples).convert("RGBA")
        overlay = Image.new("RGBA", base_image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        
        page_annots = self.temp_annots.get(self.current_page, [])
        for annot in page_annots:
            color_rgb = annot['color']
            color_int = (int(color_rgb[0]*255), int(color_rgb[1]*255), int(color_rgb[2]*255))
            if annot['type'] == 'highlight':
                color_rgba = color_int + (128,)
                for quad in annot['quads']:
                    points_objects = [quad.ul * mat, quad.ur * mat, quad.lr * mat, quad.ll * mat]
                    flat_points = [(p.x, p.y) for p in points_objects]
                    draw.polygon(flat_points, fill=color_rgba)
            elif annot['type'] == 'text':
                rect = annot['rect'] * mat
                try: font = ImageFont.truetype("Arial.ttf", size=int(11 * zoom))
                except IOError: font = ImageFont.load_default()
                draw.multiline_text((rect.x0, rect.y0), annot['text'], fill=color_int, font=font)

        final_image = Image.alpha_composite(base_image, overlay)
        self.rendered_pdf_image = ImageTk.PhotoImage(final_image)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.rendered_pdf_image)
        self.canvas.config(scrollregion=(0, 0, pix.width, pix.height))
        
        if reset_scroll: self.canvas.yview_moveto(0)
        else: self.root.after(1, lambda: self.canvas.yview_moveto(current_y_view[0]))
            
        self.update_page_nav_buttons()

    def update_page_nav_buttons(self):
        if not self.pdf_document: return
        total_pages = len(self.pdf_document)
        self.page_label.config(text=f"Page {self.current_page + 1} of {total_pages}")
        self.prev_page_button.config(state=tk.NORMAL if self.current_page > 0 else tk.DISABLED)
        self.next_page_button.config(state=tk.NORMAL if self.current_page < total_pages - 1 else tk.DISABLED)

    def prev_page(self):
        if self.current_page > 0: self.current_page -= 1; self.render_current_page(reset_scroll=True)

    def next_page(self):
        if self.pdf_document and self.current_page < len(self.pdf_document) - 1:
            self.current_page += 1; self.render_current_page(reset_scroll=True)
            
    def scroll_page_top(self, event=None):
        if not self.pdf_document: return
        self.canvas.yview_moveto(0.0)

    def scroll_page_bottom(self, event=None):
        if not self.pdf_document: return
        self.canvas.yview_moveto(1.0)

    def set_mode(self, mode):
        self.highlight_mode = mode == 'highlight'
        self.text_mode = mode == 'text'
        self.select_mode = mode == 'select'
        self.eraser_mode = mode == 'eraser'
        
        self.highlight_button.state(['pressed'] if self.highlight_mode else ['!pressed'])
        self.text_button.state(['pressed'] if self.text_mode else ['!pressed'])
        self.select_button.state(['pressed'] if self.select_mode else ['!pressed'])
        self.eraser_button.state(['pressed'] if self.eraser_mode else ['!pressed'])
        
        if self.highlight_mode: self.canvas.config(cursor="crosshair")
        elif self.text_mode: self.canvas.config(cursor="xterm")
        elif self.select_mode: self.canvas.config(cursor="ibeam")
        elif self.eraser_mode: self.canvas.config(cursor="X_cursor")
        else: self.canvas.config(cursor="")

    def toggle_highlight_mode(self): self.set_mode('highlight' if not self.highlight_mode else None)
    def toggle_text_mode(self): self.set_mode('text' if not self.text_mode else None)
    def toggle_select_mode(self): self.set_mode('select' if not self.select_mode else None)
    def toggle_eraser_mode(self): self.set_mode('eraser' if not self.eraser_mode else None)

    def on_canvas_click(self, event):
        self.canvas.focus_set()
        if self.text_mode: self.add_text_annot(event)
        elif self.highlight_mode or self.select_mode: self.start_drag(event)
        elif self.eraser_mode: self.delete_annotation_at(event)

    def start_drag(self, event):
        self.drag_start_pos = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))

    def on_drag_motion(self, event):
        if self.drag_start_pos is None: return
        self.canvas.delete("temp_selection")
        start_x, start_y = self.drag_start_pos
        end_x, end_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.canvas.create_rectangle(start_x, start_y, end_x, end_y, fill="blue", stipple="gray25", outline="", tags="temp_selection")

    def on_drag_release(self, event):
        if self.drag_start_pos is None: return
        self.canvas.delete("temp_selection")
        
        start_x, start_y = self.drag_start_pos
        end_x, end_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.drag_start_pos = None

        selection_rect_canvas = fitz.Rect(min(start_x, end_x), min(start_y, end_y), max(start_x, end_x), max(start_y, end_y))
        
        zoom = self.get_current_zoom()
        words = self.word_cache.get(self.current_page, [])
        selected_word_info = [w for w in words if (fitz.Rect(w[:4]) * zoom).intersects(selection_rect_canvas)]
        
        if not selected_word_info: return

        if self.highlight_mode:
            self.undo_stack.append(copy.deepcopy(self.temp_annots))
            self.redo_stack.clear()
            rects_to_highlight = [fitz.Rect(info[:4]) for info in selected_word_info]
            new_quads = [r.quad for r in rects_to_highlight]
            
            bounding_rect = fitz.Rect()
            for r in rects_to_highlight: bounding_rect.include_rect(r)

            new_highlight = {'type': 'highlight', 'quads': new_quads, 'color': self.current_color, 'rect': bounding_rect}
            if self.current_page not in self.temp_annots: self.temp_annots[self.current_page] = []
            self.temp_annots[self.current_page].append(new_highlight)
            
            self.render_current_page(reset_scroll=False)
            self.update_undo_redo_state()
        
        elif self.select_mode:
            full_text = " ".join([info[4] for info in selected_word_info])
            self.root.clipboard_clear()
            self.root.clipboard_append(full_text)
            self.set_mode(None)
            messagebox.showinfo("Copied", "Selected text has been copied to the clipboard.")


    def add_text_annot(self, event):
        dialog = TextInputDialog(self.root, "Add Text")
        user_text = dialog.result
        if not user_text: return

        zoom = self.get_current_zoom()
        canvas_x, canvas_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        pdf_x, pdf_y = canvas_x / zoom, canvas_y / zoom
        text_rect = fitz.Rect(pdf_x, pdf_y, pdf_x + 200, pdf_y + 50)
        
        self.undo_stack.append(copy.deepcopy(self.temp_annots))
        self.redo_stack.clear()
        new_text = {'type': 'text', 'rect': text_rect, 'text': user_text, 'color': self.current_color}
        if self.current_page not in self.temp_annots: self.temp_annots[self.current_page] = []
        self.temp_annots[self.current_page].append(new_text)
        self.render_current_page(reset_scroll=False)
        self.update_undo_redo_state()
        
    def delete_annotation_at(self, event):
        zoom = self.get_current_zoom()
        canvas_x, canvas_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        click_point_pdf = fitz.Point(canvas_x / zoom, canvas_y / zoom)

        annots_on_page = self.temp_annots.get(self.current_page, [])
        for i in range(len(annots_on_page) - 1, -1, -1):
            annot_data = annots_on_page[i]
            if annot_data['rect'].contains(click_point_pdf):
                self.undo_stack.append(copy.deepcopy(self.temp_annots))
                self.redo_stack.clear()
                annots_on_page.pop(i)
                self.render_current_page(reset_scroll=False)
                self.update_undo_redo_state()
                return

    def get_current_zoom(self):
        if not self.pdf_document: return 1.0
        page = self.pdf_document.load_page(self.current_page)
        canvas_width = self.canvas.winfo_width()
        zoom_mode = self.zoom_var.get()
        
        def get_effective_page_width(p): return p.rect.height if p.rotation in [90, 270] else p.rect.width
        if zoom_mode == "Page Width": return canvas_width / get_effective_page_width(page)
        else: return int(zoom_mode.replace('%','')) / 100.0

    def choose_color(self):
        color_code = askcolor(title="Choose color")
        if color_code and color_code[0]:
            rgb_255 = color_code[0]
            self.current_color = (rgb_255[0]/255, rgb_255[1]/255, rgb_255[2]/255)
            self.update_color_swatch()

    def update_color_swatch(self):
        rgb_255 = (int(self.current_color[0]*255), int(self.current_color[1]*255), int(self.current_color[2]*255))
        hex_color = '#%02x%02x%02x' % rgb_255
        self.color_swatch.config(bg=hex_color)

    def undo(self):
        if not self.undo_stack: return
        self.redo_stack.append(copy.deepcopy(self.temp_annots))
        self.temp_annots = self.undo_stack.pop()
        self.render_current_page(reset_scroll=False)
        self.update_undo_redo_state()

    def redo(self):
        if not self.redo_stack: return
        self.undo_stack.append(copy.deepcopy(self.temp_annots))
        self.temp_annots = self.redo_stack.pop()
        self.render_current_page(reset_scroll=False)
        self.update_undo_redo_state()

    def update_undo_redo_state(self):
        self.undo_button.config(state=tk.NORMAL if self.undo_stack else tk.DISABLED)
        self.redo_button.config(state=tk.NORMAL if self.redo_stack else tk.DISABLED)
        has_changes = bool(self.undo_stack)
        title = "PDF Viewer Application"
        if has_changes: title += "*"
        self.root.title(title)

    def save_pdf(self, show_success=True):
        if not self.pdf_document or not self.current_file_path: return False
        try:
            doc = fitz.open(self.current_file_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                for annot in page.annots(): page.delete_annot(annot)
                
                if page_num in self.temp_annots:
                    for annot_data in self.temp_annots[page_num]:
                        if annot_data['type'] == 'highlight':
                            annot = page.add_highlight_annot(annot_data['quads'])
                            annot.set_colors(stroke=annot_data['color']); annot.update()
                        elif annot_data['type'] == 'text':
                            annot = page.add_freetext_annot(annot_data['rect'], annot_data['text'], fontname="helv", fontsize=11, text_color=annot_data['color'])
            
            doc.save(self.current_file_path, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
            doc.close()
            if show_success: messagebox.showinfo("Save Successful", f"Annotations saved to\n{os.path.basename(self.current_file_path)}")
            
            self.undo_stack.clear(); self.redo_stack.clear(); self.update_undo_redo_state()
            return True
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save file: {e}")
            return False

    def show_context_menu(self, event):
        listbox_index = self.file_listbox.nearest(event.y)
        if listbox_index == -1: return
        self.file_listbox.selection_clear(0, tk.END); self.file_listbox.selection_set(listbox_index)
        
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Rename", command=lambda: self.rename_file(listbox_index))
        context_menu.tk_popup(event.x_root, event.y_root)

    def rename_file(self, index):
        if self.undo_stack:
            if not self.save_pdf(show_success=False): return

        old_name = self.pdf_files[index]
        dialog = RenameDialog(self.root, "Rename File", initialvalue=old_name)
        new_name = dialog.result

        if new_name and new_name != old_name:
            if not new_name.lower().endswith(".pdf"): new_name += ".pdf"
            old_path = os.path.join(self.current_folder, old_name)
            new_path = os.path.join(self.current_folder, new_name)
            
            try:
                if self.current_file_path == old_path and self.pdf_document:
                    self.pdf_document.close(); self.pdf_document = None
                    self.canvas.delete("all"); self.current_file_path = ""
                os.rename(old_path, new_path)
                self.select_folder(self.current_folder, file_to_select=new_name)
            except Exception as e:
                messagebox.showerror("Rename Error", f"Could not rename file: {e}")
    
    def load_last_folder(self):
        """Loads the last opened folder from the config file on startup."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    last_folder = f.read().strip()
                if os.path.isdir(last_folder):
                    self.select_folder(folder_path=last_folder)
        except Exception as e:
            print(f"Could not load last folder: {e}")

    def save_last_folder(self, folder_path):
        """Saves the last opened folder path to the config file."""
        try:
            with open(self.config_path, 'w') as f:
                f.write(folder_path)
        except Exception as e:
            print(f"Could not save config file: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFViewerApp(root)
    root.mainloop()

