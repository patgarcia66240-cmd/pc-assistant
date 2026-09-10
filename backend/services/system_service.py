"""System monitoring service"""
import platform
import re
import subprocess
import time

import psutil

# Amorce le calcul NON bloquant de psutil.cpu_percent() dès le démarrage du backend. Sans cet
# appel, la toute première mesure comparerait les temps CPU depuis le démarrage du module (donc
# depuis le lancement du serveur) au lieu de depuis la dernière requête — ce premier relevé est
# documenté par psutil lui-même comme "meaningless" et à ignorer. On "consomme" donc ce premier
# relevé sans intérêt ici, une fois, pour que la toute première requête /api/system/info renvoie
# déjà une vraie valeur.
psutil.cpu_percent(interval=None)

# Certains pilotes (constaté avec les GPU Intel Arc intégrés récents) accolent directement au
# nom de l'adaptateur la mémoire graphique totale QUE WINDOWS CALCULE (dédiée + partagée
# empruntée à la RAM système à la demande), ex. "Intel(R) Arc(TM) 140T GPU (16GB)". Ce chiffre
# n'est PAS lisible via HardwareInformation.qwMemorySize (qui ne donne que la petite réserve
# dédiée, ex. 2 Go) : Microsoft documente ce plafond comme
# MIN(RAM*0.8, MAX(RAM-16Go, RAM*0.5)) (doc pilotes WDDM "Calculating Graphics Memory"),
# recalculer cette formule nous-mêmes serait redondant et plus fragile que de simplement lire
# la valeur déjà calculée par Windows/le pilote et présente telle quelle dans le nom — donnée
# réelle, pas une estimation maison. Vérifié le 10/09/2026 : 31,4 Go RAM / 2 ≈ 15,7 Go ≈ "16GB",
# cohérent avec la formule documentée.
_NAME_TOTAL_MEMORY_PATTERN = re.compile(r"\((\d+(?:[.,]\d+)?)\s*GB\)", re.IGNORECASE)

