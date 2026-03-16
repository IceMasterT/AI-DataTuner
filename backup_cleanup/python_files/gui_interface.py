#!/usr/bin/env python3
"""
GUI Interface for the Text Formatter application.
Simple tkinter-based interface for easy text processing.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
from pathlib import Path
from text_formatter import ConversationFormatter


class TextFormatterGUI:
    """GUI application for text formatting."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Automated Text Formatter")
        self.root.geometry("800x600")
        
        self.formatter = ConversationFormatter()
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Automated Text Classifier & Formatter", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Input section
        ttk.Label(main_frame, text="Input Text:", font=("Arial", 12, "bold")).grid(
            row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        # Input text area
        self.input_text = scrolledtext.ScrolledText(main_frame, height=10, width=70)
        self.input_text.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), 
                            pady=(0, 10))
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=3, column=0, columnspan=3, pady=10)
        
        # Buttons
        ttk.Button(buttons_frame, text="Load File", command=self.load_file).pack(
            side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Process Text", command=self.process_text).pack(
            side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Clear All", command=self.clear_all).pack(
            side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Save Output", command=self.save_output).pack(
            side=tk.LEFT)
        
        # Output section
        ttk.Label(main_frame, text="Formatted Output:", font=("Arial", 12, "bold")).grid(
            row=4, column=0, sticky=tk.W, pady=(20, 5))
        
        # Output text area
        self.output_text = scrolledtext.ScrolledText(main_frame, height=10, width=70)
        self.output_text.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def load_file(self):
        """Load text from a file."""
        file_path = filedialog.askopenfilename(
            title="Select text file",
            filetypes=[("Text files", "*.txt"), ("Markdown files", "*.md"), 
                      ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.input_text.delete(1.0, tk.END)
                self.input_text.insert(1.0, content)
                self.status_var.set(f"Loaded: {Path(file_path).name}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {str(e)}")
                self.status_var.set("Error loading file")
    
    def process_text(self):
        """Process the input text."""
        input_content = self.input_text.get(1.0, tk.END).strip()
        
        if not input_content:
            messagebox.showwarning("Warning", "Please enter some text to process.")
            return
        
        # Show processing status
        self.status_var.set("Processing...")
        self.root.update()
        
        # Process in a separate thread to avoid freezing UI
        def process_thread():
            try:
                formatted_text = self.formatter.process_text(input_content)
                
                # Update UI in main thread
                self.root.after(0, self.update_output, formatted_text)
                
            except Exception as e:
                self.root.after(0, self.show_error, str(e))
        
        threading.Thread(target=process_thread, daemon=True).start()
    
    def update_output(self, formatted_text):
        """Update the output text area."""
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(1.0, formatted_text)
        self.status_var.set("Processing complete")
    
    def show_error(self, error_message):
        """Show error message."""
        messagebox.showerror("Processing Error", f"Failed to process text: {error_message}")
        self.status_var.set("Processing failed")
    
    def clear_all(self):
        """Clear all text areas."""
        self.input_text.delete(1.0, tk.END)
        self.output_text.delete(1.0, tk.END)
        self.status_var.set("Cleared")
    
    def save_output(self):
        """Save the formatted output to a file."""
        output_content = self.output_text.get(1.0, tk.END).strip()
        
        if not output_content:
            messagebox.showwarning("Warning", "No output to save.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save formatted text",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("Markdown files", "*.md"), 
                      ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(output_content)
                
                self.status_var.set(f"Saved: {Path(file_path).name}")
                messagebox.showinfo("Success", "Output saved successfully!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")
                self.status_var.set("Error saving file")


def main():
    """Main function to run the GUI."""
    root = tk.Tk()
    app = TextFormatterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
