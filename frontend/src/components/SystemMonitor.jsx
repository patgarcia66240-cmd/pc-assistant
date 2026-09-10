import { useEffect, useRef, useState } from 'react'
import { SkeletonBlock } from './Skeleton'

function MetricIcon({ type }) {
  const paths = {
    cpu: <><rect x="5" y="5" width="14" height="14" rx="2" /><path d="M9 9h6v6H9zM9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" /></>,
    memory: <><rect x="3" y="6" width="18" height="12" rx="2" /><path d="M7 10v4M11 10v4M15 10v4M19 10v4" /></>,
    disk: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="2" /><path d="M12 4v6" /></>,
    gpu: <><rect x="3" y="5" width="15" height="14" rx="2" /><path d="M18 9h3v6h-3M7 9h7v6H7z" /></>,
    network: <><path d="M4 17h4v3H4zM10 11h4v9h-4zM16 4h4v16h-4z" /></>,
    activity: <><path d="M3 12h3l2.5-7 4 14 2.5-7H21" /></>,
  }
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-5 w-5">{paths[type]}</svg>
}

function formatBytes(bytes = 0) {
  if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(1)} Go`
  return `${(bytes / 1024 ** 2).toFixed(0)} Mo`
}

// Certains GPU intégrés (mémoire partagée avec la RAM système, ex. Intel Arc récents) annoncent
// dans leur propre nom une capacité totale ("... (16GB)") bien supérieure à leur petite réserve
// dédiée réelle (ex. 2 Go) — les deux chiffres sont vrais, ce sont juste deux choses différentes
// (mémoire dédiée vs plafond partagé calculé par Windows). On ne montre la double valeur que si
// l'écart est net (> 20%), sinon ça ne fait que répéter le même nombre deux fois pour rien.
function gpuMemoryDetail(gpu) {
  const dedicated = gpu.memory ? formatBytes(gpu.memory) : null
  const total = gpu.total_memory ? formatBytes(gpu.total_memory) : null
  if (dedicated && gpu.total_memory && gpu.total_memory > gpu.memory * 1.2) {
    return `${dedicated} dédiés · jusqu'à ${total} avec mémoire partagée`
  }
  return dedicated || total || 'Mémoire indisponible'
}

function formatUptime(seconds = 0) {
  const hours = Math.floor(seconds / 3600)
  const days = Math.floor(hours / 24)
  return days ? `${days} j ${hours % 24} h` : `${hours} h`
}

// Seuils de sévérité communs à toutes les jauges (CPU/RAM/disque/lecteurs) : une seule
// échelle partagée plutôt que des couleurs choisies au hasard par carte, pour que "c'est
// en train de chauffer" se lise pareil partout dans l'onglet.
const SEVERITY = {
  good: { fill: 'bg-emerald-500', track: 'bg-emerald-500/15', text: 'text-emerald-300' },
  warning: { fill: 'bg-amber-500', track: 'bg-amber-500/15', text: 'text-amber-300' },
  critical: { fill: 'bg-red-500', track: 'bg-red-500/15', text: 'text-red-300' },
}

function getSeverity(percent) {
  if (percent >= 85) return SEVERITY.critical
  if (percent >= 60) return SEVERITY.warning
  return SEVERITY.good
}

// Barre de jauge : le remplissage porte la sévérité, la piste est une marche plus claire
// de la MÊME teinte (pas un gris neutre) pour que l'état se lise sur toute la largeur,
// même d'un coup d'œil sur la partie non remplie.
function UsageBar({ value, severity }) {
  return (
    <div className={`mt-2.5 h-1.5 overflow-hidden rounded-full ${severity.track}`}>
      <div
        className={`h-full rounded-full ${severity.fill} transition-[width] duration-500`}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  )
}

