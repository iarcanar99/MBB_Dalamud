# model.py - Professional Dark-Themed Model Settings UI
import tkinter as tk
from tkinter import ttk, messagebox, font
import logging
from appearance import appearance_manager
import hashlib
import json
import os


class ModelSettings:
    def __init__(self, parent, settings, apply_settings_callback, main_app=None):
        self.parent = parent
        self.settings = settings
        self.apply_settings_callback = apply_settings_callback
        self.main_app = main_app

        # UI State
        self.model_window = None
        # Passcode window removed
        self.window_created = False
        self.is_adult_mode_unlocked = False

        # Dark theme colors
        self.colors = {
            "bg_primary": "#1a1a1a",
            "bg_secondary": "#2d2d2d",
            "bg_tertiary": "#3d3d3d",
            "accent": "#4a9eff",
            "accent_hover": "#6bb6ff",
            "text_primary": "#ffffff",
            "text_secondary": "#b8b8b8",
            "text_muted": "#888888",
            "border": "#404040",
            "success": "#4caf50",
            "warning": "#ff9800",
            "danger": "#f44336",
            "gradient_start": "#2d2d2d",
            "gradient_end": "#1a1a1a",
        }

        # Role modes configuration - no passcode needed within model UI
        self.role_modes = {
            "rpg_general": {
                "display_name": "🎮 General RPG Translation",
                "description": "Standard translation for RPG games and general content",
            },
            "adult_enhanced": {
                "display_name": "🔥 Adult Enhanced Mode",
                "description": "Enhanced translation for adult content with explicit terminology",
            },
        }

        # Passcode management removed - handled at model UI entry level

    # Passcode functions removed - authentication handled at entry level

    # Passcode window functionality removed - authentication handled at model UI entry

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        # For Windows/Linux, delta is a multiple of 120
        # For macOS, it's a smaller number
        # We normalize it to scroll by a consistent amount
        if event.num == 5 or event.delta < 0:
            scroll_val = 1
        else:
            scroll_val = -1

        self.canvas.yview_scroll(scroll_val, "units")

    def create_modern_button(self, parent, text, command, color=None, width=None):
        """Create a modern styled button"""
        if color is None:
            color = self.colors["accent"]

        btn = tk.Button(
            parent,
            text=text,
            font=("Segoe UI", 10, "bold"),
            bg=color,
            fg=self.colors["text_primary"],
            bd=0,
            relief="flat",
            padx=20,
            pady=8,
            command=command,
            cursor="hand2",
        )

        if width:
            btn.configure(width=width)

        # Hover effects
        def on_enter(e):
            if color == self.colors["accent"]:
                btn.configure(bg=self.colors["accent_hover"])
            else:
                # Lighten the color for hover effect
                btn.configure(bg=self.lighten_color(color))

        def on_leave(e):
            btn.configure(bg=color)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

        return btn

    def lighten_color(self, color):
        """Lighten a hex color for hover effects"""
        # Simple color lightening
        if color == self.colors["warning"]:
            return "#ffb74d"
        elif color == self.colors["success"]:
            return "#66bb6a"
        elif color == self.colors["danger"]:
            return "#f66"
        return color

    def create_model_window(self):
        """Create the main model settings window with professional design"""
        if self.model_window is None or not self.model_window.winfo_exists():
            self.model_window = tk.Toplevel(self.parent)
            self.model_window.title("🚀 AI Model Configuration")
            self.model_window.geometry("650x750")
            self.model_window.configure(bg=self.colors["bg_primary"])
            self.model_window.overrideredirect(True)
            # Removed transient to allow independent window dragging
            # self.model_window.transient(self.parent)

            self.create_main_ui()
            self.window_created = True
            self.model_window.withdraw()
            self.load_current_settings()

    def create_main_ui(self):
        """Create the main UI components"""
        # Main container with border
        main_container = tk.Frame(
            self.model_window, bg=self.colors["bg_secondary"], relief="flat", bd=0
        )
        main_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Header section
        header_frame = self.create_header(main_container)

        # Content area with scrollbar
        self.create_content_area(main_container)

        # Footer with action buttons
        self.create_footer(main_container)

        # Setup window dragging on header (after header is created)
        if header_frame:
            self.setup_window_movement(self.model_window, header_frame)
            # Also bind to child widgets for better drag coverage
            self.bind_drag_to_children(self.model_window, header_frame)
        else:
            logging.error("Header frame is None - drag functionality disabled")

    def create_header(self, parent):
        """Create header section"""
        header_frame = tk.Frame(parent, bg=self.colors["bg_tertiary"], height=70)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        # Add cursor change for draggable area
        header_frame.configure(cursor="hand2")

        # Close button
        close_btn = tk.Button(
            header_frame,
            text="✕",
            font=("Segoe UI", 14, "bold"),
            bg=self.colors["bg_tertiary"],
            fg=self.colors["text_secondary"],
            bd=0,
            relief="flat",
            width=3,
            command=self.close,
        )
        close_btn.pack(side=tk.RIGHT, padx=15, pady=15)

        # Title and subtitle
        title_frame = tk.Frame(header_frame, bg=self.colors["bg_tertiary"])
        title_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=10)

        title_label = tk.Label(
            title_frame,
            text="🚀 AI Model Configuration",
            font=("Segoe UI", 18, "bold"),
            fg=self.colors["text_primary"],
            bg=self.colors["bg_tertiary"],
            anchor="w",
        )
        title_label.pack(anchor="w")

        subtitle_label = tk.Label(
            title_frame,
            text="Configure Gemini AI parameters and translation modes",
            font=("Segoe UI", 10),
            fg=self.colors["text_secondary"],
            bg=self.colors["bg_tertiary"],
            anchor="w",
        )
        subtitle_label.pack(anchor="w")

        return header_frame

    def create_content_area(self, parent):
        """Create scrollable content area"""
        # Create a container frame for the canvas and scrollbar
        canvas_container = tk.Frame(parent, bg=self.colors["bg_secondary"])
        canvas_container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            canvas_container, bg=self.colors["bg_secondary"], highlightthickness=0, bd=0
        )

        scrollbar = ttk.Scrollbar(
            canvas_container, orient="vertical", command=self.canvas.yview
        )

        self.scrollable_frame = tk.Frame(self.canvas, bg=self.colors["bg_secondary"])

        # This is the crucial part: update the scrollregion whenever the frame's size changes
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        # Create a window in the canvas that holds the scrollable_frame
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw"
        )

        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Pack the widgets onto the screen
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind the mouse wheel event to the canvas and the frame inside it
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.scrollable_frame.bind_all("<MouseWheel>", self._on_mousewheel)

        # Ensure the width of the scrollable frame matches the canvas width
        def on_canvas_configure(event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)

        self.canvas.bind("<Configure>", on_canvas_configure)

        # Add content sections to the scrollable_frame
        self.create_role_mode_section()
        self.create_model_selection_section()
        self.create_parameters_section()

    def create_role_mode_section(self):
        """Create role mode selection section"""
        section_frame = self.create_section_frame("🎭 Translation Mode")

        # Add section description
        desc_frame = tk.Frame(section_frame, bg=self.colors["bg_secondary"])
        desc_frame.pack(fill=tk.X, pady=(0, 15))

        desc_label = tk.Label(
            desc_frame,
            text="⚡ Real-time mode switching • 🔒 Secure adult content protection • 🎯 Optimized prompts",
            font=("Segoe UI", 9),
            fg=self.colors["text_muted"],
            bg=self.colors["bg_secondary"],
        )
        desc_label.pack(anchor="w")

        # Role mode selection
        mode_frame = tk.Frame(section_frame, bg=self.colors["bg_secondary"])
        mode_frame.pack(fill=tk.X, pady=(0, 10))

        self.role_var = tk.StringVar()

        for mode_key, mode_info in self.role_modes.items():
            self.create_role_option(mode_frame, mode_key, mode_info)

    def create_role_option(self, parent, mode_key, mode_info):
        """Create a role mode option"""
        option_frame = tk.Frame(
            parent, bg=self.colors["bg_tertiary"], relief="flat", bd=1
        )
        option_frame.pack(fill=tk.X, pady=2)

        # Radio button with custom styling
        radio_frame = tk.Frame(option_frame, bg=self.colors["bg_tertiary"])
        radio_frame.pack(side=tk.LEFT, padx=15, pady=12)

        radio = tk.Radiobutton(
            radio_frame,
            text="",
            variable=self.role_var,
            value=mode_key,
            bg=self.colors["bg_tertiary"],
            fg=self.colors["accent"],
            selectcolor=self.colors["bg_tertiary"],
            activebackground=self.colors["bg_tertiary"],
            bd=0,
            command=lambda: self.on_role_change(mode_key),
        )
        radio.pack()

        # Content
        content_frame = tk.Frame(option_frame, bg=self.colors["bg_tertiary"])
        content_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 15), pady=8)

        # Title - no lock icons needed within model UI
        title_text = mode_info["display_name"]
        # User already authenticated to access model UI, so all roles available

        title_label = tk.Label(
            content_frame,
            text=title_text,
            font=("Segoe UI", 12, "bold"),
            fg=self.colors["text_primary"],
            bg=self.colors["bg_tertiary"],
            anchor="w",
        )
        title_label.pack(anchor="w")

        # Description
        desc_label = tk.Label(
            content_frame,
            text=mode_info["description"],
            font=("Segoe UI", 9),
            fg=self.colors["text_secondary"],
            bg=self.colors["bg_tertiary"],
            anchor="w",
        )
        desc_label.pack(anchor="w")

    def on_role_change(self, mode_key):
        """Handle role mode change - simplified without confirmation popup"""
        mode_info = self.role_modes[mode_key]

        # Allow role selection without popup - user will apply via Apply button
        # Just log the change for now
        logging.info(f"Role mode selected: {mode_key}")

    def create_model_selection_section(self):
        """Create model selection section"""
        section_frame = self.create_section_frame("🤖 AI Model Selection")

        # Model dropdown with modern styling
        model_frame = tk.Frame(section_frame, bg=self.colors["bg_secondary"])
        model_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            model_frame,
            text="Selected Model:",
            font=("Segoe UI", 11, "bold"),
            fg=self.colors["text_primary"],
            bg=self.colors["bg_secondary"],
        ).pack(anchor="w", pady=(0, 5))

        # Custom styled combobox
        self.model_var = tk.StringVar(value="gemini-2.0-flash")
        model_combo_frame = tk.Frame(
            model_frame, bg=self.colors["bg_tertiary"], relief="flat", bd=1
        )
        model_combo_frame.pack(fill=tk.X)

        self.model_combo = ttk.Combobox(
            model_combo_frame,
            textvariable=self.model_var,
            values=["gemini-2.0-flash"],
            state="readonly",
            font=("Segoe UI", 11),
        )
        self.model_combo.pack(fill=tk.X, padx=10, pady=8)

        # Model info
        info_label = tk.Label(
            model_frame,
            text="🔥 Optimized for fast, high-quality translation with adult content support",
            font=("Segoe UI", 9),
            fg=self.colors["text_muted"],
            bg=self.colors["bg_secondary"],
        )
        info_label.pack(anchor="w", pady=(5, 0))

    def create_parameters_section(self):
        """Create parameters section with modern controls"""
        section_frame = self.create_section_frame("⚙️ Advanced Parameters")

        # Max Tokens with 5-unit precision
        self.create_parameter_control(
            section_frame,
            "Max Tokens",
            "Maximum number of tokens in the response (5-unit increments for professional control)",
            100,
            2000,
            5,
            "gemini_max_tokens",
        )

        # Temperature
        self.create_parameter_control(
            section_frame,
            "Temperature",
            "Controls randomness in responses (0.0 = deterministic, 1.0 = creative)",
            0.0,
            1.0,
            0.05,
            "gemini_temperature",
        )

        # Top P
        self.create_parameter_control(
            section_frame,
            "Top P",
            "Controls diversity via nucleus sampling",
            0.0,
            1.0,
            0.05,
            "gemini_top_p",
        )

    def create_parameter_control(
        self, parent, title, description, min_val, max_val, resolution, attr_name
    ):
        """Create a modern parameter control"""
        param_frame = tk.Frame(parent, bg=self.colors["bg_secondary"])
        param_frame.pack(fill=tk.X, pady=(0, 15))

        # Header
        header_frame = tk.Frame(param_frame, bg=self.colors["bg_secondary"])
        header_frame.pack(fill=tk.X, pady=(0, 5))

        title_label = tk.Label(
            header_frame,
            text=title,
            font=("Segoe UI", 11, "bold"),
            fg=self.colors["text_primary"],
            bg=self.colors["bg_secondary"],
        )
        title_label.pack(side=tk.LEFT)

        # Value display
        value_var = tk.StringVar()
        setattr(self, f"{attr_name}_var", value_var)

        value_label = tk.Label(
            header_frame,
            textvariable=value_var,
            font=("Segoe UI", 10, "bold"),
            fg=self.colors["accent"],
            bg=self.colors["bg_secondary"],
        )
        value_label.pack(side=tk.RIGHT)

        # Description
        desc_label = tk.Label(
            param_frame,
            text=description,
            font=("Segoe UI", 9),
            fg=self.colors["text_secondary"],
            bg=self.colors["bg_secondary"],
            wraplength=500,
            justify=tk.LEFT,
        )
        desc_label.pack(anchor="w", pady=(0, 8))

        # Slider with custom styling
        slider_frame = tk.Frame(param_frame, bg=self.colors["bg_tertiary"])
        slider_frame.pack(fill=tk.X, ipady=8)

        scale = tk.Scale(
            slider_frame,
            from_=min_val,
            to=max_val,
            orient=tk.HORIZONTAL,
            resolution=resolution,
            bg=self.colors["bg_tertiary"],
            fg=self.colors["text_primary"],
            troughcolor=self.colors["bg_primary"],
            activebackground=self.colors["accent"],
            highlightthickness=0,
            bd=0,
            showvalue=False,
            command=lambda v: value_var.set(
                f"{float(v):.2f}" if resolution < 1 else str(int(float(v)))
            ),
        )
        scale.pack(fill=tk.X, padx=15)

        # Add left-click functionality to slider
        def on_slider_click(event):
            # Calculate click position relative to slider
            slider_width = scale.winfo_width()
            click_x = event.x

            # Calculate value based on click position
            if slider_width > 0:
                ratio = click_x / slider_width
                value_range = max_val - min_val
                new_value = min_val + (ratio * value_range)

                # Clamp value to bounds
                new_value = max(min_val, min(max_val, new_value))

                # Round to resolution
                if resolution > 0:
                    new_value = round(new_value / resolution) * resolution

                # Set the new value
                scale.set(new_value)

        scale.bind("<Button-1>", on_slider_click)

        setattr(self, attr_name, scale)

    def create_section_frame(self, title):
        """Create a section frame with title"""
        section_container = tk.Frame(
            self.scrollable_frame, bg=self.colors["bg_secondary"]
        )
        section_container.pack(fill=tk.X, pady=(0, 20))

        # Section title
        title_frame = tk.Frame(section_container, bg=self.colors["bg_secondary"])
        title_frame.pack(fill=tk.X, pady=(0, 10))

        title_label = tk.Label(
            title_frame,
            text=title,
            font=("Segoe UI", 14, "bold"),
            fg=self.colors["text_primary"],
            bg=self.colors["bg_secondary"],
        )
        title_label.pack(side=tk.LEFT, padx=15)

        # Separator line
        sep_frame = tk.Frame(title_frame, bg=self.colors["border"], height=2)
        sep_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 15))

        # Content frame
        content_frame = tk.Frame(section_container, bg=self.colors["bg_secondary"])
        content_frame.pack(fill=tk.X, padx=15)

        return content_frame

    def create_footer(self, parent):
        """Create footer with action buttons"""
        footer_frame = tk.Frame(parent, bg=self.colors["bg_tertiary"], height=70)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        footer_frame.pack_propagate(False)

        # Button container
        btn_container = tk.Frame(footer_frame, bg=self.colors["bg_tertiary"])
        btn_container.pack(expand=True, fill=tk.BOTH)

        # Buttons
        btn_frame = tk.Frame(btn_container, bg=self.colors["bg_tertiary"])
        btn_frame.pack(pady=15)

        # Reset button
        reset_btn = self.create_modern_button(
            btn_frame,
            "🔄 Reset to Defaults",
            self.reset_to_defaults,
            self.colors["warning"],
            12,
        )
        reset_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Apply button
        self.apply_btn = self.create_modern_button(
            btn_frame,
            "✨ Apply Settings",
            self.apply_settings,
            self.colors["success"],
            15,
        )
        self.apply_btn.pack(side=tk.RIGHT, padx=(10, 0))

    def setup_window_movement(self, window, handle_widget):
        """Setup window movement"""

        def start_move(event):
            window.x = event.x
            window.y = event.y

        def stop_move(event):
            window.x = None
            window.y = None

        def do_move(event):
            if hasattr(window, "x") and hasattr(window, "y"):
                deltax = event.x - window.x
                deltay = event.y - window.y
                x = window.winfo_x() + deltax
                y = window.winfo_y() + deltay
                window.geometry(f"+{x}+{y}")

        handle_widget.bind("<Button-1>", start_move)
        handle_widget.bind("<ButtonRelease-1>", stop_move)
        handle_widget.bind("<B1-Motion>", do_move)

    def bind_drag_to_children(self, window, parent_widget):
        """Bind drag functionality to child widgets for better coverage"""

        def start_move(event):
            window.x = event.x_root - window.winfo_x()
            window.y = event.y_root - window.winfo_y()

        def stop_move(event):
            window.x = None
            window.y = None

        def do_move(event):
            if hasattr(window, "x") and hasattr(window, "y"):
                x = event.x_root - window.x
                y = event.y_root - window.y
                window.geometry(f"+{x}+{y}")

        # Bind to all child widgets except buttons
        for child in parent_widget.winfo_children():
            widget_class = child.winfo_class()
            if widget_class not in [
                "Button"
            ]:  # Skip buttons to preserve their click functionality
                try:
                    child.bind("<Button-1>", start_move)
                    child.bind("<ButtonRelease-1>", stop_move)
                    child.bind("<B1-Motion>", do_move)
                    child.configure(cursor="hand2")

                    # Recursively bind to grandchildren
                    self.bind_drag_to_children_recursive(
                        window, child, start_move, stop_move, do_move
                    )
                except:
                    pass  # Some widgets might not support binding

    def bind_drag_to_children_recursive(
        self, window, widget, start_move, stop_move, do_move
    ):
        """Recursively bind drag to nested widgets"""
        try:
            for child in widget.winfo_children():
                widget_class = child.winfo_class()
                if widget_class not in ["Button"]:
                    child.bind("<Button-1>", start_move)
                    child.bind("<ButtonRelease-1>", stop_move)
                    child.bind("<B1-Motion>", do_move)
                    child.configure(cursor="hand2")
                    self.bind_drag_to_children_recursive(
                        window, child, start_move, stop_move, do_move
                    )
        except:
            pass

    def center_window(self, window, width, height):
        """Center window on screen"""
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")

    def show_message(self, message, msg_type="info"):
        """Show temporary message"""
        colors = {
            "success": self.colors["success"],
            "warning": self.colors["warning"],
            "error": self.colors["danger"],
            "info": self.colors["accent"],
        }

        # You could implement a toast notification here
        # For now, using messagebox
        if msg_type == "success":
            messagebox.showinfo("Success", message)
        elif msg_type == "warning":
            messagebox.showwarning("Warning", message)
        elif msg_type == "error":
            messagebox.showerror("Error", message)
        else:
            messagebox.showinfo("Info", message)

    def load_current_settings(self):
        """Load current settings from settings object"""
        current_params = self.settings.get_api_parameters()

        # Set role mode
        role_mode = current_params.get("role_mode", "rpg_general")
        self.role_var.set(role_mode)

        # Set model
        model = current_params.get("model", "gemini-2.0-flash")
        self.model_var.set(model)

        # Set parameters
        self.gemini_max_tokens.set(current_params.get("max_tokens", 500))
        self.gemini_temperature.set(current_params.get("temperature", 0.7))
        self.gemini_top_p.set(current_params.get("top_p", 0.9))

        # Update value displays
        self.gemini_max_tokens_var.set(str(int(current_params.get("max_tokens", 500))))
        self.gemini_temperature_var.set(f"{current_params.get('temperature', 0.7):.2f}")
        self.gemini_top_p_var.set(f"{current_params.get('top_p', 0.9):.2f}")

    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        if messagebox.askyesno(
            "Reset Settings", "Reset all settings to default values?"
        ):
            self.role_var.set("rpg_general")
            self.gemini_max_tokens.set(500)
            self.gemini_temperature.set(0.7)
            self.gemini_top_p.set(0.9)

            # Update displays
            self.gemini_max_tokens_var.set("500")
            self.gemini_temperature_var.set("0.70")
            self.gemini_top_p_var.set("0.90")

    def apply_settings(self):
        """Apply settings with enhanced validation and real-time updates"""
        try:
            # Get current values
            selected_model = self.model_var.get()
            selected_role = self.role_var.get()

            # Get role information for display
            role_info = self.role_modes.get(selected_role)

            # No passcode required within model UI - user already authenticated
            # Role selection is free within the model settings window

            # Create parameters
            api_parameters = {
                "model": selected_model,
                "max_tokens": int(self.gemini_max_tokens.get()),
                "temperature": float(self.gemini_temperature.get()),
                "top_p": float(self.gemini_top_p.get()),
                "role_mode": selected_role,
            }

            # Validate parameters
            self.settings.validate_model_parameters(api_parameters)

            # Apply settings with detailed logging
            logging.info(f"Attempting to apply parameters: {api_parameters}")
            success, error = self.settings.set_api_parameters(**api_parameters)
            if not success:
                logging.error(f"Failed to apply parameters: {error}")
                raise ValueError(error)
            else:
                logging.info(f"Parameters applied successfully: {success}")

            # Save settings
            self.settings.save_settings()

            # Show confirmation
            confirm = messagebox.askyesno(
                "Apply Settings",
                f"Apply new configuration?\n\n"
                f"Model: {selected_model}\n"
                f"Mode: {role_info['display_name'] if role_info else 'Unknown'}\n"
                f"Temperature: {api_parameters['temperature']:.2f}\n"
                f"Top P: {api_parameters['top_p']:.2f}\n\n"
                f"Settings will be applied immediately.",
                icon="question",
            )

            if not confirm:
                return False

            # Update UI feedback
            self.apply_btn.configure(text="✅ Applied!", bg=self.colors["success"])
            self.model_window.after(
                2000,
                lambda: self.apply_btn.configure(
                    text="✨ Apply Settings", bg=self.colors["success"]
                ),
            )

            # Call main app update
            if self.main_app and hasattr(self.main_app, "update_api_settings"):
                try:
                    success = self.main_app.update_api_settings()
                    if success:
                        logging.info(f"Settings applied successfully: {api_parameters}")
                        # Update translator prompt in real-time
                        self.update_translator_prompt(selected_role)
                        return True
                    else:
                        self.show_message(
                            "Settings applied but system update failed", "warning"
                        )
                        return False
                except Exception as e:
                    logging.error(f"Error updating settings: {e}")
                    self.show_message(f"Error applying settings: {e}", "error")
                    return False

            return True

        except Exception as e:
            self.show_message(f"Failed to apply settings: {str(e)}", "error")
            return False

    def update_translator_prompt(self, role_mode):
        """Update translator prompt based on role mode - real-time without restart"""
        try:
            # Get the translator instance
            if hasattr(self.main_app, "translator") and self.main_app.translator:
                if hasattr(self.main_app.translator, "set_role_mode"):
                    self.main_app.translator.set_role_mode(role_mode)
                    logging.info(f"Translator prompt updated for role: {role_mode}")
                else:
                    logging.warning("Translator doesn't support set_role_mode method")
            else:
                logging.warning("No active translator found")
        except Exception as e:
            logging.error(f"Error updating translator prompt: {e}")

    def open(self):
        """Show the model settings window"""
        if not self.window_created:
            self.create_model_window()

        # Center relative to parent
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()

        x = parent_x + parent_width + 20
        y = parent_y

        self.model_window.geometry(f"+{x}+{y}")
        self.model_window.deiconify()
        self.model_window.lift()
        # Removed topmost to allow normal window dragging behavior
        # self.model_window.attributes("-topmost", True)

    def close(self):
        """Hide the model settings window"""
        if self.model_window and self.window_created:
            self.model_window.withdraw()

        # Passcode window functionality removed - no cleanup needed
