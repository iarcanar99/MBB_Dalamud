"""
Simple CPU Monitor for Magicite Babel
Monitors system CPU usage to adjust MBB performance
"""

import psutil
import time
import logging
from typing import Dict, Tuple


class SimpleCPUMonitor:
    def __init__(self, settings=None):
        """
        Initialize CPU Monitor with settings
        
        Args:
            settings: Settings object for configuration
        """
        self.settings = settings
        self.last_check_time = 0
        self.check_interval = 0.5  # ตรวจทุก 0.5 วินาที
        self.cached_mode = 'medium'
        self.cached_cpu_percent = 0
        
        # Default thresholds
        self.cpu_threshold_high = 70
        self.cpu_threshold_low = 30
        
        # Default intervals (seconds)
        self.intervals = {
            'high': 0.5,      # เกมหนัก -> MBB หยุดนานขึ้น
            'medium': 0.3,    # ปกติ
            'low': 0.15       # ระบบว่าง -> MBB ทำงานเร็วขึ้น
        }
        
        # Load settings if available
        self._load_settings()
        
        # Avoid Unicode logging issues in Windows console
        print(f"CPU Monitor: High threshold {self.cpu_threshold_high}%, Low {self.cpu_threshold_low}%")
    
    def _load_settings(self):
        """Load CPU monitoring settings from settings object"""
        if not self.settings:
            return
            
        try:
            # Load thresholds
            self.cpu_threshold_high = self.settings.get("cpu_high_threshold", 70)
            self.cpu_threshold_low = self.settings.get("cpu_low_threshold", 30)
            
            # Load intervals
            high_interval = self.settings.get("cpu_high_interval", 0.5)
            medium_interval = self.settings.get("cpu_medium_interval", 0.3)
            low_interval = self.settings.get("cpu_low_interval", 0.15)
            
            self.intervals = {
                'high': high_interval,
                'medium': medium_interval,
                'low': low_interval
            }
            
            print(f"CPU Monitor settings loaded - Thresholds: {self.cpu_threshold_low}-{self.cpu_threshold_high}%")
            
        except Exception as e:
            logging.warning(f"Failed to load CPU monitor settings: {e}, using defaults")
    
    def is_enabled(self) -> bool:
        """Check if CPU monitoring is enabled in settings"""
        if not self.settings:
            return True  # Default enabled
        return self.settings.get("enable_cpu_monitoring", True)
    
    def get_cpu_status(self) -> Tuple[str, float]:
        """
        Get current CPU status with caching
        
        Returns:
            Tuple of (mode, cpu_percent)
            mode: 'high', 'medium', 'low'
        """
        current_time = time.time()
        
        # Use cached value if recent enough
        if current_time - self.last_check_time < self.check_interval:
            return self.cached_mode, self.cached_cpu_percent
        
        # Get new CPU reading
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.cached_cpu_percent = cpu_percent
            self.last_check_time = current_time
            
            # Determine mode
            if cpu_percent > self.cpu_threshold_high:
                self.cached_mode = 'high'
            elif cpu_percent < self.cpu_threshold_low:
                self.cached_mode = 'low'
            else:
                self.cached_mode = 'medium'
                
            return self.cached_mode, cpu_percent
            
        except Exception as e:
            logging.error(f"Failed to get CPU status: {e}")
            return 'medium', 50  # Safe fallback
    
    def get_cpu_mode(self) -> str:
        """Get current CPU mode only"""
        mode, _ = self.get_cpu_status()
        return mode
    
    def get_sleep_interval(self) -> float:
        """Get recommended sleep interval based on CPU usage"""
        if not self.is_enabled():
            return 0.3  # Default interval when disabled
            
        mode = self.get_cpu_mode()
        return self.intervals.get(mode, 0.3)
    
    def get_status_message(self) -> str:
        """Get human-readable status message"""
        if not self.is_enabled():
            return ""
            
        mode, cpu_percent = self.get_cpu_status()
        
        status_messages = {
            'high': f'Gaming mode ({cpu_percent:.0f}% CPU) - Reduced activity',
            'medium': f'Normal operation ({cpu_percent:.0f}% CPU)',
            'low': f'System idle ({cpu_percent:.0f}% CPU) - Enhanced performance'
        }
        
        return status_messages.get(mode, f'📊 CPU: {cpu_percent:.0f}%')
    
    def get_performance_info(self) -> Dict:
        """Get detailed performance information"""
        mode, cpu_percent = self.get_cpu_status()
        sleep_interval = self.get_sleep_interval()
        
        return {
            'enabled': self.is_enabled(),
            'cpu_percent': cpu_percent,
            'mode': mode,
            'sleep_interval': sleep_interval,
            'thresholds': {
                'high': self.cpu_threshold_high,
                'low': self.cpu_threshold_low
            },
            'intervals': self.intervals.copy()
        }


# Test function
def test_monitor():
    """Test function for SimpleCPUMonitor"""
    print("Testing SimpleCPUMonitor...")
    monitor = SimpleCPUMonitor()
    
    for i in range(5):
        info = monitor.get_performance_info()
        message = monitor.get_status_message()
        
        print(f"Test {i+1}:")
        print(f"  CPU: {info['cpu_percent']:.1f}%")
        print(f"  Mode: {info['mode']}")
        print(f"  Sleep: {info['sleep_interval']}s")
        print(f"  Status: {message}")
        print()
        
        time.sleep(1)


if __name__ == "__main__":
    test_monitor()