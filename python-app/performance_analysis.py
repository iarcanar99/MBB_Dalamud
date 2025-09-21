"""
Performance Analysis for Rainbow Animation vs Blinking Indicator
Analyzes CPU, memory, and rendering performance of both implementations
"""

import tkinter as tk
import time
import psutil
import threading
import gc
from rainbow_progress_bar import RainbowProgressBar
from PIL import Image, ImageTk
import cProfile
import pstats
import io


class PerformanceAnalyzer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Performance Analysis")
        self.root.geometry("600x400")
        self.root.configure(bg="#2c2c2c")
        
        # Performance metrics
        self.metrics = {
            "rainbow": {"cpu": [], "memory": [], "fps": [], "render_time": []},
            "blinking": {"cpu": [], "memory": [], "fps": [], "render_time": []},
        }
        
        # Create UI
        self.setup_ui()
        
        # Process monitoring
        self.process = psutil.Process()
        self.monitoring = False
        
    def setup_ui(self):
        """Setup UI for testing both implementations"""
        # Title
        title = tk.Label(
            self.root,
            text="Performance Analysis: Rainbow vs Blinking",
            fg="white",
            bg="#2c2c2c",
            font=("Segoe UI", 14, "bold")
        )
        title.pack(pady=10)
        
        # Rainbow Progress Bar
        rainbow_frame = tk.LabelFrame(
            self.root,
            text="Rainbow Animation (New)",
            fg="white",
            bg="#2c2c2c",
            font=("Segoe UI", 10)
        )
        rainbow_frame.pack(pady=10, padx=20, fill="x")
        
        self.rainbow_bar = RainbowProgressBar(rainbow_frame, width=400, height=8)
        self.rainbow_bar.pack(pady=10, padx=10)
        
        # Blinking Indicator (Old implementation)
        blinking_frame = tk.LabelFrame(
            self.root,
            text="Blinking Indicator (Old)",
            fg="white",
            bg="#2c2c2c",
            font=("Segoe UI", 10)
        )
        blinking_frame.pack(pady=10, padx=20, fill="x")
        
        self.setup_blinking_indicator(blinking_frame)
        
        # Results display
        self.results_text = tk.Text(
            self.root,
            height=10,
            bg="#1a1a1a",
            fg="white",
            font=("Consolas", 9)
        )
        self.results_text.pack(pady=10, padx=20, fill="both", expand=True)
        
        # Control buttons
        button_frame = tk.Frame(self.root, bg="#2c2c2c")
        button_frame.pack(pady=10)
        
        tk.Button(
            button_frame,
            text="Test Rainbow",
            command=self.test_rainbow,
            bg="#4CAF50",
            fg="white",
            width=15
        ).pack(side="left", padx=5)
        
        tk.Button(
            button_frame,
            text="Test Blinking",
            command=self.test_blinking,
            bg="#2196F3",
            fg="white",
            width=15
        ).pack(side="left", padx=5)
        
        tk.Button(
            button_frame,
            text="Compare Both",
            command=self.compare_performance,
            bg="#FF9800",
            fg="white",
            width=15
        ).pack(side="left", padx=5)
        
    def setup_blinking_indicator(self, parent):
        """Setup old blinking indicator for comparison"""
        # Status frame similar to old implementation
        status_frame = tk.Frame(parent, bg="#2c2c2c")
        status_frame.pack(pady=10, padx=10, fill="x")
        
        self.status_label = tk.Label(
            status_frame,
            text="ready",
            fg="#888",
            bg="#2c2c2c",
            font=("Segoe UI", 9)
        )
        self.status_label.pack(side="left", padx=5)
        
        # Load icons for blinking
        try:
            self.blink_icon = ImageTk.PhotoImage(
                Image.open("assets/red_icon.png").resize((20, 20))
            )
            self.black_icon = ImageTk.PhotoImage(
                Image.open("assets/black_icon.png").resize((20, 20))
            )
        except:
            # Create simple colored squares if icons not found
            red_img = Image.new("RGB", (20, 20), color="#FF0000")
            black_img = Image.new("RGB", (20, 20), color="#000000")
            self.blink_icon = ImageTk.PhotoImage(red_img)
            self.black_icon = ImageTk.PhotoImage(black_img)
        
        self.blink_label = tk.Label(
            status_frame,
            image=self.black_icon,
            bg="#2c2c2c"
        )
        self.blink_label.pack(side="right", padx=5)
        
        self.blinking = False
        self.blink_state = False
        
    def blink(self):
        """Old blinking animation"""
        if self.blinking:
            # Toggle between red and black icons
            if self.blink_state:
                self.blink_label.config(image=self.black_icon)
            else:
                self.blink_label.config(image=self.blink_icon)
            self.blink_state = not self.blink_state
            
            # Schedule next blink (500ms interval as per original)
            self.root.after(500, self.blink)
    
    def monitor_performance(self, duration=10, test_type="rainbow"):
        """Monitor CPU and memory usage during animation"""
        start_time = time.time()
        self.monitoring = True
        
        while self.monitoring and (time.time() - start_time) < duration:
            # CPU usage
            cpu_percent = self.process.cpu_percent(interval=0.1)
            
            # Memory usage
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # Store metrics
            self.metrics[test_type]["cpu"].append(cpu_percent)
            self.metrics[test_type]["memory"].append(memory_mb)
            
            time.sleep(0.1)
    
    def test_rainbow(self):
        """Test rainbow animation performance"""
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "Testing Rainbow Animation...\n")
        self.root.update()
        
        # Clear previous metrics
        self.metrics["rainbow"] = {"cpu": [], "memory": [], "fps": [], "render_time": []}
        
        # Start monitoring in background thread
        monitor_thread = threading.Thread(
            target=self.monitor_performance,
            args=(10, "rainbow")
        )
        monitor_thread.start()
        
        # Start rainbow animation
        self.rainbow_bar.start_animation("Testing performance...")
        
        # Measure FPS and render time
        frame_count = 0
        start_time = time.time()
        
        for _ in range(250):  # 10 seconds at 25 FPS
            frame_start = time.time()
            self.root.update()
            frame_time = time.time() - frame_start
            self.metrics["rainbow"]["render_time"].append(frame_time * 1000)  # Convert to ms
            frame_count += 1
            
            # Wait for next frame (40ms = 25 FPS)
            remaining_time = 0.04 - frame_time
            if remaining_time > 0:
                time.sleep(remaining_time)
        
        elapsed_time = time.time() - start_time
        actual_fps = frame_count / elapsed_time
        self.metrics["rainbow"]["fps"] = actual_fps
        
        # Stop animation
        self.rainbow_bar.stop_animation()
        self.monitoring = False
        monitor_thread.join()
        
        # Display results
        self.display_results("rainbow")
    
    def test_blinking(self):
        """Test blinking indicator performance"""
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "Testing Blinking Indicator...\n")
        self.root.update()
        
        # Clear previous metrics
        self.metrics["blinking"] = {"cpu": [], "memory": [], "fps": [], "render_time": []}
        
        # Start monitoring in background thread
        monitor_thread = threading.Thread(
            target=self.monitor_performance,
            args=(10, "blinking")
        )
        monitor_thread.start()
        
        # Start blinking animation
        self.blinking = True
        self.status_label.config(text="translating...")
        self.blink()
        
        # Measure render time (blinking happens every 500ms)
        frame_count = 0
        start_time = time.time()
        
        for _ in range(200):  # 10 seconds at lower update rate
            frame_start = time.time()
            self.root.update()
            frame_time = time.time() - frame_start
            self.metrics["blinking"]["render_time"].append(frame_time * 1000)  # Convert to ms
            frame_count += 1
            
            # Wait for next update (50ms for measurement)
            time.sleep(0.05)
        
        elapsed_time = time.time() - start_time
        actual_fps = frame_count / elapsed_time
        self.metrics["blinking"]["fps"] = actual_fps
        
        # Stop animation
        self.blinking = False
        self.status_label.config(text="ready")
        self.blink_label.config(image=self.black_icon)
        self.monitoring = False
        monitor_thread.join()
        
        # Display results
        self.display_results("blinking")
    
    def compare_performance(self):
        """Run both tests and compare results"""
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "Running comprehensive comparison...\n\n")
        self.root.update()
        
        # Test both implementations
        self.test_rainbow()
        time.sleep(2)  # Brief pause between tests
        self.test_blinking()
        
        # Display comprehensive comparison
        self.display_comparison()
    
    def display_results(self, test_type):
        """Display performance results for a test"""
        metrics = self.metrics[test_type]
        
        if metrics["cpu"]:
            avg_cpu = sum(metrics["cpu"]) / len(metrics["cpu"])
            max_cpu = max(metrics["cpu"])
        else:
            avg_cpu = max_cpu = 0
            
        if metrics["memory"]:
            avg_memory = sum(metrics["memory"]) / len(metrics["memory"])
            max_memory = max(metrics["memory"])
        else:
            avg_memory = max_memory = 0
            
        if metrics["render_time"]:
            avg_render = sum(metrics["render_time"]) / len(metrics["render_time"])
            max_render = max(metrics["render_time"])
        else:
            avg_render = max_render = 0
        
        fps = metrics.get("fps", 0)
        
        result_text = f"""
{'='*50}
{test_type.upper()} ANIMATION RESULTS:
{'='*50}
CPU Usage:
  Average: {avg_cpu:.2f}%
  Maximum: {max_cpu:.2f}%
  
Memory Usage:
  Average: {avg_memory:.2f} MB
  Maximum: {max_memory:.2f} MB
  
Rendering:
  Average Frame Time: {avg_render:.2f} ms
  Maximum Frame Time: {max_render:.2f} ms
  Actual FPS: {fps:.1f}
  
"""
        self.results_text.insert(tk.END, result_text)
        self.root.update()
    
    def display_comparison(self):
        """Display comparison between both implementations"""
        rainbow = self.metrics["rainbow"]
        blinking = self.metrics["blinking"]
        
        # Calculate averages
        rainbow_cpu = sum(rainbow["cpu"]) / len(rainbow["cpu"]) if rainbow["cpu"] else 0
        blinking_cpu = sum(blinking["cpu"]) / len(blinking["cpu"]) if blinking["cpu"] else 0
        
        rainbow_memory = sum(rainbow["memory"]) / len(rainbow["memory"]) if rainbow["memory"] else 0
        blinking_memory = sum(blinking["memory"]) / len(blinking["memory"]) if blinking["memory"] else 0
        
        rainbow_render = sum(rainbow["render_time"]) / len(rainbow["render_time"]) if rainbow["render_time"] else 0
        blinking_render = sum(blinking["render_time"]) / len(blinking["render_time"]) if blinking["render_time"] else 0
        
        comparison_text = f"""
{'='*50}
PERFORMANCE COMPARISON SUMMARY:
{'='*50}

CPU USAGE IMPACT:
  Rainbow:  {rainbow_cpu:.2f}% avg
  Blinking: {blinking_cpu:.2f}% avg
  Difference: {rainbow_cpu - blinking_cpu:+.2f}% ({((rainbow_cpu - blinking_cpu) / blinking_cpu * 100) if blinking_cpu else 0:+.1f}% relative)

MEMORY USAGE:
  Rainbow:  {rainbow_memory:.2f} MB avg
  Blinking: {blinking_memory:.2f} MB avg
  Difference: {rainbow_memory - blinking_memory:+.2f} MB

RENDERING PERFORMANCE:
  Rainbow:  {rainbow_render:.2f} ms per frame
  Blinking: {blinking_render:.2f} ms per frame
  Difference: {rainbow_render - blinking_render:+.2f} ms

VISUAL QUALITY:
  Rainbow:  Smooth gradient animation at 25 FPS
  Blinking: Simple toggle at 2 FPS (500ms interval)

RECOMMENDATION:
"""
        
        # Add recommendation based on results
        cpu_increase = rainbow_cpu - blinking_cpu
        if cpu_increase < 2:
            comparison_text += "✓ Rainbow animation has minimal CPU impact (<2% increase)\n"
        elif cpu_increase < 5:
            comparison_text += "⚠ Rainbow animation has moderate CPU impact (2-5% increase)\n"
        else:
            comparison_text += "✗ Rainbow animation has significant CPU impact (>5% increase)\n"
        
        memory_increase = rainbow_memory - blinking_memory
        if memory_increase < 5:
            comparison_text += "✓ Memory usage is acceptable (<5MB increase)\n"
        elif memory_increase < 10:
            comparison_text += "⚠ Memory usage is moderate (5-10MB increase)\n"
        else:
            comparison_text += "✗ Memory usage is high (>10MB increase)\n"
        
        self.results_text.insert(tk.END, comparison_text)
        self.root.update()
    
    def run(self):
        """Run the performance analyzer"""
        self.root.mainloop()


if __name__ == "__main__":
    analyzer = PerformanceAnalyzer()
    analyzer.run()