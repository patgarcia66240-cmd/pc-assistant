import { useEffect, useMemo, useState } from 'react'
import { SkeletonBlock } from './Skeleton'

const API_URL = '/api/files'

function FolderIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5 shrink-0 text-blue-400" aria-hidden="true">
      <path d="M3.5 6.5h6l2 2h9v9.5a2 2 0 0 1-2 2h-15a2 2 0 0 1-2-2v-9.5a2 2 0 0 1 2-2Z" />
      <path d="M1.5 10.5h19" />
    </svg>
  )
}

function FileIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5 shrink-0 text-gray-400" aria-hidden="true">
      <path d="M6 3.5h8l4 4v13H6a2 2 0 0 1-2-2v-13a2 2 0 0 1 2-2Z" />
      <path d="M14 3.5v4h4M8 12h8M8 16h6" />
    </svg>
  )
}

function HomeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4 shrink-0" aria-hidden="true">
      <path d="M4 11.5 12 4l8 7.5" />
      <path d="M6 10v9a1 1 0 0 0 1 1h3v-6h4v6h3a1 1 0 0 0 1-1v-9" />
    </svg>
  )
}

function LocationIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4 shrink-0" aria-hidden="true">
      <path d="M3.5 6.5h6l2 2h9v9.5a2 2 0 0 1-2 2h-15a2 2 0 0 1-2-2v-9.5a2 2 0 0 1 2-2Z" />
    </svg>
  )
}

function ParentFolderIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5 shrink-0 text-blue-400" aria-hidden="true">
      <path d="M12 19V5M5 12l7-7 7 7" />
    </svg>
  )
}

function BackIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4" aria-hidden="true">
      <path d="M19 12H5M11 6l-6 6 6 6" />
    </svg>
  )
}

function ChevronIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5 shrink-0 text-gray-600" aria-hidden="true">
      <path d="M9 6l6 6-6 6" />
    </svg>
  )
}

function EditPathIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4" aria-hidden="true">
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </svg>
  )
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4 shrink-0 text-gray-500" aria-hidden="true">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </svg>
  )
}

function FilterIcon({ type }) {
  if (type === 'folders') {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5 shrink-0" aria-hidden="true">
        <path d="M3.5 6.5h6l2 2h9v9.5a2 2 0 0 1-2 2h-15a2 2 0 0 1-2-2v-9.5a2 2 0 0 1 2-2Z" />
      </svg>
    )
  }
  if (type === 'files') {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5 shrink-0" aria-hidden="true">
        <path d="M6 3.5h8l4 4v13H6a2 2 0 0 1-2-2v-13a2 2 0 0 1 2-2Z" />
        <path d="M14 3.5v4h4" />
      </svg>
    )
  }
  return null
}

