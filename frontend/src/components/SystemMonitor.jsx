import { useEffect, useState } from 'react'

function MetricIcon({ type }) {
  const paths = {
    cpu: <><rect x="5" y="5" width="14" height="14" rx="2" /><path d="M9 9h6v6H9zM9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" /></>,
    memory: <><rect x="3" y="6" width="18" height="12" rx="2" /><path d="M7 10v4M11 10v4M15 10v4M19 10v4" /></>,
    disk: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="2" /><path d="M12 4v6" /></>,
    gpu: <><rect x="3" y="5" width="15" height="14" rx="2" /><path d="M18 9h3v6h-3M7 9h7v6H7z" /></>,
    network: <><path d="M4 17h4v3H4zM10 11h4v9h-4zM16 4h4v16h-4z" /></>,
  }
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-5 w-5">{paths[type]}</svg>
}

function formatBytes(bytes = 0) {
  if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(1)} Go`
  return `${(bytes / 1024 ** 2).toFixed(0)} Mo`
}

function formatUptime(seconds = 0) {
  const hours = Math.floor(seconds / 3600)
  const days = Math.floor(hours / 24)
  return days ? `${days} j ${hours % 24} h` : `${hours} h`
}

function UsageBar({ value, color = 'bg-blue-500' }) {
  return <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-gray-700"><div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} /></div>
}

function MetricCard({ icon, label, value, detail, usage, color }) {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-800/80 p-5 shadow-lg shadow-black/10">
      <div className="flex items-start justify-between gap-3">
        <div><p className="text-sm text-gray-400">{label}</p><p className="mt-2 text-3xl font-semibold tracking-tight text-white">{value}</p></div>
        <span className="rounded-lg bg-blue-500/10 p-2.5 text-blue-300"><MetricIcon type={icon} /></span>
      </div>
      {detail && <p className="mt-2 truncate text-xs text-gray-500">{detail}</p>}
      {usage !== undefined && <UsageBar value={usage} color={color} />}
    </div>
  )
}

export default function SystemMonitor() {
  const [systemInfo, setSystemInfo] = useState(null)
  const [processes, setProcesses] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [infoRes, processRes] = await Promise.all([fetch('/api/system/info'), fetch('/api/system/processes')])
        if (!infoRes.ok || !processRes.ok) throw new Error('Impossible de charger les données système')
        setSystemInfo(await infoRes.json())
        setProcesses((await processRes.json()).processes || [])
        setError('')
      } catch (loadError) {
        setError(loadError.message)
      }
    }
    fetchData()
    const interval = setInterval(fetchData, 3000)
    return () => clearInterval(interval)
  }, [])

  if (error) return <p className="rounded-lg border border-red-800 bg-red-950/30 p-4 text-sm text-red-300">{error}</p>
  if (!systemInfo) return <p className="text-sm text-gray-400">Chargement des données système...</p>

  const gpuMemory = systemInfo.gpu?.memory ? formatBytes(systemInfo.gpu.memory) : 'Mémoire indisponible'
  return (
    <section className="h-full overflow-y-auto pr-1">
      <div className="mb-6 flex items-end justify-between gap-4">
        <div><p className="text-xs font-semibold uppercase tracking-widest text-blue-400">Vue d’ensemble</p><h2 className="mt-1 text-2xl font-semibold text-white">État du PC</h2><p className="mt-1 text-sm text-gray-400">Actualisation automatique toutes les 3 secondes</p></div>
        <p className="text-xs text-gray-500">Uptime {formatUptime(systemInfo.uptime_seconds)}</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <MetricCard icon="cpu" label="Processeur" value={`${systemInfo.cpu_percent.toFixed(1)}%`} detail={`${systemInfo.cpu_count || '?'} processeurs logiques`} usage={systemInfo.cpu_percent} />
        <MetricCard icon="memory" label="Mémoire vive" value={`${systemInfo.memory.percent.toFixed(1)}%`} detail={`${formatBytes(systemInfo.memory.used)} utilisés sur ${formatBytes(systemInfo.memory.total)}`} usage={systemInfo.memory.percent} color="bg-emerald-500" />
        <MetricCard icon="disk" label="Disque système" value={`${systemInfo.disk.percent.toFixed(1)}%`} detail={`${formatBytes(systemInfo.disk.used)} utilisés sur ${formatBytes(systemInfo.disk.total)}`} usage={systemInfo.disk.percent} color="bg-amber-500" />
        <MetricCard icon="gpu" label="Carte graphique" value={systemInfo.gpu?.name || 'Non détectée'} detail={gpuMemory} />
        <MetricCard icon="network" label="Réseau entrant" value={`${systemInfo.network?.download_mbps || 0} Mb/s`} detail={`Sortant ${systemInfo.network?.upload_mbps || 0} Mb/s`} />
        <MetricCard icon="disk" label="Lecteurs détectés" value={systemInfo.drives?.length || 0} detail={`${systemInfo.drives?.filter((drive) => drive.removable).length || 0} support(s) amovible(s)`} />
      </div>
      <div className="mt-6 rounded-xl border border-gray-800 bg-gray-800/70 p-5">
        <div className="flex items-center justify-between gap-3"><div><h3 className="text-lg font-semibold text-white">Lecteurs et volumes</h3><p className="text-sm text-gray-500">Disques locaux, partitions et supports USB montés</p></div><span className="rounded-full bg-gray-700 px-3 py-1 text-xs text-gray-300">{systemInfo.drives?.length || 0} lecteurs</span></div>
        <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[38rem] text-left text-sm"><thead className="border-b border-gray-700 text-xs uppercase tracking-wider text-gray-500"><tr><th className="px-3 py-3">Lecteur</th><th className="px-3 py-3">Type</th><th className="px-3 py-3">Système</th><th className="px-3 py-3 text-right">Utilisation</th></tr></thead><tbody className="divide-y divide-gray-800">{(systemInfo.drives || []).map((drive) => <tr key={`${drive.device}-${drive.mountpoint}`} className="text-gray-300"><td className="px-3 py-3 font-medium text-white"><div>{drive.device}</div>{drive.mountpoint !== drive.device && <div className="mt-1 text-xs text-gray-500">Montage : {drive.mountpoint}</div>}</td><td className="px-3 py-3">{drive.removable ? <span className="rounded-full bg-amber-500/10 px-2 py-1 text-xs text-amber-300">USB / amovible</span> : <span className="rounded-full bg-gray-700 px-2 py-1 text-xs text-gray-300">Local</span>}</td><td className="px-3 py-3 text-gray-500">{drive.filesystem}</td><td className="px-3 py-3"><div className="flex min-w-[12rem] items-center justify-end gap-3"><div className="w-20 overflow-hidden rounded-full bg-gray-700"><div className={`h-1.5 rounded-full ${drive.percent > 85 ? 'bg-red-400' : 'bg-blue-400'}`} style={{ width: `${Math.min(100, drive.percent)}%` }} /></div><div className="text-right"><div className={drive.percent > 85 ? 'font-semibold text-red-300' : 'font-semibold text-blue-300'}>{drive.percent.toFixed(1)}%</div><div className="text-xs text-gray-500">{formatBytes(drive.free)} libres</div></div></div></td></tr>)}</tbody></table></div>
      </div>
      <div className="mt-6 rounded-xl border border-gray-800 bg-gray-800/70 p-5">
        <div className="flex items-center justify-between"><div><h3 className="text-lg font-semibold text-white">Processus actifs</h3><p className="text-sm text-gray-500">Les plus consommateurs en mémoire</p></div><span className="rounded-full bg-gray-700 px-3 py-1 text-xs text-gray-300">{processes.length} affichés</span></div>
        <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[34rem] text-left text-sm"><thead className="border-b border-gray-700 text-xs uppercase tracking-wider text-gray-500"><tr><th className="px-3 py-3">Processus</th><th className="px-3 py-3">PID</th><th className="px-3 py-3 text-right">CPU</th><th className="px-3 py-3 text-right">Mémoire</th></tr></thead><tbody className="divide-y divide-gray-800">{processes.map((process) => <tr key={`${process.pid}-${process.name}`} className="text-gray-300"><td className="max-w-[18rem] truncate px-3 py-3 font-medium">{process.name || 'Inconnu'}</td><td className="px-3 py-3 text-gray-500">{process.pid}</td><td className="px-3 py-3 text-right">{(process.cpu_percent || 0).toFixed(1)}%</td><td className="px-3 py-3 text-right">{(process.memory_percent || 0).toFixed(1)}%</td></tr>)}</tbody></table></div>
      </div>
    </section>
  )
}