class SystemService:
    _network_sample = None

    # Calculée une seule fois par lancement du backend, pas à chaque appel : le matériel GPU ne
    # change pas en cours de session, et get_system_info() est interrogé toutes les 3s par le
    # frontend — relancer PowerShell + parcourir le registre à ce rythme serait un gaspillage
    # inutile (et plus lent qu'avant, vu ce que la version corrigée doit lire en plus).
    _gpu_cache = None

    _GPU_POWERSHELL_SCRIPT = r'''
$classKey = "HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
$subkeys = Get-ChildItem $classKey -ErrorAction SilentlyContinue |
    Where-Object { $_.PSChildName -match '^\d{4}$' } |
    ForEach-Object { Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue }

$gpus = Get-CimInstance Win32_VideoController |
    Where-Object { $_.PNPDeviceID -match '^PCI\\' -and $_.Status -eq 'OK' }

$result = foreach ($gpu in $gpus) {
    $vram = [uint64]$gpu.AdapterRAM
    $devId = ($gpu.PNPDeviceID -replace '^PCI\\','').ToLower()
    $match = $subkeys | Where-Object {
        $_.MatchingDeviceId -and $devId -like "*$($_.MatchingDeviceId.Split('\')[-1].ToLower())*"
    } | Select-Object -First 1
    if ($match.'HardwareInformation.qwMemorySize') {
        $vram = [uint64]$match.'HardwareInformation.qwMemorySize'
    }
    [PSCustomObject]@{
        Name = $gpu.Name
        VRAMBytes = $vram
    }
}
@($result) | ConvertTo-Json -Compress
'''

    @classmethod
    def _get_gpus(cls):
        """Liste de TOUTES les cartes graphiques, pas juste la première : l'ancien
        `Select-Object -First 1` masquait les machines multi-GPU (ex. Intel Core Ultra avec un
        Arc intégré ET un Arc dédié — cas de l'utilisatrice, 2 GPU jamais affichés qu'un). Filtre
        aussi aux périphériques PCI actifs (Status=OK) pour écarter les pilotes miroir RDP /
        Basic Display que Win32_VideoController liste aussi parfois.
        AdapterRAM (WMI) est un uint32 qui déborde au-delà de ~4 Go : une carte de 16 Go
        remontait "2.0 Go" (bug constaté et vérifié le 10/09/2026 — cf. forums NVIDIA developer
        et issue wmi-rs #35, même limite documentée par Microsoft : AdapterRAM est bien typé
        uint32 dans le schéma Win32_VideoController). On lit donc la vraie valeur 64 bits dans
        HardwareInformation.qwMemorySize (registre, sous la classe Display adapters
        {4d36e968-...}), avec repli sur AdapterRAM si cette valeur est absente (vieux pilotes
        non-WDDM)."""
        if cls._gpu_cache is not None:
            return cls._gpu_cache
        if platform.system() != "Windows":
            cls._gpu_cache = [{"name": "Détection GPU disponible sous Windows", "memory": None, "total_memory": None}]
            return cls._gpu_cache
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cls._GPU_POWERSHELL_SCRIPT],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )
            data = __import__("json").loads(result.stdout or "null")
            if data is None:
                data = []
            if isinstance(data, dict):
                data = [data]
            gpus = []
            for item in data:
                name = item.get("Name") or "GPU inconnue"
                total_match = _NAME_TOTAL_MEMORY_PATTERN.search(name)
                total_memory = (
                    round(float(total_match.group(1).replace(",", ".")) * (1024 ** 3))
                    if total_match else None
                )
                gpus.append({"name": name, "memory": item.get("VRAMBytes"), "total_memory": total_memory})
            cls._gpu_cache = gpus or [{"name": "GPU non détecté", "memory": None, "total_memory": None}]
        except (OSError, subprocess.SubprocessError, ValueError, TypeError):
            cls._gpu_cache = [{"name": "GPU non détecté", "memory": None, "total_memory": None}]
        return cls._gpu_cache

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
        # all=False (au lieu de all=True) au lieu de tout lister : sous Windows, psutil ne garde
        # par défaut "que les disques durs et lecteurs CD" (commentaire du code source psutil,
        # arch/windows/disk.c) et exclut notamment les LECTEURS RÉSEAU MAPPÉS (qui peuvent
        # bloquer plusieurs secondes si le partage est injoignable) — cause probable de la
        # lenteur constatée le 10/09/2026 sur l'onglet Système. Vérifié : les vrais disques USB
        # amovibles restent inclus (seule la disquette A:\ est exclue parmi les lecteurs
        # amovibles), donc aucune perte de détection pour l'utilisatrice.
        for partition in psutil.disk_partitions(all=False):
            # Lecteur CD/DVD sans disque inséré : psutil.disk_usage() peut lever une erreur,
            # déclencher une popup Windows ("Insérer un disque"), ou bloquer plusieurs secondes.
            # Contournement recommandé par psutil lui-même (scripts/disk_usage.py de leur repo) :
            # ignorer les entrées "cdrom" sans système de fichiers détecté.
            if "cdrom" in partition.opts.lower() or not partition.fstype:
                continue
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
            # interval=None (non bloquant, delta depuis le dernier appel) au lieu de interval=0.2
            # (qui bloquait 200ms sur CHAQUE requête, alors que le frontend interroge toutes les
            # 3s — largement assez pour une mesure fiable sans avoir à dormir explicitement ici).
            # Amorcé une fois au chargement du module, voir plus haut. Vérifié dans la doc psutil.
            "cpu_percent": psutil.cpu_percent(interval=None),
            "cpu_count": psutil.cpu_count(logical=True),
            "memory": memory._asdict(),
            "disk": psutil.disk_usage(disk_path)._asdict(),
            "gpus": SystemService._get_gpus(),
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
