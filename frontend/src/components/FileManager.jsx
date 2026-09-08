import { useEffect, useMemo, useState } from 'react'

const API_URL = '/api/files'

function FolderIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5 text-blue-400" aria-hidden="true">
      <path d="M3.5 6.5h6l2 2h9v9.5a2 2 0 0 1-2 2h-15a2 2 0 0 1-2-2v-9.5a2 2 0 0 1 2-2Z" />
      <path d="M1.5 10.5h19" />
    </svg>
  )
}

function FileIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5 text-gray-400" aria-hidden="true">
      <path d="M6 3.5h8l4 4v13H6a2 2 0 0 1-2-2v-13a2 2 0 0 1 2-2Z" />
      <path d="M14 3.5v4h4M8 12h8M8 16h6" />
    </svg>
  )
}

export default function FileManager() {
  const [path, setPath] = useState('.')
  const [files, setFiles] = useState([])
  const [locations, setLocations] = useState([])
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadLocations = async () => {
    const response = await fetch(`${API_URL}/locations`)
    if (!response.ok) throw new Error('Impossible de charger les emplacements')
    setLocations((await response.json()).locations)
  }

  const loadFiles = async (nextPath = path) => {
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${API_URL}/list?path=${encodeURIComponent(nextPath)}`)
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Impossible de lire ce dossier')
      setPath(data.path)
      setFiles(data.files)
    } catch (loadError) {
      setError(loadError.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    Promise.all([loadLocations(), loadFiles('.')]).catch((loadError) => setError(loadError.message))
  }, [])

  const visibleFiles = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase()
    return files
      .filter((file) => filter === 'all' || (filter === 'folders' ? file.is_dir : !file.is_dir))
      .filter((file) => !normalizedSearch || file.name.toLowerCase().includes(normalizedSearch))
      .sort((left, right) => {
        if (left.is_dir !== right.is_dir) return left.is_dir ? -1 : 1
        return left.name.localeCompare(right.name, undefined, { sensitivity: 'base' })
      })
  }, [files, filter, search])

  const goUp = () => {
    if (path === '.') return
    const parts = path.split('/').filter(Boolean)
    parts.pop()
    loadFiles(parts.length ? parts.join('/') : '.')
  }

  return (
    <section className="flex h-full min-h-[32rem] flex-col gap-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-blue-400">Espace de travail</p>
          <h2 className="mt-1 text-2xl font-semibold text-white">Fichiers</h2>
          <p className="text-sm text-gray-400">Navigation rapide dans votre dossier utilisateur</p>
        </div>
        <button onClick={() => loadFiles()} className="rounded-md border border-gray-600 px-3 py-2 text-sm font-medium text-gray-200 transition hover:border-gray-500 hover:bg-gray-800">
          Actualiser
        </button>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-gray-800 pb-4">
        {locations.map((location) => (
          <button
            key={location.path}
            onClick={() => loadFiles(location.path)}
            className={`rounded-md px-3 py-2 text-sm font-medium transition ${path === location.path ? 'bg-blue-600 text-white shadow-sm' : 'bg-gray-800/70 text-gray-300 hover:bg-gray-700'}`}
          >
            {location.name}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        <button onClick={goUp} disabled={path === '.'} title="Dossier parent" aria-label="Dossier parent" className="rounded-md border border-gray-700 px-3 py-2 text-lg leading-none text-gray-200 transition hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-40">
          &larr;
        </button>
        <input
          value={path}
          onChange={(event) => setPath(event.target.value)}
          onKeyDown={(event) => event.key === 'Enter' && loadFiles()}
          className="min-w-[14rem] flex-1 rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white outline-none transition placeholder:text-gray-600 focus:border-blue-500"
          aria-label="Chemin relatif"
        />
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Rechercher..."
          className="w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white outline-none transition placeholder:text-gray-600 focus:border-blue-500 sm:w-56"
          aria-label="Rechercher un fichier"
        />
      </div>

      <div className="flex items-center justify-between gap-3" aria-label="Filtrer l'affichage">
        {[
          ['all', 'Tout'],
          ['folders', 'Dossiers'],
          ['files', 'Fichiers'],
        ].map(([value, label]) => (
          <button
            key={value}
            type="button"
            title={label}
            aria-label={label}
            aria-pressed={filter === value}
            onClick={() => setFilter(value)}
            className={`rounded-md border px-3 py-2 text-sm font-medium transition ${filter === value ? 'border-blue-500 bg-blue-600 text-white' : 'border-gray-700 bg-gray-800 text-gray-300 hover:bg-gray-700'}`}
          >
            {label}
          </button>
        ))}
      </div>

      {error && <p className="rounded border border-red-800 bg-red-950/40 px-3 py-2 text-sm text-red-300">{error}</p>}

      <div className="flex-1 overflow-auto rounded-md border border-gray-800 bg-gray-900">
        {loading ? (
          <p className="p-3 text-gray-400">Chargement...</p>
        ) : visibleFiles.length === 0 ? (
          <p className="p-3 text-gray-400">Aucun élément</p>
        ) : (
          <div className="min-w-[34rem]">
            <div className="grid grid-cols-[minmax(0,1fr)_8rem_7rem] gap-3 border-b border-gray-800 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
              <span>Nom</span>
              <span>Type</span>
              <span className="text-right">Taille</span>
            </div>
            {visibleFiles.map((file) => (
              <button
                key={file.path}
                onDoubleClick={() => file.is_dir && loadFiles(file.path)}
                disabled={!file.is_dir}
                className="grid w-full grid-cols-[minmax(0,1fr)_8rem_7rem] gap-3 border-b border-gray-800 px-4 py-3 text-left text-sm text-gray-200 transition last:border-b-0 hover:bg-gray-800 disabled:cursor-default disabled:hover:bg-transparent"
              >
                <span className="flex min-w-0 items-center gap-3">
                  {file.is_dir ? <FolderIcon /> : <FileIcon />}
                  <span className="truncate font-medium">{file.name}</span>
                </span>
                <span className={file.is_dir ? 'text-blue-400' : 'text-gray-500'}>{file.is_dir ? 'Dossier' : 'Fichier'}</span>
                <span className="text-right text-xs text-gray-500">{file.is_dir ? '—' : `${file.size} o`}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
