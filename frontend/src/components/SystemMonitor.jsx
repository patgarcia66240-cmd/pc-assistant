import { useState, useEffect } from 'react'

export default function SystemMonitor() {
  const [systemInfo, setSystemInfo] = useState(null)
  const [processes, setProcesses] = useState([])

  useEffect(() => {
    const fetchData = async () => {
      try {
        const infoRes = await fetch('/api/system/info')
        setSystemInfo(await infoRes.json())

        const procRes = await fetch('/api/system/processes')
        setProcesses(await procRes.json())
      } catch (error) {
        console.error('System monitor error:', error)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 2000)
    return () => clearInterval(interval)
  }, [])

  if (!systemInfo) return <div>Loading...</div>

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-gray-800 p-4 rounded">
          <div className="text-gray-400 text-sm">CPU</div>
          <div className="text-2xl font-bold">{systemInfo.cpu_percent.toFixed(1)}%</div>
        </div>
        <div className="bg-gray-800 p-4 rounded">
          <div className="text-gray-400 text-sm">Memory</div>
          <div className="text-2xl font-bold">{(systemInfo.memory.percent).toFixed(1)}%</div>
        </div>
        <div className="bg-gray-800 p-4 rounded">
          <div className="text-gray-400 text-sm">Disk</div>
          <div className="text-2xl font-bold">{(systemInfo.disk.percent).toFixed(1)}%</div>
        </div>
      </div>
    </div>
  )
}
