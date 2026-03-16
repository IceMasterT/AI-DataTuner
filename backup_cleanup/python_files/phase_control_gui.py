#!/usr/bin/env python3
"""
Phase Control Dashboard GUI
Red Light/Green Light control system for the LLM data preparation pipeline.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import json
from datetime import datetime
from pathlib import Path

from phase_controlled_pipeline import get_pipeline, PhaseStatus


class PhaseControlDashboard:
    """Main dashboard for phase-controlled pipeline."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("LLM Data Pipeline - Phase Control Dashboard")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # Get pipeline instance
        self.pipeline = get_pipeline()
        
        # GUI state
        self.processing_thread = None
        self.status_update_job = None
        
        # Create GUI
        self.create_widgets()
        self.update_phase_displays()
        
        # Start status updates
        self.start_status_updates()
    
    def create_widgets(self):
        """Create all GUI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(main_frame, text="LLM Data Pipeline - Phase Control Dashboard", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Create phase control panel
        self.create_phase_control_panel(main_frame)
        
        # Create master controls
        self.create_master_controls(main_frame)
        
        # Create status and logs panel
        self.create_status_panel(main_frame)
    
    def create_phase_control_panel(self, parent):
        """Create the phase control panel with red/green lights."""
        control_frame = ttk.LabelFrame(parent, text="Phase Control - Red Light/Green Light System", padding=15)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Phase controls container
        phases_frame = ttk.Frame(control_frame)
        phases_frame.pack(fill=tk.X)
        
        self.phase_controls = {}
        
        # Create controls for each phase
        for i, (phase_name, phase_config) in enumerate(self.pipeline.phases.items()):
            phase_frame = ttk.Frame(phases_frame)
            phase_frame.grid(row=i//2, column=i%2, sticky="ew", padx=10, pady=5)
            
            # Configure grid weights
            phases_frame.grid_columnconfigure(0, weight=1)
            phases_frame.grid_columnconfigure(1, weight=1)
            
            # Phase info frame
            info_frame = ttk.Frame(phase_frame)
            info_frame.pack(fill=tk.X)
            
            # Phase title
            title_label = ttk.Label(info_frame, text=phase_config.name, 
                                   font=("Arial", 12, "bold"))
            title_label.pack(anchor=tk.W)
            
            # Phase description
            desc_label = ttk.Label(info_frame, text=phase_config.description, 
                                  font=("Arial", 9), foreground="gray")
            desc_label.pack(anchor=tk.W)
            
            # Control frame
            control_inner_frame = ttk.Frame(phase_frame)
            control_inner_frame.pack(fill=tk.X, pady=(5, 0))
            
            # Status light (large colored circle)
            status_frame = ttk.Frame(control_inner_frame)
            status_frame.pack(side=tk.LEFT)
            
            status_canvas = tk.Canvas(status_frame, width=30, height=30, highlightthickness=0)
            status_canvas.pack(side=tk.LEFT, padx=(0, 10))
            
            # Toggle button
            toggle_button = ttk.Button(control_inner_frame, text="Toggle", 
                                      command=lambda pn=phase_name: self.toggle_phase(pn))
            toggle_button.pack(side=tk.LEFT, padx=(0, 10))
            
            # Settings button
            settings_button = ttk.Button(control_inner_frame, text="⚙️ Settings", 
                                        command=lambda pn=phase_name: self.open_phase_settings(pn))
            settings_button.pack(side=tk.LEFT)
            
            # Status text
            status_label = ttk.Label(control_inner_frame, text="Ready", font=("Arial", 9))
            status_label.pack(side=tk.RIGHT)
            
            # Store references
            self.phase_controls[phase_name] = {
                'canvas': status_canvas,
                'toggle_button': toggle_button,
                'settings_button': settings_button,
                'status_label': status_label,
                'frame': phase_frame
            }
    
    def create_master_controls(self, parent):
        """Create master pipeline controls."""
        master_frame = ttk.LabelFrame(parent, text="Master Pipeline Controls", padding=15)
        master_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Control buttons
        button_frame = ttk.Frame(master_frame)
        button_frame.pack(fill=tk.X)
        
        # Start button (large and prominent)
        self.start_button = ttk.Button(button_frame, text="🚀 START PIPELINE", 
                                      command=self.start_pipeline, 
                                      style="Accent.TButton")
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Control buttons
        self.pause_button = ttk.Button(button_frame, text="⏸️ Pause", 
                                      command=self.pause_pipeline, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.resume_button = ttk.Button(button_frame, text="▶️ Resume", 
                                       command=self.resume_pipeline, state=tk.DISABLED)
        self.resume_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.abort_button = ttk.Button(button_frame, text="⏹️ Abort", 
                                      command=self.abort_pipeline, state=tk.DISABLED)
        self.abort_button.pack(side=tk.LEFT, padx=(0, 20))
        
        # Quick actions
        ttk.Button(button_frame, text="🔄 Refresh Status", 
                  command=self.update_phase_displays).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(button_frame, text="💾 Save Config", 
                  command=self.save_configuration).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(button_frame, text="📊 View Results", 
                  command=self.view_results).pack(side=tk.LEFT)
        
        # Pipeline info
        info_frame = ttk.Frame(master_frame)
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.pipeline_info_label = ttk.Label(info_frame, text="Ready to start pipeline", 
                                            font=("Arial", 10))
        self.pipeline_info_label.pack(anchor=tk.W)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(info_frame, variable=self.progress_var, 
                                           maximum=100, length=400)
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))
    
    def create_status_panel(self, parent):
        """Create status and logs panel."""
        status_frame = ttk.LabelFrame(parent, text="Pipeline Status & Logs", padding=10)
        status_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for different views
        notebook = ttk.Notebook(status_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Real-time logs tab
        logs_frame = ttk.Frame(notebook)
        notebook.add(logs_frame, text="📋 Real-time Logs")
        
        self.logs_text = scrolledtext.ScrolledText(logs_frame, height=15, width=80)
        self.logs_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Phase results tab
        results_frame = ttk.Frame(notebook)
        notebook.add(results_frame, text="📊 Phase Results")
        
        self.results_text = scrolledtext.ScrolledText(results_frame, height=15, width=80)
        self.results_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # System status tab
        system_frame = ttk.Frame(notebook)
        notebook.add(system_frame, text="🖥️ System Status")
        
        self.system_text = scrolledtext.ScrolledText(system_frame, height=15, width=80)
        self.system_text.pack(fill=tk.BOTH, expand=True, pady=5)
    
    def update_phase_displays(self):
        """Update all phase status displays."""
        for phase_name, controls in self.phase_controls.items():
            phase_config = self.pipeline.phases[phase_name]
            status = phase_config.status
            
            # Update status light color
            canvas = controls['canvas']
            canvas.delete("all")
            
            color_map = {
                PhaseStatus.DISABLED: "#ff4444",    # Red
                PhaseStatus.ENABLED: "#44ff44",     # Green
                PhaseStatus.RUNNING: "#ffff44",     # Yellow
                PhaseStatus.COMPLETE: "#4444ff",    # Blue
                PhaseStatus.ERROR: "#ff8844"        # Orange
            }
            
            color = color_map.get(status, "#cccccc")
            canvas.create_oval(5, 5, 25, 25, fill=color, outline="black", width=2)
            
            # Update status text
            status_text_map = {
                PhaseStatus.DISABLED: "DISABLED",
                PhaseStatus.ENABLED: "READY",
                PhaseStatus.RUNNING: "RUNNING",
                PhaseStatus.COMPLETE: "COMPLETE",
                PhaseStatus.ERROR: "ERROR"
            }
            
            controls['status_label'].config(text=status_text_map.get(status, "UNKNOWN"))
            
            # Update button states
            if self.pipeline.is_running:
                controls['toggle_button'].config(state=tk.DISABLED)
                controls['settings_button'].config(state=tk.DISABLED)
            else:
                controls['toggle_button'].config(state=tk.NORMAL)
                controls['settings_button'].config(state=tk.NORMAL)
    
    def toggle_phase(self, phase_name: str):
        """Toggle phase between enabled/disabled."""
        new_status = self.pipeline.toggle_phase(phase_name)
        self.update_phase_displays()
        
        status_text = "enabled" if new_status == PhaseStatus.ENABLED else "disabled"
        self.log_message(f"Phase '{self.pipeline.phases[phase_name].name}' {status_text}")
    
    def open_phase_settings(self, phase_name: str):
        """Open settings dialog for a phase."""
        phase_config = self.pipeline.phases[phase_name]
        
        settings_window = tk.Toplevel(self.root)
        settings_window.title(f"Settings - {phase_config.name}")
        settings_window.geometry("600x500")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Settings content
        ttk.Label(settings_window, text=f"Settings for {phase_config.name}", 
                 font=("Arial", 14, "bold")).pack(pady=10)
        
        # Settings editor
        settings_frame = ttk.LabelFrame(settings_window, text="Configuration", padding=10)
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        settings_text = scrolledtext.ScrolledText(settings_frame, height=20, width=70)
        settings_text.pack(fill=tk.BOTH, expand=True)
        
        # Load current settings
        settings_json = json.dumps(phase_config.settings, indent=2)
        settings_text.insert(1.0, settings_json)
        
        # Buttons
        button_frame = ttk.Frame(settings_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def save_settings():
            try:
                new_settings = json.loads(settings_text.get(1.0, tk.END))
                self.pipeline.update_phase_settings(phase_name, new_settings)
                messagebox.showinfo("Success", "Settings saved successfully!")
                settings_window.destroy()
            except json.JSONDecodeError as e:
                messagebox.showerror("Error", f"Invalid JSON: {e}")
        
        ttk.Button(button_frame, text="💾 Save", command=save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Cancel", 
                  command=settings_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def start_pipeline(self):
        """Start the pipeline execution."""
        enabled_phases = self.pipeline.get_enabled_phases()
        
        if not enabled_phases:
            messagebox.showwarning("Warning", "No phases are enabled! Please enable at least one phase.")
            return
        
        # Confirm start
        phase_names = [self.pipeline.phases[name].name for name in enabled_phases]
        message = f"Start pipeline with {len(enabled_phases)} enabled phases?\n\n" + "\n".join(f"• {name}" for name in phase_names)
        
        if not messagebox.askyesno("Confirm Start", message):
            return
        
        # Update UI state
        self.start_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        self.abort_button.config(state=tk.NORMAL)
        
        self.progress_var.set(0)
        self.pipeline_info_label.config(text=f"Starting pipeline with {len(enabled_phases)} phases...")
        
        # Start processing in background
        self.processing_thread = threading.Thread(target=self._run_pipeline, daemon=True)
        self.processing_thread.start()
        
        self.log_message(f"Pipeline started with phases: {', '.join(enabled_phases)}")
    
    def _run_pipeline(self):
        """Run pipeline in background thread."""
        try:
            results = self.pipeline.start_pipeline()
            
            # Update UI on completion
            self.root.after(0, lambda: self._on_pipeline_complete(results))
            
        except Exception as e:
            self.root.after(0, lambda: self._on_pipeline_error(str(e)))
    
    def _on_pipeline_complete(self, results):
        """Handle pipeline completion."""
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.resume_button.config(state=tk.DISABLED)
        self.abort_button.config(state=tk.DISABLED)
        
        self.progress_var.set(100)
        self.pipeline_info_label.config(text="Pipeline completed successfully!")
        
        # Show results
        self.update_results_display(results)
        self.log_message("Pipeline completed successfully!")
        
        messagebox.showinfo("Complete", "Pipeline execution completed!")
    
    def _on_pipeline_error(self, error_message):
        """Handle pipeline error."""
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.resume_button.config(state=tk.DISABLED)
        self.abort_button.config(state=tk.DISABLED)
        
        self.pipeline_info_label.config(text=f"Pipeline error: {error_message}")
        self.log_message(f"Pipeline error: {error_message}")
        
        messagebox.showerror("Error", f"Pipeline failed: {error_message}")
    
    def pause_pipeline(self):
        """Pause pipeline execution."""
        self.pipeline.pause_pipeline()
        self.pause_button.config(state=tk.DISABLED)
        self.resume_button.config(state=tk.NORMAL)
        self.log_message("Pipeline paused")
    
    def resume_pipeline(self):
        """Resume pipeline execution."""
        self.pipeline.resume_pipeline()
        self.pause_button.config(state=tk.NORMAL)
        self.resume_button.config(state=tk.DISABLED)
        self.log_message("Pipeline resumed")
    
    def abort_pipeline(self):
        """Abort pipeline execution."""
        if messagebox.askyesno("Confirm Abort", "Are you sure you want to abort the pipeline?"):
            self.pipeline.abort_pipeline()
            self.log_message("Pipeline aborted by user")
    
    def save_configuration(self):
        """Save current configuration."""
        self.pipeline.save_configuration()
        messagebox.showinfo("Success", "Configuration saved successfully!")
        self.log_message("Configuration saved")
    
    def view_results(self):
        """View detailed results."""
        results_window = tk.Toplevel(self.root)
        results_window.title("Pipeline Results")
        results_window.geometry("800x600")
        
        results_text = scrolledtext.ScrolledText(results_window, width=90, height=35)
        results_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Display current results
        if self.pipeline.results:
            results_json = json.dumps(
                {name: result.__dict__ for name, result in self.pipeline.results.items()}, 
                indent=2, default=str
            )
            results_text.insert(1.0, results_json)
        else:
            results_text.insert(1.0, "No results available. Run the pipeline first.")
    
    def update_results_display(self, results):
        """Update the results display."""
        self.results_text.delete(1.0, tk.END)
        
        for phase_name, result in results.items():
            phase_info = f"""
