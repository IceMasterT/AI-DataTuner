#!/usr/bin/env python3
"""
Graphical User Interface for the AI-Enhanced Pipeline System.
Easy-to-use interface for configuring all pipeline options and personality modifiers.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import json
import threading
from pathlib import Path
from datetime import datetime
import os

from env_config import get_config, EnvironmentConfigLoader
from workflow_orchestrator import WorkflowOrchestrator
from personality_modifier import PersonalityModifier, PersonalityTemplate


class PipelineGUI:
    """Main GUI application for the pipeline system."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI-Enhanced Pipeline System")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # Load configuration
        self.config = get_config()
        self.orchestrator = None
        self.processing_thread = None
        
        # GUI variables
        self.setup_variables()
        
        # Create GUI
        self.create_widgets()
        self.load_current_config()
        
        # Status
        self.status_text = "Ready"
        self.update_status("Pipeline GUI loaded successfully")

    def _load_personality_options(self):
        """Load available personality options including custom ones."""
        # Default templates
        default_personalities = [
            "neutral", "casual", "professional", "technical",
            "creative", "friendly", "formal", "humorous",
            "educational", "conversational"
        ]

        # Load custom personalities
        try:
            from custom_personality_manager import get_custom_personality_manager
            custom_manager = get_custom_personality_manager()
            custom_names = custom_manager.list_personalities()

            # Combine all options
            self.personality_options = default_personalities + [f"custom:{name}" for name in custom_names] + ["custom"]

        except Exception as e:
            self.personality_options = default_personalities + ["custom"]
    
    def setup_variables(self):
        """Setup tkinter variables for all configuration options."""
        # OpenAI Settings
        self.openai_api_key = tk.StringVar(value=self.config.openai_api_key or "")
        self.openai_model = tk.StringVar(value=self.config.openai_model)
        self.daily_cost_limit = tk.DoubleVar(value=self.config.daily_cost_limit)
        
        # AI Features
        self.enable_ai_classification = tk.BooleanVar(value=self.config.enable_ai_classification)
        self.enable_content_enhancement = tk.BooleanVar(value=self.config.enable_content_enhancement)
        self.enable_personality_modifier = tk.BooleanVar(value=False)
        
        # Security Settings
        self.enable_security_filtering = tk.BooleanVar(value=self.config.enable_security_filtering)
        self.security_level = tk.StringVar(value=self.config.security_level)
        
        # Pipeline Settings
        self.input_folder = tk.StringVar(value=self.config.input_folder)
        self.filtered_folder = tk.StringVar(value=self.config.filtered_folder)
        self.output_folder = tk.StringVar(value=self.config.output_folder)
        self.output_format = tk.StringVar(value=self.config.output_format)
        
        # Processing Settings
        self.parallel_processing = tk.BooleanVar(value=self.config.parallel_processing)
        self.max_workers = tk.IntVar(value=self.config.max_workers)
        self.auto_move_files = tk.BooleanVar(value=self.config.auto_move_files)
        
        # Personality Settings
        self.personality_template = tk.StringVar(value="neutral")
        self.custom_personality = tk.StringVar(value="")
        self.personality_strength = tk.DoubleVar(value=0.7)
    
    def create_widgets(self):
        """Create all GUI widgets."""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create tabs
        self.create_main_tab()
        self.create_ai_settings_tab()
        self.create_personality_tab()
        self.create_security_tab()
        self.create_folders_tab()
        self.create_processing_tab()
        self.create_monitoring_tab()
        
        # Create bottom frame for buttons and status
        self.create_bottom_frame()
    
    def create_main_tab(self):
        """Create the main control tab."""
        main_frame = ttk.Frame(self.notebook)
        self.notebook.add(main_frame, text="🚀 Main Control")
        
        # Title
        title_label = ttk.Label(main_frame, text="AI-Enhanced Pipeline System", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Quick start section
        quick_frame = ttk.LabelFrame(main_frame, text="Quick Start", padding=10)
        quick_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # File selection
        file_frame = ttk.Frame(quick_frame)
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_frame, text="Select files to process:").pack(anchor=tk.W)
        
        file_buttons_frame = ttk.Frame(file_frame)
        file_buttons_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(file_buttons_frame, text="📁 Select Files", 
                  command=self.select_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_buttons_frame, text="📂 Select Folder", 
                  command=self.select_folder).pack(side=tk.LEFT, padx=5)
        
        # Selected files display
        self.selected_files_text = scrolledtext.ScrolledText(file_frame, height=4, width=80)
        self.selected_files_text.pack(fill=tk.X, pady=5)
        
        # Processing controls
        control_frame = ttk.LabelFrame(main_frame, text="Processing Controls", padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.start_button = ttk.Button(button_frame, text="🚀 Start Processing", 
                                      command=self.start_processing, style="Accent.TButton")
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="⏹️ Stop", 
                                     command=self.stop_processing, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="📊 View Status", 
                  command=self.show_status).pack(side=tk.LEFT, padx=5)
        
        # Progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding=10)
        progress_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                           maximum=100, length=400)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.progress_label = ttk.Label(progress_frame, text="Ready to process")
        self.progress_label.pack(pady=5)
        
        # Log output
        self.log_text = scrolledtext.ScrolledText(progress_frame, height=10, width=80)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)
    
    def create_ai_settings_tab(self):
        """Create the AI settings tab."""
        ai_frame = ttk.Frame(self.notebook)
        self.notebook.add(ai_frame, text="🤖 AI Settings")
        
        # OpenAI Configuration
        openai_frame = ttk.LabelFrame(ai_frame, text="OpenAI Configuration", padding=10)
        openai_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # API Key
        ttk.Label(openai_frame, text="API Key:").grid(row=0, column=0, sticky=tk.W, pady=2)
        api_key_entry = ttk.Entry(openai_frame, textvariable=self.openai_api_key, 
                                 show="*", width=50)
        api_key_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Button(openai_frame, text="Test Connection", 
                  command=self.test_openai_connection).grid(row=0, column=2, padx=5, pady=2)
        
        # Model Selection
        ttk.Label(openai_frame, text="Model:").grid(row=1, column=0, sticky=tk.W, pady=2)
        model_combo = ttk.Combobox(openai_frame, textvariable=self.openai_model, 
                                  values=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo-preview", 
                                         "gpt-4", "gpt-3.5-turbo"], width=30)
        model_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Daily Cost Limit
        ttk.Label(openai_frame, text="Daily Cost Limit ($):").grid(row=2, column=0, sticky=tk.W, pady=2)
        cost_spin = ttk.Spinbox(openai_frame, from_=1.0, to=100.0, increment=1.0, 
                               textvariable=self.daily_cost_limit, width=10)
        cost_spin.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # AI Features
        features_frame = ttk.LabelFrame(ai_frame, text="AI Features", padding=10)
        features_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Checkbutton(features_frame, text="Enable AI Classification", 
                       variable=self.enable_ai_classification).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(features_frame, text="Enable Content Enhancement", 
                       variable=self.enable_content_enhancement).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(features_frame, text="Enable Personality Modifier", 
                       variable=self.enable_personality_modifier).pack(anchor=tk.W, pady=2)
        
        # Cost Information
        cost_frame = ttk.LabelFrame(ai_frame, text="Cost Information", padding=10)
        cost_frame.pack(fill=tk.X, padx=10, pady=5)
        
        cost_info = """
Typical costs per file:
• Classification (gpt-4o-mini): ~$0.0004
• Enhancement (gpt-4o): ~$0.010
• High-quality (gpt-4-turbo): ~$0.020

Cost optimization features:
• Intelligent caching (30-50% savings)
• Automatic daily limits
• Model selection based on task complexity
        """
        ttk.Label(cost_frame, text=cost_info.strip(), justify=tk.LEFT).pack(anchor=tk.W)
    
    def create_personality_tab(self):
        """Create the personality modifier tab."""
        personality_frame = ttk.Frame(self.notebook)
        self.notebook.add(personality_frame, text="🎭 Personality")
        
        # Personality Templates
        template_frame = ttk.LabelFrame(personality_frame, text="Personality Templates", padding=10)
        template_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(template_frame, text="Select a personality template:").pack(anchor=tk.W, pady=2)
        
        # Load available personalities
        self._load_personality_options()

        template_combo = ttk.Combobox(template_frame, textvariable=self.personality_template,
                                     values=self.personality_options, width=30)
        template_combo.pack(anchor=tk.W, pady=5)
        template_combo.bind('<<ComboboxSelected>>', self.on_personality_template_change)
        
        # Personality Strength
        strength_frame = ttk.Frame(template_frame)
        strength_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(strength_frame, text="Personality Strength:").pack(side=tk.LEFT)
        strength_scale = ttk.Scale(strength_frame, from_=0.1, to=1.0, 
                                  variable=self.personality_strength, orient=tk.HORIZONTAL)
        strength_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        strength_label = ttk.Label(strength_frame, text="0.7")
        strength_label.pack(side=tk.LEFT)
        
        def update_strength_label(*args):
            strength_label.config(text=f"{self.personality_strength.get():.1f}")
        
        self.personality_strength.trace('w', update_strength_label)
        
        # Custom Personality
        custom_frame = ttk.LabelFrame(personality_frame, text="Custom Personality", padding=10)
        custom_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        ttk.Label(custom_frame, text="Describe the personality/style you want:").pack(anchor=tk.W, pady=2)
        
        self.custom_personality_text = scrolledtext.ScrolledText(custom_frame, height=8, width=80)
        self.custom_personality_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Personality preview
        preview_frame = ttk.Frame(custom_frame)
        preview_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(preview_frame, text="🔍 Preview Personality",
                  command=self.preview_personality).pack(side=tk.LEFT, padx=5)
        ttk.Button(preview_frame, text="💾 Save Custom Personality",
                  command=self.save_custom_personality).pack(side=tk.LEFT, padx=5)
        ttk.Button(preview_frame, text="📚 Manage Personalities",
                  command=self.manage_personalities).pack(side=tk.LEFT, padx=5)
        
        # Example personalities
        examples_frame = ttk.LabelFrame(personality_frame, text="Example Personalities", padding=10)
        examples_frame.pack(fill=tk.X, padx=10, pady=5)
        
        examples_text = """
Examples of personality descriptions:
• "Casual and friendly, uses modern slang and emojis"
• "Professional but approachable, like a knowledgeable colleague"
• "Technical expert who explains things clearly with examples"
• "Creative and imaginative, uses metaphors and storytelling"
• "Humorous and witty, makes learning fun with jokes"
        """
        ttk.Label(examples_frame, text=examples_text.strip(), justify=tk.LEFT).pack(anchor=tk.W)
    
    def create_security_tab(self):
        """Create the security settings tab."""
        security_frame = ttk.Frame(self.notebook)
        self.notebook.add(security_frame, text="🛡️ Security")
        
        # Security Settings
        settings_frame = ttk.LabelFrame(security_frame, text="Security Settings", padding=10)
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Checkbutton(settings_frame, text="Enable Security Filtering", 
                       variable=self.enable_security_filtering).pack(anchor=tk.W, pady=2)
        
        ttk.Label(settings_frame, text="Security Level:").pack(anchor=tk.W, pady=2)
        security_combo = ttk.Combobox(settings_frame, textvariable=self.security_level,
                                     values=["permissive", "balanced", "strict", "paranoid"], 
                                     width=20)
        security_combo.pack(anchor=tk.W, pady=5)
        
        # Security Information
        info_frame = ttk.LabelFrame(security_frame, text="Security Features", padding=10)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        security_info = """
Security Protection Layers:

🔍 Unicode Analysis
• Normalization and invisible character removal
• Homoglyph detection and script mixing analysis
• Direction override and steganography detection

📊 Content Analysis
• Entropy analysis and token pollution detection
• Statistical character distribution analysis
• Pattern recognition for adversarial content

🔒 Code Validation
• HTML/JSON/XML/Markdown validation
• XSS and injection pattern detection
• Dangerous function and keyword filtering

🗃️ Quarantine System
• Automatic isolation of suspicious content
• Detailed threat analysis and logging
• Review workflow with approval/rejection
        """
        
        info_text = scrolledtext.ScrolledText(info_frame, height=15, width=80)
        info_text.insert(tk.END, security_info.strip())
        info_text.config(state=tk.DISABLED)
        info_text.pack(fill=tk.BOTH, expand=True)
    
    def create_folders_tab(self):
        """Create the folders configuration tab."""
        folders_frame = ttk.Frame(self.notebook)
        self.notebook.add(folders_frame, text="📁 Folders")
        
        # Folder Settings
        settings_frame = ttk.LabelFrame(folders_frame, text="Pipeline Folders", padding=10)
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Input Folder
        self.create_folder_row(settings_frame, "Input Folder:", self.input_folder, 0)
        
        # Filtered Folder
        self.create_folder_row(settings_frame, "Filtered Folder:", self.filtered_folder, 1)
        
        # Output Folder
        self.create_folder_row(settings_frame, "Output Folder:", self.output_folder, 2)
        
        # Output Format
        ttk.Label(settings_frame, text="Output Format:").grid(row=3, column=0, sticky=tk.W, pady=5)
        format_combo = ttk.Combobox(settings_frame, textvariable=self.output_format,
                                   values=["qwen", "alpaca", "chatml", "sharegpt", "llama2", 
                                          "vicuna", "openai", "anthropic", "mistral", "gemma"], 
                                   width=20)
        format_combo.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Folder Status
        status_frame = ttk.LabelFrame(folders_frame, text="Folder Status", padding=10)
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.folder_status_text = scrolledtext.ScrolledText(status_frame, height=10, width=80)
        self.folder_status_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Button(status_frame, text="🔄 Refresh Status", 
                  command=self.refresh_folder_status).pack(pady=5)
        
        # Initialize folder status
        self.refresh_folder_status()
    
    def create_folder_row(self, parent, label_text, var, row):
        """Create a folder selection row."""
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky=tk.W, pady=5)
        
        entry = ttk.Entry(parent, textvariable=var, width=40)
        entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        
        def browse_folder():
            folder = filedialog.askdirectory(initialdir=var.get())
            if folder:
                var.set(folder)
        
        ttk.Button(parent, text="Browse", command=browse_folder).grid(row=row, column=2, padx=5, pady=5)
    
    def create_processing_tab(self):
        """Create the processing settings tab."""
        processing_frame = ttk.Frame(self.notebook)
        self.notebook.add(processing_frame, text="⚙️ Processing")
        
        # Processing Settings
        settings_frame = ttk.LabelFrame(processing_frame, text="Processing Settings", padding=10)
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Checkbutton(settings_frame, text="Enable Parallel Processing", 
                       variable=self.parallel_processing).pack(anchor=tk.W, pady=2)
        
        ttk.Checkbutton(settings_frame, text="Auto Move Files", 
                       variable=self.auto_move_files).pack(anchor=tk.W, pady=2)
        
        # Max Workers
        workers_frame = ttk.Frame(settings_frame)
        workers_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(workers_frame, text="Max Workers:").pack(side=tk.LEFT)
        workers_spin = ttk.Spinbox(workers_frame, from_=1, to=16, 
                                  textvariable=self.max_workers, width=10)
        workers_spin.pack(side=tk.LEFT, padx=10)
        
        # File Format Support
        formats_frame = ttk.LabelFrame(processing_frame, text="Supported File Formats", padding=10)
        formats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        formats_info = """
Input Formats Supported:
• PDF - Document text extraction
• CSV - Structured Q&A data
• JSON - Conversation data (ShareGPT, etc.)
• JSONL - Line-delimited JSON
• TXT/MD - Plain text and Markdown

Output Formats Available:
• Qwen, Alpaca, ChatML, ShareGPT
• Llama-2, Vicuna, OpenAI, Anthropic
• Mistral, Gemma (10 total formats)
        """
        ttk.Label(formats_frame, text=formats_info.strip(), justify=tk.LEFT).pack(anchor=tk.W)
    
    def create_monitoring_tab(self):
        """Create the monitoring and statistics tab."""
        monitoring_frame = ttk.Frame(self.notebook)
        self.notebook.add(monitoring_frame, text="📊 Monitoring")
        
        # Real-time Stats
        stats_frame = ttk.LabelFrame(monitoring_frame, text="Real-time Statistics", padding=10)
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.stats_text = scrolledtext.ScrolledText(stats_frame, height=8, width=80)
        self.stats_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Button(stats_frame, text="🔄 Refresh Stats", 
                  command=self.refresh_stats).pack(pady=5)
        
        # Cost Tracking
        cost_frame = ttk.LabelFrame(monitoring_frame, text="Cost Tracking", padding=10)
        cost_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.cost_text = scrolledtext.ScrolledText(cost_frame, height=6, width=80)
        self.cost_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Log Viewer
        log_frame = ttk.LabelFrame(monitoring_frame, text="Recent Logs", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_viewer = scrolledtext.ScrolledText(log_frame, height=8, width=80)
        self.log_viewer.pack(fill=tk.BOTH, expand=True, pady=5)
        
        log_buttons = ttk.Frame(log_frame)
        log_buttons.pack(fill=tk.X, pady=5)
        
        ttk.Button(log_buttons, text="🔄 Refresh Logs", 
                  command=self.refresh_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_buttons, text="🗑️ Clear Logs", 
                  command=self.clear_logs).pack(side=tk.LEFT, padx=5)
    
    def create_bottom_frame(self):
        """Create the bottom frame with buttons and status."""
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(bottom_frame)
        button_frame.pack(side=tk.LEFT)
        
        ttk.Button(button_frame, text="💾 Save Config", 
                  command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📂 Load Config", 
                  command=self.load_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🔄 Reset to Defaults", 
                  command=self.reset_config).pack(side=tk.LEFT, padx=5)
        
        # Status bar
        initial_text = getattr(self, 'status_text', 'Ready')
        self.status_bar = ttk.Label(bottom_frame, text=initial_text, relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=10)
    
    def load_current_config(self):
        """Load current configuration into GUI."""
        try:
            # Load configuration from environment
            config = get_config()

            # Update GUI variables with loaded config
            if config.openai_api_key:
                self.openai_api_key.set(config.openai_api_key)

            if config.openai_model:
                self.openai_model.set(config.openai_model)

            if config.daily_cost_limit:
                self.daily_cost_limit.set(config.daily_cost_limit)

            if config.output_format:
                self.output_format.set(config.output_format)

            # Update boolean settings
            self.enable_ai_classification.set(config.enable_ai_classification)
            self.enable_content_enhancement.set(config.enable_content_enhancement)
            self.enable_security_filtering.set(config.enable_security_filtering)
            self.enable_personality_modifier.set(config.enable_personality_modifier)

            # Update folder paths
            if config.input_folder:
                self.input_folder.set(config.input_folder)
            if config.filtered_folder:
                self.filtered_folder.set(config.filtered_folder)
            if config.output_folder:
                self.output_folder.set(config.output_folder)

            # Update personality settings
            if config.personality_template:
                self.personality_template.set(config.personality_template)
            if config.personality_strength:
                self.personality_strength.set(config.personality_strength)

            # Update security settings
            if config.security_level:
                self.security_level.set(config.security_level)

            self.log_message("Configuration loaded successfully")

        except Exception as e:
            self.log_message(f"Error loading configuration: {e}")
            # Use default values if loading fails
    
    def update_status(self, message):
        """Update the status bar."""
        if hasattr(self, 'status_bar'):
            self.status_bar.config(text=f"{datetime.now().strftime('%H:%M:%S')} - {message}")
            self.root.update_idletasks()
        else:
            # Status bar not created yet, just store the message
            self.status_text = message
    
    def log_message(self, message):
        """Add message to log display."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def select_files(self):
        """Select files for processing."""
        files = filedialog.askopenfilenames(
            title="Select files to process",
            filetypes=[
                ("All supported", "*.pdf;*.csv;*.json;*.jsonl;*.txt;*.md"),
                ("PDF files", "*.pdf"),
                ("CSV files", "*.csv"),
                ("JSON files", "*.json"),
                ("JSONL files", "*.jsonl"),
                ("Text files", "*.txt;*.md"),
                ("All files", "*.*")
            ]
        )

        if files:
            self.selected_files_text.delete(1.0, tk.END)
            for file in files:
                self.selected_files_text.insert(tk.END, f"{file}\n")
            self.update_status(f"Selected {len(files)} files")

    def select_folder(self):
        """Select folder for processing."""
        folder = filedialog.askdirectory(title="Select folder to process")
        if folder:
            self.input_folder.set(folder)
            self.selected_files_text.delete(1.0, tk.END)
            self.selected_files_text.insert(tk.END, f"Folder: {folder}\n")
            self.update_status(f"Selected folder: {folder}")

    def test_openai_connection(self):
        """Test OpenAI API connection."""
        if not self.openai_api_key.get():
            messagebox.showerror("Error", "Please enter your OpenAI API key")
            return

        self.update_status("Testing OpenAI connection...")

        def test_connection():
            try:
                from openai_integration import OpenAIConfig, OpenAIClient

                config = OpenAIConfig(
                    api_key=self.openai_api_key.get(),
                    model=self.openai_model.get()
                )

                client = OpenAIClient(config)
                result = client.make_request("Test connection", "You are a helpful assistant.")

                self.root.after(0, lambda: messagebox.showinfo(
                    "Success",
                    f"OpenAI connection successful!\nModel: {self.openai_model.get()}\nCost: ${result['cost']:.6f}"
                ))
                self.root.after(0, lambda: self.update_status("OpenAI connection test successful"))

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"OpenAI connection failed: {e}"))
                self.root.after(0, lambda: self.update_status("OpenAI connection test failed"))

        threading.Thread(target=test_connection, daemon=True).start()

    def on_personality_template_change(self, event=None):
        """Handle personality template selection change."""
        template = self.personality_template.get()

        if template == "custom":
            self.custom_personality_text.config(state=tk.NORMAL)
        else:
            # Load predefined personality
            personalities = {
                "neutral": "Maintain a neutral, balanced tone without adding personality",
                "casual": "Use casual, friendly language with modern expressions and a relaxed tone",
                "professional": "Maintain professional language while being approachable and clear",
                "technical": "Use precise technical language with detailed explanations and examples",
                "creative": "Use imaginative language with metaphors, storytelling, and creative expressions",
                "friendly": "Be warm, encouraging, and supportive with a positive attitude",
                "formal": "Use formal, academic language with proper structure and terminology",
                "humorous": "Add appropriate humor, wit, and light-hearted comments to make content engaging",
                "educational": "Focus on clear explanations, step-by-step guidance, and learning-oriented language",
                "conversational": "Use natural, dialogue-like language as if speaking with a friend"
            }

            if template in personalities:
                self.custom_personality_text.delete(1.0, tk.END)
                self.custom_personality_text.insert(1.0, personalities[template])
                self.custom_personality_text.config(state=tk.DISABLED)

    def preview_personality(self):
        """Preview personality modification."""
        sample_text = "What is machine learning? Machine learning is a method of data analysis that automates analytical model building."

        personality_desc = self.custom_personality_text.get(1.0, tk.END).strip()
        if not personality_desc:
            messagebox.showwarning("Warning", "Please enter a personality description")
            return

        self.update_status("Generating personality preview...")

        def generate_preview():
            try:
                from personality_modifier import PersonalityModifier

                modifier = PersonalityModifier()
                result = modifier.apply_personality(
                    sample_text,
                    personality_desc,
                    strength=self.personality_strength.get()
                )

                preview_window = tk.Toplevel(self.root)
                preview_window.title("Personality Preview")
                preview_window.geometry("600x400")

                ttk.Label(preview_window, text="Original:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=10, pady=5)

                original_text = scrolledtext.ScrolledText(preview_window, height=4, width=70)
                original_text.pack(fill=tk.X, padx=10, pady=5)
                original_text.insert(1.0, sample_text)
                original_text.config(state=tk.DISABLED)

                ttk.Label(preview_window, text="With Personality:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=10, pady=5)

                modified_text = scrolledtext.ScrolledText(preview_window, height=4, width=70)
                modified_text.pack(fill=tk.X, padx=10, pady=5)
                modified_text.insert(1.0, result.get('modified_text', sample_text))
                modified_text.config(state=tk.DISABLED)

                info_text = f"Cost: ${result.get('cost', 0):.6f} | Confidence: {result.get('confidence', 0):.2f}"
                ttk.Label(preview_window, text=info_text).pack(pady=5)

                self.root.after(0, lambda: self.update_status("Personality preview generated"))

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Preview failed: {e}"))
                self.root.after(0, lambda: self.update_status("Personality preview failed"))

        threading.Thread(target=generate_preview, daemon=True).start()

    def save_custom_personality(self):
        """Save custom personality template."""
        personality_desc = self.custom_personality_text.get(1.0, tk.END).strip()
        if not personality_desc:
            messagebox.showwarning("Warning", "Please enter a personality description")
            return

        name = tk.simpledialog.askstring("Save Personality", "Enter a name for this personality:")
        if name:
            # Save to personalities file
            personalities_file = Path("personalities.json")
            personalities = {}

            if personalities_file.exists():
                with open(personalities_file, 'r') as f:
                    personalities = json.load(f)

            personalities[name] = {
                "description": personality_desc,
                "strength": self.personality_strength.get(),
                "created": datetime.now().isoformat()
            }

            with open(personalities_file, 'w') as f:
                json.dump(personalities, f, indent=2)

            messagebox.showinfo("Success", f"Personality '{name}' saved successfully!")
            self.update_status(f"Saved personality: {name}")

            # Refresh personality options
            self._load_personality_options()

    def manage_personalities(self):
        """Open personality management window."""
        manage_window = tk.Toplevel(self.root)
        manage_window.title("Manage Custom Personalities")
        manage_window.geometry("800x600")

        # Create notebook for management tabs
        notebook = ttk.Notebook(manage_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Browse tab
        browse_frame = ttk.Frame(notebook)
        notebook.add(browse_frame, text="📚 Browse")

        # Create tab
        create_frame = ttk.Frame(notebook)
        notebook.add(create_frame, text="➕ Create")

        # Import/Export tab
        import_frame = ttk.Frame(notebook)
        notebook.add(import_frame, text="📁 Import/Export")

        self._create_browse_tab(browse_frame)
        self._create_create_tab(create_frame)
        self._create_import_export_tab(import_frame)

    def _create_browse_tab(self, parent):
        """Create the browse personalities tab."""
        # Personality list
        list_frame = ttk.LabelFrame(parent, text="Custom Personalities", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Treeview for personalities
        columns = ("Name", "Description", "Tags", "Usage")
        self.personality_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)

        for col in columns:
            self.personality_tree.heading(col, text=col)
            self.personality_tree.column(col, width=150)

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.personality_tree.yview)
        self.personality_tree.configure(yscrollcommand=scrollbar.set)

        self.personality_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(button_frame, text="🔄 Refresh",
                  command=self._refresh_personality_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="✏️ Edit",
                  command=self._edit_selected_personality).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🗑️ Delete",
                  command=self._delete_selected_personality).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🧪 Test",
                  command=self._test_selected_personality).pack(side=tk.LEFT, padx=5)

        # Load initial data
        self._refresh_personality_list()

    def _create_create_tab(self, parent):
        """Create the create personality tab."""
        create_frame = ttk.LabelFrame(parent, text="Create New Personality", padding=10)
        create_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Name
        ttk.Label(create_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.new_personality_name = tk.StringVar()
        ttk.Entry(create_frame, textvariable=self.new_personality_name, width=40).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        # Description
        ttk.Label(create_frame, text="Description:").grid(row=1, column=0, sticky=tk.NW, pady=5)
        self.new_personality_desc = scrolledtext.ScrolledText(create_frame, height=8, width=60)
        self.new_personality_desc.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        # Strength
        ttk.Label(create_frame, text="Default Strength:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.new_personality_strength = tk.DoubleVar(value=0.7)
        strength_frame = ttk.Frame(create_frame)
        strength_frame.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Scale(strength_frame, from_=0.1, to=1.0, variable=self.new_personality_strength,
                 orient=tk.HORIZONTAL, length=200).pack(side=tk.LEFT)
        strength_label = ttk.Label(strength_frame, text="0.7")
        strength_label.pack(side=tk.LEFT, padx=10)

        def update_strength_label(*args):
            strength_label.config(text=f"{self.new_personality_strength.get():.1f}")
        self.new_personality_strength.trace('w', update_strength_label)

        # Tags
        ttk.Label(create_frame, text="Tags (comma-separated):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.new_personality_tags = tk.StringVar(value="custom")
        ttk.Entry(create_frame, textvariable=self.new_personality_tags, width=40).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)

        # Create button
        ttk.Button(create_frame, text="✅ Create Personality",
                  command=self._create_new_personality).grid(row=4, column=1, sticky=tk.W, padx=5, pady=10)

    def _create_import_export_tab(self, parent):
        """Create the import/export tab."""
        # Export section
        export_frame = ttk.LabelFrame(parent, text="Export Personalities", padding=10)
        export_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(export_frame, text="📤 Export All Personalities",
                  command=self._export_personalities).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="📤 Export Selected",
                  command=self._export_selected_personalities).pack(side=tk.LEFT, padx=5)

        # Import section
        import_frame = ttk.LabelFrame(parent, text="Import Personalities", padding=10)
        import_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(import_frame, text="📥 Import from File",
                  command=self._import_personalities).pack(side=tk.LEFT, padx=5)

        # Statistics section
        stats_frame = ttk.LabelFrame(parent, text="Statistics", padding=10)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.stats_text = scrolledtext.ScrolledText(stats_frame, height=10, width=70)
        self.stats_text.pack(fill=tk.BOTH, expand=True, pady=5)

        ttk.Button(stats_frame, text="🔄 Refresh Stats",
                  command=self._refresh_stats).pack(pady=5)

        # Load initial stats
        self._refresh_stats()

    def _refresh_personality_list(self):
        """Refresh the personality list in the browse tab."""
        # Clear existing items
        for item in self.personality_tree.get_children():
            self.personality_tree.delete(item)

        try:
            from custom_personality_manager import get_custom_personality_manager
            manager = get_custom_personality_manager()

            for name, personality in manager.custom_personalities.items():
                tags_str = ", ".join(personality.tags[:3])  # Limit to 3 tags
                desc_str = personality.description[:50] + "..." if len(personality.description) > 50 else personality.description

                self.personality_tree.insert("", "end", values=(
                    name,
                    desc_str,
                    tags_str,
                    personality.usage_count
                ))

        except Exception as e:
            print(f"Error refreshing personality list: {e}")

    def _edit_selected_personality(self):
        """Edit the selected personality."""
        selection = self.personality_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a personality to edit")
            return

        item = self.personality_tree.item(selection[0])
        personality_name = item['values'][0]

        # Open comprehensive edit dialog
        self._open_personality_editor(personality_name)

    def _open_personality_editor(self, personality_name: str):
        """Open a comprehensive personality editor dialog."""
        try:
            # Get the personality data
            personality = self.custom_personality_manager.get_personality(personality_name)

            # Create edit window
            edit_window = tk.Toplevel(self.root)
            edit_window.title(f"Edit Personality: {personality_name}")
            edit_window.geometry("600x500")
            edit_window.transient(self.root)
            edit_window.grab_set()

            # Name field
            name_frame = ttk.Frame(edit_window)
            name_frame.pack(fill=tk.X, padx=10, pady=5)

            ttk.Label(name_frame, text="Name:").pack(side=tk.LEFT)
            name_var = tk.StringVar(value=personality.name)
            name_entry = ttk.Entry(name_frame, textvariable=name_var, width=40)
            name_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

            # Description field
            desc_frame = ttk.LabelFrame(edit_window, text="Description", padding=10)
            desc_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            desc_text = scrolledtext.ScrolledText(desc_frame, height=15, width=70)
            desc_text.pack(fill=tk.BOTH, expand=True)
            desc_text.insert(1.0, personality.description)

            # Tags field
            tags_frame = ttk.Frame(edit_window)
            tags_frame.pack(fill=tk.X, padx=10, pady=5)

            ttk.Label(tags_frame, text="Tags (comma-separated):").pack(side=tk.LEFT)
            tags_var = tk.StringVar(value=", ".join(getattr(personality, 'tags', [])))
            tags_entry = ttk.Entry(tags_frame, textvariable=tags_var, width=40)
            tags_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

            # Buttons
            button_frame = ttk.Frame(edit_window)
            button_frame.pack(fill=tk.X, padx=10, pady=5)

            def save_changes():
                try:
                    # Update personality
                    new_name = name_var.get().strip()
                    new_description = desc_text.get(1.0, tk.END).strip()
                    new_tags = [tag.strip() for tag in tags_var.get().split(',') if tag.strip()]

                    if not new_name or not new_description:
                        messagebox.showwarning("Warning", "Name and description are required")
                        return

                    # Create updated personality
                    from custom_personality_manager import CustomPersonality
                    updated_personality = CustomPersonality(
                        name=new_name,
                        description=new_description,
                        tags=new_tags
                    )

                    # Delete old if name changed
                    if new_name != personality_name:
                        self.custom_personality_manager.delete_personality(personality_name)

                    # Save updated personality
                    self.custom_personality_manager.save_personality(updated_personality)

                    # Refresh the personality list
                    self._refresh_personality_list()

                    messagebox.showinfo("Success", f"Personality '{new_name}' updated successfully!")
                    self.log_message(f"Updated personality: {new_name}")

                    edit_window.destroy()

                except Exception as e:
                    messagebox.showerror("Error", f"Failed to update personality: {e}")
                    self.log_message(f"Error updating personality: {e}")

            ttk.Button(button_frame, text="Save Changes", command=save_changes).pack(side=tk.RIGHT, padx=5)
            ttk.Button(button_frame, text="Cancel", command=edit_window.destroy).pack(side=tk.RIGHT, padx=5)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open personality editor: {e}")
            self.log_message(f"Error opening personality editor: {e}")

    def _delete_selected_personality(self):
        """Delete the selected personality."""
        selection = self.personality_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a personality to delete")
            return

        item = self.personality_tree.item(selection[0])
        personality_name = item['values'][0]

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{personality_name}'?"):
            try:
                from custom_personality_manager import get_custom_personality_manager
                manager = get_custom_personality_manager()

                if manager.delete_personality(personality_name):
                    messagebox.showinfo("Success", f"Deleted personality '{personality_name}'")
                    self._refresh_personality_list()
                else:
                    messagebox.showerror("Error", f"Failed to delete personality '{personality_name}'")

            except Exception as e:
                messagebox.showerror("Error", f"Error deleting personality: {e}")

    def _test_selected_personality(self):
        """Test the selected personality."""
        selection = self.personality_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a personality to test")
            return

        item = self.personality_tree.item(selection[0])
        personality_name = item['values'][0]

        # Use the existing preview functionality
        sample_text = "This is a sample text to demonstrate the personality transformation."

        try:
            from personality_modifier import PersonalityModifier
            modifier = PersonalityModifier()

            result = modifier.apply_personality(sample_text, personality_name, 0.7)

            # Show result in a popup
            test_window = tk.Toplevel(self.root)
            test_window.title(f"Test: {personality_name}")
            test_window.geometry("600x400")

            ttk.Label(test_window, text="Original:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=10, pady=5)

            original_text = scrolledtext.ScrolledText(test_window, height=4, width=70)
            original_text.pack(fill=tk.X, padx=10, pady=5)
            original_text.insert(1.0, sample_text)
            original_text.config(state=tk.DISABLED)

            ttk.Label(test_window, text="Transformed:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=10, pady=5)

            modified_text = scrolledtext.ScrolledText(test_window, height=4, width=70)
            modified_text.pack(fill=tk.X, padx=10, pady=5)
            modified_text.insert(1.0, result.modified_text)
            modified_text.config(state=tk.DISABLED)

            info_text = f"Confidence: {result.confidence:.2f} | Cost: ${result.cost:.6f}"
            ttk.Label(test_window, text=info_text).pack(pady=5)

        except Exception as e:
            messagebox.showerror("Error", f"Test failed: {e}")

    def _create_new_personality(self):
        """Create a new personality from the form."""
        name = self.new_personality_name.get().strip()
        description = self.new_personality_desc.get(1.0, tk.END).strip()
        strength = self.new_personality_strength.get()
        tags = [tag.strip() for tag in self.new_personality_tags.get().split(",") if tag.strip()]

        if not name:
            messagebox.showerror("Error", "Please enter a personality name")
            return

        if not description:
            messagebox.showerror("Error", "Please enter a personality description")
            return

        try:
            from custom_personality_manager import get_custom_personality_manager, CustomPersonality
            manager = get_custom_personality_manager()

            # Check if personality already exists
            if manager.get_personality(name):
                messagebox.showerror("Error", f"Personality '{name}' already exists")
                return

            # Create new personality
            personality = CustomPersonality(
                name=name,
                description=description,
                strength=strength,
                tags=tags or ["custom"]
            )

            if manager.add_personality(personality):
                messagebox.showinfo("Success", f"Created personality '{name}'")

                # Clear form
                self.new_personality_name.set("")
                self.new_personality_desc.delete(1.0, tk.END)
                self.new_personality_strength.set(0.7)
                self.new_personality_tags.set("custom")

                # Refresh lists
                self._refresh_personality_list()
                self._load_personality_options()
            else:
                messagebox.showerror("Error", f"Failed to create personality '{name}'")

        except Exception as e:
            messagebox.showerror("Error", f"Error creating personality: {e}")

    def _export_personalities(self):
        """Export all personalities to a file."""
        file_path = filedialog.asksaveasfilename(
            title="Export Personalities",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if file_path:
            try:
                from custom_personality_manager import get_custom_personality_manager
                manager = get_custom_personality_manager()

                if manager.export_personalities(file_path):
                    messagebox.showinfo("Success", f"Exported personalities to {file_path}")
                else:
                    messagebox.showerror("Error", "Failed to export personalities")

            except Exception as e:
                messagebox.showerror("Error", f"Export failed: {e}")

    def _export_selected_personalities(self):
        """Export selected personalities to file."""
        selection = self.personality_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select personalities to export")
            return

        # Get selected personality names
        selected_names = []
        for item_id in selection:
            item = self.personality_tree.item(item_id)
            selected_names.append(item['values'][0])

        # Choose export file
        file_path = filedialog.asksaveasfilename(
            title="Export Selected Personalities",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            # Export selected personalities
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'personalities': []
            }

            for name in selected_names:
                try:
                    personality = self.custom_personality_manager.get_personality(name)
                    export_data['personalities'].append({
                        'name': personality.name,
                        'description': personality.description,
                        'tags': getattr(personality, 'tags', []),
                        'strength': getattr(personality, 'strength', 0.7)
                    })
                except Exception as e:
                    self.log_message(f"Warning: Could not export {name}: {e}")

            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)

            messagebox.showinfo("Success", f"Exported {len(export_data['personalities'])} personalities to {file_path}")
            self.log_message(f"Exported {len(selected_names)} personalities")

        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")
            self.log_message(f"Export error: {e}")

    def _import_personalities(self):
        """Import personalities from a file."""
        file_path = filedialog.askopenfilename(
            title="Import Personalities",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if file_path:
            try:
                from custom_personality_manager import get_custom_personality_manager
                manager = get_custom_personality_manager()

                imported_count = manager.import_personalities(file_path, overwrite=False)

                if imported_count > 0:
                    messagebox.showinfo("Success", f"Imported {imported_count} personalities")
                    self._refresh_personality_list()
                    self._load_personality_options()
                else:
                    messagebox.showwarning("Warning", "No personalities were imported")

            except Exception as e:
                messagebox.showerror("Error", f"Import failed: {e}")

    def _refresh_stats(self):
        """Refresh statistics display."""
        try:
            from custom_personality_manager import get_custom_personality_manager
            manager = get_custom_personality_manager()
            stats = manager.get_usage_statistics()

            self.stats_text.delete(1.0, tk.END)

            stats_info = f"""Personality Statistics:

Total Personalities: {stats['total_personalities']}
Environment Personalities: {stats['env_personalities']}
File Personalities: {stats['file_personalities']}

Most Used: {stats['most_used'] or 'None'} ({stats['most_used_count']} times)

Individual Usage:
"""

            self.stats_text.insert(tk.END, stats_info)

            for name, data in stats['personalities'].items():
                usage_line = f"  {name}: {data['usage_count']} times"
                if data['last_used']:
                    usage_line += f" (last: {data['last_used'][:10]})"
                usage_line += "\n"
                self.stats_text.insert(tk.END, usage_line)

        except Exception as e:
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(tk.END, f"Error loading stats: {e}")

    def start_processing(self):
        """Start the processing pipeline."""
        # Validate configuration
        if self.enable_ai_classification.get() and not self.openai_api_key.get():
            messagebox.showerror("Error", "OpenAI API key required for AI features")
            return

        # Get selected files
        selected_text = self.selected_files_text.get(1.0, tk.END).strip()
        if not selected_text:
            messagebox.showerror("Error", "Please select files or folder to process")
            return

        # Update UI state
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.progress_label.config(text="Starting processing...")

        # Start processing in background thread
        self.processing_thread = threading.Thread(target=self._process_files, daemon=True)
        self.processing_thread.start()

        self.update_status("Processing started")

    def stop_processing(self):
        """Stop the processing pipeline."""
        if self.orchestrator:
            self.orchestrator.stop_monitoring()

        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress_label.config(text="Processing stopped")

        self.update_status("Processing stopped")

    def _process_files(self):
        """Process files in background thread."""
        try:
            # Create orchestrator with current settings
            from workflow_orchestrator import WorkflowOrchestrator
            from env_config import EnvironmentConfig

            # Create config from GUI settings
            config = EnvironmentConfig(
                openai_api_key=self.openai_api_key.get(),
                openai_model=self.openai_model.get(),
                daily_cost_limit=self.daily_cost_limit.get(),
                enable_ai_classification=self.enable_ai_classification.get(),
                enable_content_enhancement=self.enable_content_enhancement.get(),
                enable_security_filtering=self.enable_security_filtering.get(),
                security_level=self.security_level.get(),
                input_folder=self.input_folder.get(),
                filtered_folder=self.filtered_folder.get(),
                output_folder=self.output_folder.get(),
                output_format=self.output_format.get(),
                parallel_processing=self.parallel_processing.get(),
                max_workers=self.max_workers.get(),
                auto_move_files=self.auto_move_files.get()
            )

            self.orchestrator = WorkflowOrchestrator(config)

            # Process files
            self.root.after(0, lambda: self.log_message("Starting file processing..."))

            summary = self.orchestrator.process_input_folder()

            # Update progress
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: self.progress_label.config(text="Processing complete"))

            # Show results
            result_msg = f"Processing complete!\nFiles processed: {summary['files_processed']}\nFiles failed: {summary['files_failed']}\nTotal cost: ${summary['total_cost']:.4f}"

            self.root.after(0, lambda: self.log_message(result_msg))
            self.root.after(0, lambda: messagebox.showinfo("Complete", result_msg))

        except Exception as e:
            error_msg = f"Processing error: {str(e)}"
            self.root.after(0, lambda: self.log_message(error_msg))
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))

        finally:
            # Reset UI state
            self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))

    def show_status(self):
        """Show detailed pipeline status."""
        if self.orchestrator:
            status = self.orchestrator.get_workflow_status()

            status_window = tk.Toplevel(self.root)
            status_window.title("Pipeline Status")
            status_window.geometry("600x500")

            status_text = scrolledtext.ScrolledText(status_window, width=70, height=30)
            status_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            status_text.insert(tk.END, json.dumps(status, indent=2, default=str))
            status_text.config(state=tk.DISABLED)
        else:
            messagebox.showinfo("Status", "No active processing session")

    def refresh_folder_status(self):
        """Refresh folder status display."""
        self.folder_status_text.delete(1.0, tk.END)

        folders = {
            "Input": self.input_folder.get(),
            "Filtered": self.filtered_folder.get(),
            "Output": self.output_folder.get()
        }

        for name, folder_path in folders.items():
            path = Path(folder_path)
            if path.exists():
                file_count = len(list(path.glob('*')))
                self.folder_status_text.insert(tk.END, f"{name}: {file_count} files\n")
            else:
                self.folder_status_text.insert(tk.END, f"{name}: Folder not found\n")

        self.update_status("Folder status refreshed")

    def refresh_stats(self):
        """Refresh statistics display with real data."""
        self.stats_text.delete(1.0, tk.END)

        try:
            # Get statistics from various sources
            stats_report = f"""
📊 PIPELINE STATISTICS REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📁 File Processing:
   Total Files Processed: {getattr(self.orchestrator, 'total_files_processed', 0)}
   Successful: {getattr(self.orchestrator, 'successful_files', 0)}
   Failed: {getattr(self.orchestrator, 'failed_files', 0)}

🎭 Personality Usage:
   Active Template: {self.personality_template.get()}
   Strength Setting: {self.personality_strength.get():.1f}
   Custom Personalities: {len(self.custom_personality_manager.list_personalities()) if hasattr(self, 'custom_personality_manager') else 0}

🤖 AI Integration:
   Model: {self.openai_model.get()}
   Classification Enabled: {self.enable_ai_classification.get()}
   Enhancement Enabled: {self.enable_content_enhancement.get()}
   Daily Cost Limit: ${self.daily_cost_limit.get():.2f}

🛡️ Security:
   Security Level: {self.security_level.get()}
   Filtering Enabled: {self.enable_security_filtering.get()}

⚙️ Processing Settings:
   Output Format: {self.output_format.get()}
   Parallel Workers: {self.parallel_workers.get()}
   Batch Size: {self.batch_size.get()}

📂 Folder Status:
   Input: {self.input_folder.get()}
   Filtered: {self.filtered_folder.get()}
   Output: {self.output_folder.get()}

⏱️ Performance:
   Average Processing Time: {getattr(self.orchestrator, 'avg_processing_time', 0):.2f}s per file
   Total Processing Time: {getattr(self.orchestrator, 'total_processing_time', 0):.1f}s
   Throughput: {getattr(self.orchestrator, 'throughput', 0):.1f} files/minute
            """

            self.stats_text.insert(tk.END, stats_report.strip())
            self.log_message("Statistics refreshed")

        except Exception as e:
            error_msg = f"Error generating statistics: {e}\n\nBasic Statistics:\n"
            error_msg += f"Current Settings: {self.output_format.get()} format, {self.personality_template.get()} personality"
            self.stats_text.insert(tk.END, error_msg)
            self.log_message(f"Stats refresh error: {e}")

    def refresh_logs(self):
        """Refresh logs display with real log data."""
        self.log_viewer.delete(1.0, tk.END)

        try:
            # Get recent log entries
            log_entries = []

            # Add orchestrator logs if available
            if hasattr(self.orchestrator, 'get_recent_logs'):
                log_entries.extend(self.orchestrator.get_recent_logs())

            # Add GUI logs
            if hasattr(self, 'log_entries'):
                log_entries.extend(self.log_entries[-50:])  # Last 50 entries

            if log_entries:
                for entry in log_entries[-100:]:  # Show last 100 entries
                    if isinstance(entry, dict):
                        timestamp = entry.get('timestamp', 'N/A')
                        level = entry.get('level', 'INFO')
                        message = entry.get('message', str(entry))
                        self.log_viewer.insert(tk.END, f"[{timestamp}] {level}: {message}\n")
                    else:
                        self.log_viewer.insert(tk.END, f"{entry}\n")
            else:
                self.log_viewer.insert(tk.END, "No log entries available.\n")
                self.log_viewer.insert(tk.END, "Logs will appear here as the pipeline processes files.\n")

            # Scroll to bottom
            self.log_viewer.see(tk.END)
            self.log_message("Logs refreshed")

        except Exception as e:
            error_msg = f"Error refreshing logs: {e}\n"
            error_msg += "Log system is active and will display processing information.\n"
            self.log_viewer.insert(tk.END, error_msg)
            self.log_message(f"Log refresh error: {e}")

    def clear_logs(self):
        """Clear logs display."""
        self.log_viewer.delete(1.0, tk.END)
        self.update_status("Logs cleared")

    def save_config(self):
        """Save current configuration."""
        config_file = filedialog.asksaveasfilename(
            title="Save Configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if config_file:
            config_data = {
                "openai_api_key": self.openai_api_key.get(),
                "openai_model": self.openai_model.get(),
                "daily_cost_limit": self.daily_cost_limit.get(),
                "enable_ai_classification": self.enable_ai_classification.get(),
                "enable_content_enhancement": self.enable_content_enhancement.get(),
                "enable_personality_modifier": self.enable_personality_modifier.get(),
                "enable_security_filtering": self.enable_security_filtering.get(),
                "security_level": self.security_level.get(),
                "input_folder": self.input_folder.get(),
                "filtered_folder": self.filtered_folder.get(),
                "output_folder": self.output_folder.get(),
                "output_format": self.output_format.get(),
                "parallel_processing": self.parallel_processing.get(),
                "max_workers": self.max_workers.get(),
                "auto_move_files": self.auto_move_files.get(),
                "personality_template": self.personality_template.get(),
                "custom_personality": self.custom_personality_text.get(1.0, tk.END).strip(),
                "personality_strength": self.personality_strength.get()
            }

            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)

            messagebox.showinfo("Success", f"Configuration saved to {config_file}")
            self.update_status(f"Configuration saved: {config_file}")

    def load_config(self):
        """Load configuration from file."""
        config_file = filedialog.askopenfilename(
            title="Load Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if config_file:
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)

                # Load values into GUI
                self.openai_api_key.set(config_data.get("openai_api_key", ""))
                self.openai_model.set(config_data.get("openai_model", "gpt-4o"))
                self.daily_cost_limit.set(config_data.get("daily_cost_limit", 10.0))
                self.enable_ai_classification.set(config_data.get("enable_ai_classification", True))
                self.enable_content_enhancement.set(config_data.get("enable_content_enhancement", True))
                self.enable_personality_modifier.set(config_data.get("enable_personality_modifier", False))
                self.enable_security_filtering.set(config_data.get("enable_security_filtering", True))
                self.security_level.set(config_data.get("security_level", "balanced"))
                self.input_folder.set(config_data.get("input_folder", "input"))
                self.filtered_folder.set(config_data.get("filtered_folder", "filtered"))
                self.output_folder.set(config_data.get("output_folder", "output"))
                self.output_format.set(config_data.get("output_format", "qwen"))
                self.parallel_processing.set(config_data.get("parallel_processing", True))
                self.max_workers.set(config_data.get("max_workers", 4))
                self.auto_move_files.set(config_data.get("auto_move_files", True))
                self.personality_template.set(config_data.get("personality_template", "neutral"))
                self.personality_strength.set(config_data.get("personality_strength", 0.7))

                # Load custom personality
                custom_personality = config_data.get("custom_personality", "")
                self.custom_personality_text.delete(1.0, tk.END)
                self.custom_personality_text.insert(1.0, custom_personality)

                messagebox.showinfo("Success", f"Configuration loaded from {config_file}")
                self.update_status(f"Configuration loaded: {config_file}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to load configuration: {e}")

    def reset_config(self):
        """Reset configuration to defaults."""
        if messagebox.askyesno("Confirm", "Reset all settings to defaults?"):
            # Reset to default values
            self.openai_api_key.set("")
            self.openai_model.set("gpt-4o")
            self.daily_cost_limit.set(10.0)
            self.enable_ai_classification.set(True)
            self.enable_content_enhancement.set(True)
            self.enable_personality_modifier.set(False)
            self.enable_security_filtering.set(True)
            self.security_level.set("balanced")
            self.input_folder.set("input")
            self.filtered_folder.set("filtered")
            self.output_folder.set("output")
            self.output_format.set("qwen")
            self.parallel_processing.set(True)
            self.max_workers.set(4)
            self.auto_move_files.set(True)
            self.personality_template.set("neutral")
            self.personality_strength.set(0.7)
            self.custom_personality_text.delete(1.0, tk.END)

            self.update_status("Configuration reset to defaults")

    def run(self):
        """Start the GUI application."""
        self.root.mainloop()


def main():
    """Main entry point for the GUI."""
    try:
        app = PipelineGUI()
        app.run()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start GUI: {e}")


if __name__ == "__main__":
    main()
