"""System monitoring service"""
import platform
import subprocess
import time

import psutil

class SystemService:
    _network_sample = None

    @staticmethod
    def _get_gpu_info():
        if platform.system() != "Windows":
            return {"name": "Détection GPU disponible sous Windows", "memory": None}
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_VideoController | Select-Object -First 1 Name,AdapterRAM | ConvertTo-Json -Compress"],
                capture_output=True,
                text=True,
                timeout=3,
                check=True,
            )
            data = __import__("json").loads(result.stdout)
            memory = data.get("AdapterRAM")
            return {"name": data.get("Name", "GPU inconnue"), "memory": memory}
        except (OSError, subprocess.SubprocessError, ValueError, TypeError):
            return {"name": "GPU non détecté", "memory": None}

    @classmethod
    def _get_network_speed(cls):
        now = time.monotonic()
        counters = psutil.net_io_counters()
        current = (now, counters.bytes_sent, counters.bytes_recv)
        previous = cls._network_sample
        cls._network_sample = current
        if previous is None or now <= previous[0]:
            return {"upload_mbps": 0, "download_mbps": 0}
        elapsed = now - previous[0]
        return {
            "upload_mbps": round((counters.bytes_sent - previous[1]) * 8 / elapsed / 1_000_000, 2),
            "download_mbps": round((counters.bytes_recv - previous[2]) * 8 / elapsed / 1_000_000, 2),
        }

    @staticmethod
    def _get_drives():
        drives = []
        for partition in psutil.disk_partitions(all=True):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                drives.append({
                    "device": partition.device or partition.mountpoint,
                    "mountpoint": partition.mountpoint,
                    "filesystem": partition.fstype or "Inconnu",
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                    "removable": "removable" in partition.opts.lower() or partition.device.startswith("USB"),
                })
            except (OSError, PermissionError):
                continue
        return drives

    @staticmethod
    def get_system_info():
        """Get current system info"""
        memory = psutil.virtual_memory()
        disk_path = f"{__import__('os').getenv('SystemDrive', 'C:')}\\"
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.2),
            "cpu_count": psutil.cpu_count(logical=True),
            "memory": memory._asdict(),
            "disk": psutil.disk_usage(disk_path)._asdict(),
            "gpu": SystemService._get_gpu_info(),
            "network": SystemService._get_network_speed(),
            "uptime_seconds": round(time.time() - psutil.boot_time()),
            "drives": SystemService._get_drives(),
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
        return sorted(processes, key=lambda item: item.get("memory_percent") or 0, reverse=True)[:20]

system_service = SystemService()
