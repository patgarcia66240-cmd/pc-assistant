"""System monitoring service"""
import psutil

class SystemService:
    @staticmethod
    def get_system_info():
        """Get current system info"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": psutil.virtual_memory()._asdict(),
            "disk": psutil.disk_usage("/")._asdict()
        }
    
    @staticmethod
    def get_processes():
        """Get running processes"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:20]

system_service = SystemService()