Phase: {result.phase_name}
Status: {result.status.value}
Files Processed: {result.files_processed}
Files Failed: {result.files_failed}
Duration: {result.end_time - result.start_time if result.end_time else 'N/A'}
Output Files: {len(result.output_files)}
Errors: {len(result.errors)}

"""
            self.results_text.insert(tk.END, phase_info)
            
            if result.errors:
                self.results_text.insert(tk.END, "Errors:\n")
                for error in result.errors:
                    self.results_text.insert(tk.END, f"  • {error}\n")
                self.results_text.insert(tk.END, "\n")
    
    def start_status_updates(self):
        """Start periodic status updates."""
        self.update_status()
        self.status_update_job = self.root.after(1000, self.start_status_updates)
    
    def update_status(self):
        """Update status displays."""
        self.update_phase_displays()
        
        # Update system status
        status = self.pipeline.get_pipeline_status()
        self.system_text.delete(1.0, tk.END)
        
        status_info = f"""Pipeline Status: {'Running' if status['is_running'] else 'Idle'}
Current Phase: {status.get('current_phase', 'None')}
Paused: {status.get('pause_requested', False)}
Abort Requested: {status.get('abort_requested', False)}

Phase Summary:
"""
        
        for phase_name, phase_info in status['phases'].items():
            status_info += f"  {phase_info['status'].upper()}: {phase_info['description']}\n"
        
        self.system_text.insert(1.0, status_info)
    
    def log_message(self, message):
        """Add message to logs."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        
        self.logs_text.insert(tk.END, log_entry)
        self.logs_text.see(tk.END)
    
    def run(self):
        """Start the GUI application."""
        try:
            self.root.mainloop()
        finally:
            if self.status_update_job:
                self.root.after_cancel(self.status_update_job)


def main():
    """Main entry point."""
    app = PhaseControlDashboard()
    app.run()


if __name__ == "__main__":
    main()