function formatSize(bytes) {
  if (bytes >= 1024 ** 2) return `${(bytes / 1024 ** 2).toFixed(1)} Mo`
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} Ko`
  return `${bytes} o`
}

// Lignes de tableau grisées pendant le chargement — reprend la grille réelle (nom / type /
// taille) plutôt qu'une simple phrase "Chargement...".
function FileRowSkeleton() {
  return (
    <div className="grid w-full grid-cols-[minmax(0,1fr)_8rem_7rem] items-center gap-3 border-b border-gray-800 px-4 py-3 last:border-b-0">
      <span className="flex min-w-0 items-center gap-3">
        <SkeletonBlock className="h-5 w-5 shrink-0 rounded" />
        <SkeletonBlock className="h-3 w-40" />
      </span>
      <SkeletonBlock className="h-3 w-14" />
      <SkeletonBlock className="ml-auto h-3 w-10" />
    </div>
  )
}

function FilesSkeleton() {
  return (
    <div className="min-w-[34rem]">
      <div className="grid grid-cols-[minmax(0,1fr)_8rem_7rem] gap-3 border-b border-gray-700 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
        <span>Nom</span>
        <span>Type</span>
        <span className="text-right">Taille</span>
      </div>
      {Array.from({ length: 7 }).map((_, i) => (
        <FileRowSkeleton key={i} />
      ))}
    </div>
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
  // Saisie manuelle d'un chemin : repliée par défaut (le fil d'Ariane suffit pour naviguer dans
  // la quasi-totalité des cas) et sur son propre brouillon (pathDraft), pour ne plus mélanger
  // "ce qu'on tape" et "le dossier réellement affiché" comme avant (l'input reflétait `path`
  // directement, donc changeait de sens dès la première frappe).
  const [manualPathOpen, setManualPathOpen] = useState(false)
  const [pathDraft, setPathDraft] = useState('.')

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

  // Fil d'Ariane à partir de `path` ("." ou "documents/rapports/2024") : le premier segment
  // reprend le libellé de l'emplacement s'il en connaît un (ex. "documents" -> "Documents"),
  // les suivants restent le nom réel du dossier. Remplace l'ancien input texte brut ("." ou
  // "documents/rapports") comme affichage principal — bien plus lisible et cliquable.
  const breadcrumbs = useMemo(() => {
    if (path === '.') return [{ label: 'Accueil', value: '.' }]
    const segments = path.split('/').filter(Boolean)
    const known = locations.find((location) => location.path === segments[0])
    const crumbs = [{ label: 'Accueil', value: '.' }]
    let accumulated = ''
    segments.forEach((segment, index) => {
      accumulated = accumulated ? `${accumulated}/${segment}` : segment
      crumbs.push({ label: index === 0 && known ? known.name : segment, value: accumulated })
    })
    return crumbs
  }, [path, locations])

  const goUp = () => {
    if (path === '.') return
    const parts = path.split('/').filter(Boolean)
    parts.pop()
    loadFiles(parts.length ? parts.join('/') : '.')
  }

  // Raccourci clavier "remonter au dossier parent" : Alt+Flèche haut uniquement. Retour arrière
  // (Backspace) a été essayé mais est intercepté au niveau natif par WebView2 (le moteur de la
  // fenêtre Tauri) AVANT même d'atteindre le JS de la page — Backspace fait partie de ses
  // "browser accelerator keys" par défaut (au même titre que Ctrl+F, F5, F12...), donc
  // preventDefault() côté JS ne peut rien y faire (vérifié le 10/09/2026, doc WebView2
  // CoreWebView2Settings.AreBrowserAcceleratorKeysEnabled). Le débloquer nécessiterait du code
  // Rust désactivant CE réglage globalement — mais il coupe aussi F12/DevTools, Ctrl+F, Ctrl+P
  // etc. pour toute l'appli, donc pas retenu. On ignore la frappe si le focus est dans un champ
  // de saisie (recherche, chemin manuel) pour ne pas interférer avec la frappe normale.
  useEffect(() => {
    const handleKeyDown = (event) => {
      const isAltUp = event.altKey && event.key === 'ArrowUp'
      if (!isAltUp) return

      const target = event.target
      const isTyping =
        target instanceof HTMLElement &&
        (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)
      if (isTyping) return

      event.preventDefault()
      goUp()
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [path])

  return (
    <section className="flex h-full min-h-[32rem] flex-col gap-5 overflow-y-auto pr-1">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-blue-400">Espace de travail</p>
          <h2 className="mt-1 text-2xl font-semibold text-white">Fichiers</h2>
          <p className="mt-1 text-sm text-gray-400">Navigation rapide dans votre dossier utilisateur — double-cliquez un dossier pour l'ouvrir</p>
        </div>
        <button onClick={() => loadFiles()} className="inline-flex min-h-[44px] shrink-0 items-center rounded-md border border-gray-700 px-3 py-2 text-sm font-medium text-gray-200 transition hover:border-gray-600 hover:bg-gray-800">
          Actualiser
        </button>
      </div>

      <div className="rounded-xl border border-gray-800 bg-gray-800/70 p-4">
        <div className="flex flex-wrap gap-2">
          {locations.map((location) => (
            <button
              key={location.path}
              onClick={() => loadFiles(location.path)}
              aria-current={path === location.path ? 'true' : undefined}
              className={`inline-flex min-h-[44px] items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium transition ${
                path === location.path
                  ? 'bg-gradient-to-br from-blue-600 to-cyan-500 text-white shadow-md shadow-blue-950/30'
                  : 'bg-gray-900/60 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {location.path === '.' ? <HomeIcon /> : <LocationIcon />}
              {location.name}
            </button>
          ))}
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button onClick={goUp} disabled={path === '.'} title="Dossier parent" aria-label="Dossier parent" className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-gray-700 text-gray-300 transition hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-40">
            <BackIcon />
          </button>

          {manualPathOpen ? (
            <input
              autoFocus
              value={pathDraft}
              onChange={(event) => setPathDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  loadFiles(pathDraft)
                  setManualPathOpen(false)
                } else if (event.key === 'Escape') {
                  setManualPathOpen(false)
                }
              }}
              onBlur={() => setManualPathOpen(false)}
              placeholder="ex. documents/rapports"
              className="min-w-[14rem] flex-1 rounded-md border border-blue-500 bg-gray-900 px-3 py-2 text-sm text-white outline-none placeholder:text-gray-500"
              aria-label="Aller à un chemin relatif"
            />
          ) : (
            <nav
              aria-label="Fil d'Ariane"
              className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto rounded-md border border-gray-700 bg-gray-900/60 px-2 py-2"
            >
              {breadcrumbs.map((crumb, index) => (
                <span key={crumb.value} className="flex shrink-0 items-center gap-1">
                  {index > 0 && <ChevronIcon />}
                  <button
                    type="button"
                    onClick={() => loadFiles(crumb.value)}
                    disabled={index === breadcrumbs.length - 1}
                    className={`max-w-[12rem] truncate rounded px-1.5 py-0.5 text-sm font-medium transition ${
                      index === breadcrumbs.length - 1
                        ? 'cursor-default text-white'
                        : 'text-gray-400 hover:bg-gray-700 hover:text-gray-200'
                    }`}
                  >
                    {crumb.label}
                  </button>
                </span>
              ))}
            </nav>
          )}

          <button
            type="button"
            onClick={() => {
              setPathDraft(path)
              setManualPathOpen((open) => !open)
            }}
            title="Aller à un chemin précis"
            aria-label="Aller à un chemin précis"
            aria-pressed={manualPathOpen}
            className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md border transition ${
              manualPathOpen ? 'border-blue-500 bg-blue-600 text-white' : 'border-gray-700 text-gray-300 hover:bg-gray-800'
            }`}
          >
            <EditPathIcon />
          </button>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-3">
          <div className="relative min-w-[10rem] flex-1 sm:max-w-xs">
            <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center">
              <SearchIcon />
            </span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Rechercher..."
              className="w-full rounded-md border border-gray-700 bg-gray-900 py-2 pl-9 pr-3 text-sm text-white outline-none transition placeholder:text-gray-500 focus:border-blue-500"
              aria-label="Rechercher un fichier"
            />
          </div>
          <div className="inline-flex rounded-md border border-gray-700 bg-gray-900/60 p-1" role="group" aria-label="Filtrer l'affichage">
            {[
              ['all', 'Tout'],
              ['folders', 'Dossiers'],
              ['files', 'Fichiers'],
            ].map(([value, label]) => (
              <button
                key={value}
                type="button"
                aria-pressed={filter === value}
                onClick={() => setFilter(value)}
                className={`inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-sm font-medium transition ${
                  filter === value
                    ? 'bg-gradient-to-br from-blue-600 to-cyan-500 text-white shadow-sm shadow-blue-950/30'
                    : 'text-gray-300 hover:bg-gray-700'
                }`}
              >
                <FilterIcon type={value} />
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && <p role="alert" className="rounded-lg border border-red-800 bg-red-950/40 px-3 py-2 text-sm text-red-300">{error}</p>}

      <div className="flex-1 overflow-auto rounded-xl border border-gray-800 bg-gray-800/70">
        {loading ? (
          <FilesSkeleton />
        ) : (
          <div className="min-w-[34rem]">
            {/* En-tête + ligne "dossier parent" figées en haut (sticky) pendant le défilement
                de la liste : avant, il fallait remonter jusqu'à la flèche de la barre d'outils
                pour remonter d'un niveau une fois scrollé dans un dossier bien rempli. */}
            <div className="sticky top-0 z-10 bg-gray-800/95 backdrop-blur">
              <div className="grid grid-cols-[minmax(0,1fr)_8rem_7rem] gap-3 border-b border-gray-700 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
                <span>Nom</span>
                <span>Type</span>
                <span className="text-right">Taille</span>
              </div>
              {path !== '.' && (
                <button
                  type="button"
                  onClick={goUp}
                  className="grid w-full grid-cols-[minmax(0,1fr)_8rem_7rem] gap-3 border-b border-gray-800 px-4 py-3 text-left text-sm text-gray-200 transition hover:bg-gray-700/50"
                >
                  <span className="flex min-w-0 items-center gap-3">
                    <ParentFolderIcon />
                    <span className="font-medium">.. (dossier parent)</span>
                  </span>
                  <span className="text-gray-500">Dossier</span>
                  <span className="text-right text-xs tabular-nums text-gray-500">—</span>
                </button>
              )}
            </div>
            {visibleFiles.length === 0 ? (
              <p className="p-4 text-gray-400">Aucun élément</p>
            ) : visibleFiles.map((file) => {
              const rowContent = (
                <>
                  <span className="flex min-w-0 items-center gap-3">
                    {file.is_dir ? <FolderIcon /> : <FileIcon />}
                    <span className="truncate font-medium">{file.name}</span>
                  </span>
                  <span className={file.is_dir ? 'text-blue-400' : 'text-gray-500'}>{file.is_dir ? 'Dossier' : 'Fichier'}</span>
                  <span className="text-right text-xs tabular-nums text-gray-500">{file.is_dir ? '—' : formatSize(file.size)}</span>
                </>
              )
              // Seuls les dossiers sont des actions (double-clic pour naviguer) : un fichier reste
              // une ligne d'info simple plutôt qu'un <button disabled>, plus propre pour un lecteur
              // d'écran (pas de bouton "désactivé" annoncé sur chaque fichier de la liste).
              return file.is_dir ? (
                <button
                  key={file.path}
                  onDoubleClick={() => loadFiles(file.path)}
                  className="grid w-full grid-cols-[minmax(0,1fr)_8rem_7rem] gap-3 border-b border-gray-800 px-4 py-3 text-left text-sm text-gray-200 transition last:border-b-0 hover:bg-gray-700/50"
                >
                  {rowContent}
                </button>
              ) : (
                <div key={file.path} className="grid w-full grid-cols-[minmax(0,1fr)_8rem_7rem] gap-3 border-b border-gray-800 px-4 py-3 text-sm text-gray-200 last:border-b-0">
                  {rowContent}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </section>
  )
}