// Mini sparkline (historique local des derniers relevés, en mémoire, aucune valeur
// inventée) : le tracé en gris discret, le dernier point ressort dans la couleur de
// sévérité du moment — reprend le principe "trend" d'une stat tile.
function Sparkline({ points, severity }) {
  if (!points || points.length < 2) return null
  const width = 100
  const height = 28
  const max = Math.max(100, ...points)
  const coords = points.map((value, index) => {
    const x = (index / (points.length - 1)) * width
    const y = height - (value / max) * height
    return [x, y]
  })
  const path = coords.map(([x, y], index) => `${index === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  const [lastX, lastY] = coords[coords.length - 1]
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="mt-2.5 h-6 w-full" preserveAspectRatio="none" aria-hidden="true">
      <path d={path} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" className="text-gray-600" />
      <circle cx={lastX} cy={lastY} r="2.2" className={severity.text} fill="currentColor" stroke="#1f2937" strokeWidth="1.5" />
    </svg>
  )
}

function MetricCard({ icon, label, value, detail, usage, severity, history }) {
  const valueColorClass = usage !== undefined ? severity.text : 'text-white'
  return (
    <div className="group rounded-xl border border-gray-800 bg-gradient-to-br from-gray-800/95 via-gray-800/80 to-gray-900/70 p-4 shadow-[0_4px_14px_rgba(8,15,35,0.35),inset_0_1px_0_rgba(255,255,255,0.04)] transition-colors hover:border-gray-700">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs text-gray-400">{label}</p>
          <p className={`mt-1.5 text-2xl font-semibold tracking-tight ${valueColorClass}`}>{value}</p>
        </div>
        <span className="shrink-0 rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500 p-2 text-white shadow-sm shadow-blue-950/30 transition-transform group-hover:scale-105">
          <MetricIcon type={icon} />
        </span>
      </div>
      {detail && <p className="mt-1.5 truncate text-xs text-gray-500">{detail}</p>}
      {usage !== undefined && <UsageBar value={usage} severity={severity} />}
      {history && <Sparkline points={history} severity={severity} />}
    </div>
  )
}

// Skeleton du premier chargement (avant le premier /api/system/info) : reprend la forme
// réelle de la page (en-tête + 6 cartes de métriques + 2 tableaux) plutôt qu'une simple
// phrase "Chargement...", pour que l'œil comprenne tout de suite la structure à venir.
function MetricCardSkeleton() {
  return (
    <div className="rounded-xl border border-gray-800 bg-gradient-to-br from-gray-800/95 via-gray-800/80 to-gray-900/70 p-4 shadow-[0_4px_14px_rgba(8,15,35,0.35),inset_0_1px_0_rgba(255,255,255,0.04)]">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <SkeletonBlock className="h-2.5 w-20" />
          <SkeletonBlock className="h-6 w-16" />
        </div>
        <SkeletonBlock className="h-8 w-8 rounded-lg" />
      </div>
      <SkeletonBlock className="mt-3 h-2.5 w-24" />
      <SkeletonBlock className="mt-2.5 h-1.5 w-full rounded-full" />
    </div>
  )
}

function TableRowsSkeleton({ rows }) {
  return (
    <div className="mt-4 space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonBlock key={i} className="h-8 w-full" />
      ))}
    </div>
  )
}

function SystemSkeleton() {
  return (
    <section className="h-full overflow-y-auto pr-1">
      <div className="mb-6 flex items-end justify-between gap-4">
        <div className="space-y-2">
          <SkeletonBlock className="h-3 w-32" />
          <SkeletonBlock className="h-7 w-44" />
          <SkeletonBlock className="h-3 w-60" />
        </div>
        <SkeletonBlock className="h-3 w-20" />
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <MetricCardSkeleton key={i} />
        ))}
      </div>
      <div className="mt-6 rounded-xl border border-gray-800 bg-gradient-to-br from-gray-800/95 via-gray-800/80 to-gray-900/70 p-5 shadow-[0_4px_14px_rgba(8,15,35,0.35),inset_0_1px_0_rgba(255,255,255,0.04)]">
        <SkeletonBlock className="h-5 w-52" />
        <TableRowsSkeleton rows={3} />
      </div>
      <div className="mt-6 rounded-xl border border-gray-800 bg-gradient-to-br from-gray-800/95 via-gray-800/80 to-gray-900/70 p-5 shadow-[0_4px_14px_rgba(8,15,35,0.35),inset_0_1px_0_rgba(255,255,255,0.04)]">
        <SkeletonBlock className="h-5 w-44" />
        <TableRowsSkeleton rows={4} />
      </div>
    </section>
  )
}

const HISTORY_LENGTH = 20

export default function SystemMonitor() {
  const [systemInfo, setSystemInfo] = useState(null)
  const [processes, setProcesses] = useState([])
  const [error, setError] = useState('')
  const cpuHistoryRef = useRef([])
  const memoryHistoryRef = useRef([])

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [infoRes, processRes] = await Promise.all([fetch('/api/system/info'), fetch('/api/system/processes')])
        if (!infoRes.ok || !processRes.ok) throw new Error('Impossible de charger les données système')
        const info = await infoRes.json()
        cpuHistoryRef.current = [...cpuHistoryRef.current, info.cpu_percent].slice(-HISTORY_LENGTH)
        memoryHistoryRef.current = [...memoryHistoryRef.current, info.memory.percent].slice(-HISTORY_LENGTH)
        setSystemInfo(info)
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
  if (!systemInfo) return <SystemSkeleton />

  const gpus = systemInfo.gpus || []
  const cpuSeverity = getSeverity(systemInfo.cpu_percent)
  const memorySeverity = getSeverity(systemInfo.memory.percent)
  const diskSeverity = getSeverity(systemInfo.disk.percent)

  return (
    <section className="h-full overflow-y-auto pr-1">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-blue-400">Vue d'ensemble</p>
          <h2 className="mt-1 text-2xl font-semibold text-white">État du PC</h2>
          <p className="mt-1 text-sm text-gray-400">Actualisation automatique toutes les 3 secondes</p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-gray-800 bg-gray-900/60 px-3 py-1.5 text-xs text-gray-300">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
          </span>
          Uptime {formatUptime(systemInfo.uptime_seconds)}
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <MetricCard
          icon="cpu" label="Processeur" value={`${systemInfo.cpu_percent.toFixed(1)}%`}
          detail={`${systemInfo.cpu_count || '?'} processeurs logiques`}
          usage={systemInfo.cpu_percent} severity={cpuSeverity} history={cpuHistoryRef.current}
        />
        <MetricCard
          icon="memory" label="Mémoire vive" value={`${systemInfo.memory.percent.toFixed(1)}%`}
          detail={`${formatBytes(systemInfo.memory.used)} utilisés sur ${formatBytes(systemInfo.memory.total)}`}
          usage={systemInfo.memory.percent} severity={memorySeverity} history={memoryHistoryRef.current}
        />
        <MetricCard
          icon="disk" label="Disque système" value={`${systemInfo.disk.percent.toFixed(1)}%`}
          detail={`${formatBytes(systemInfo.disk.used)} utilisés sur ${formatBytes(systemInfo.disk.total)}`}
          usage={systemInfo.disk.percent} severity={diskSeverity}
        />
        {gpus.length > 0 ? (
          gpus.map((gpu, index) => (
            <MetricCard
              key={`${gpu.name}-${index}`}
              icon="gpu"
              label={gpus.length > 1 ? `Carte graphique ${index + 1}` : 'Carte graphique'}
              value={gpu.name || 'Non détectée'}
              detail={gpuMemoryDetail(gpu)}
            />
          ))
        ) : (
          <MetricCard icon="gpu" label="Carte graphique" value="Non détectée" detail="Mémoire indisponible" />
        )}
        <MetricCard
          icon="network" label="Réseau entrant" value={`${systemInfo.network?.download_mbps || 0} Mb/s`}
          detail={`Sortant ${systemInfo.network?.upload_mbps || 0} Mb/s`}
        />
      </div>

      <div className="mt-6 rounded-xl border border-gray-800 bg-gradient-to-br from-gray-800/95 via-gray-800/80 to-gray-900/70 p-5 shadow-[0_4px_14px_rgba(8,15,35,0.35),inset_0_1px_0_rgba(255,255,255,0.04)]">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="shrink-0 rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500 p-2 text-white shadow-sm shadow-blue-950/30">
              <MetricIcon type="disk" />
            </span>
            <div>
              <h3 className="text-lg font-semibold text-white">Lecteurs et volumes</h3>
              <p className="text-sm text-gray-500">Disques locaux, partitions et supports USB montés</p>
            </div>
          </div>
          <span className="rounded-full border border-gray-700 bg-gray-900/60 px-3 py-1 text-xs text-gray-300">{systemInfo.drives?.length || 0} lecteurs</span>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[38rem] text-left text-sm">
            <thead className="border-b border-gray-700 text-xs uppercase tracking-wider text-gray-500">
              <tr>
                <th className="px-3 py-3">Lecteur</th>
                <th className="px-3 py-3">Type</th>
                <th className="px-3 py-3">Système</th>
                <th className="px-3 py-3 text-right">Utilisation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {(systemInfo.drives || []).map((drive) => {
                const driveSeverity = getSeverity(drive.percent)
                return (
                  <tr key={`${drive.device}-${drive.mountpoint}`} className="text-gray-300 transition-colors hover:bg-blue-500/5">
                    <td className="px-3 py-3 font-medium text-white">
                      <div>{drive.device}</div>
                      {drive.mountpoint !== drive.device && <div className="mt-1 text-xs text-gray-500">Montage : {drive.mountpoint}</div>}
                    </td>
                    <td className="px-3 py-3">
                      {drive.removable
                        ? <span className="rounded-full border border-amber-500/20 bg-amber-500/10 px-2 py-1 text-xs text-amber-300">USB / amovible</span>
                        : <span className="rounded-full border border-gray-700 bg-gray-900/60 px-2 py-1 text-xs text-gray-300">Local</span>}
                    </td>
                    <td className="px-3 py-3 text-gray-500">{drive.filesystem}</td>
                    <td className="px-3 py-3">
                      <div className="flex min-w-[12rem] items-center justify-end gap-3">
                        <div className={`w-20 overflow-hidden rounded-full ${driveSeverity.track}`}>
                          <div className={`h-1.5 rounded-full ${driveSeverity.fill}`} style={{ width: `${Math.min(100, drive.percent)}%` }} />
                        </div>
                        <div className="text-right">
                          <div className={`font-semibold tabular-nums ${driveSeverity.text}`}>{drive.percent.toFixed(1)}%</div>
                          <div className="text-xs tabular-nums text-gray-500">{formatBytes(drive.free)} libres</div>
                        </div>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-6 rounded-xl border border-gray-800 bg-gradient-to-br from-gray-800/95 via-gray-800/80 to-gray-900/70 p-5 shadow-[0_4px_14px_rgba(8,15,35,0.35),inset_0_1px_0_rgba(255,255,255,0.04)]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="shrink-0 rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500 p-2 text-white shadow-sm shadow-blue-950/30">
              <MetricIcon type="activity" />
            </span>
            <div>
              <h3 className="text-lg font-semibold text-white">Processus actifs</h3>
              <p className="text-sm text-gray-500">Les plus consommateurs en mémoire</p>
            </div>
          </div>
          <span className="rounded-full border border-gray-700 bg-gray-900/60 px-3 py-1 text-xs text-gray-300">{processes.length} affichés</span>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[34rem] text-left text-sm">
            <thead className="border-b border-gray-700 text-xs uppercase tracking-wider text-gray-500">
              <tr>
                <th className="px-3 py-3">Processus</th>
                <th className="px-3 py-3">PID</th>
                <th className="px-3 py-3 text-right">CPU</th>
                <th className="px-3 py-3 text-right">Mémoire</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {processes.map((process) => {
                const cpuValue = process.cpu_percent || 0
                const memoryValue = process.memory_percent || 0
                const cpuSev = getSeverity(cpuValue)
                const memSev = getSeverity(memoryValue)
                return (
                  <tr key={`${process.pid}-${process.name}`} className="text-gray-300 transition-colors hover:bg-blue-500/5">
                    <td className="max-w-[18rem] truncate px-3 py-3 font-medium text-white">{process.name || 'Inconnu'}</td>
                    <td className="px-3 py-3 tabular-nums text-gray-500">{process.pid}</td>
                    <td className={`px-3 py-3 text-right font-semibold tabular-nums ${cpuSev.text}`}>{cpuValue.toFixed(1)}%</td>
                    <td className="px-3 py-3">
                      <div className="ml-auto flex w-24 items-center justify-end gap-2">
                        <div className={`h-1.5 w-10 overflow-hidden rounded-full ${memSev.track}`}>
                          <div className={`h-full rounded-full ${memSev.fill}`} style={{ width: `${Math.min(100, memoryValue)}%` }} />
                        </div>
                        <span className={`w-12 text-right font-semibold tabular-nums ${memSev.text}`}>{memoryValue.toFixed(1)}%</span>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
