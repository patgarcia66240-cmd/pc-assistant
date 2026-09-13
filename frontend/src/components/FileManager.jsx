import { useEffect, useMemo, useState } from 'react'
import { SkeletonBlock } from './Skeleton'
import Prism from 'prismjs'
import 'prismjs/themes/prism-tomorrow.css'
import 'prismjs/components/prism-clike'
import 'prismjs/components/prism-c'
import 'prismjs/components/prism-csharp'
import 'prismjs/components/prism-cpp'
import 'prismjs/components/prism-python'
import 'prismjs/components/prism-typescript'
import 'prismjs/components/prism-jsx'
import 'prismjs/components/prism-tsx'
import 'prismjs/components/prism-rust'
import 'prismjs/components/prism-json'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const API_URL = '/api/files'

// Association extension de fichier -> langage Prism.js pour la coloration syntaxique.
const EXTENSION_TO_LANGUAGE = {
  '.py': 'python',
  '.js': 'javascript',
  '.jsx': 'jsx',
  '.tsx': 'tsx',
  '.ts': 'typescript',
  '.c': 'c',
  '.h': 'c',
  '.cs': 'csharp',
  '.cpp': 'cpp',
  '.hpp': 'cpp',
  '.rs': 'rust',
  '.json': 'json',
}

marked.setOptions({ breaks: true, gfm: true })

function renderMarkdown(content) {
  try {
    const html = marked.parse(content)
    return DOMPurify.sanitize(html)
  } catch {
    return null
  }
}

function highlightCode(content, extension) {
  const language = EXTENSION_TO_LANGUAGE[(extension || '').toLowerCase()]
  const grammar = language && Prism.languages[language]
  if (!grammar) {
    return null
  }
  try {
    return Prism.highlight(content, grammar, language)
  } catch {
    return null
  }
}

// Petite icone triangle pour l'expand/collapse de l'arbre JSON.
function CaretIcon({ expanded }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className={`h-3 w-3 shrink-0 transition-transform ${expanded ? 'rotate-90' : ''}`}
      aria-hidden="true"
    >
      <path d="M8 5v14l11-7z" />
    </svg>
  )
}

// Noeud de l'arbre JSON collapsible : gere objets, tableaux et valeurs primitives colorees.
function JsonNode({ nodeKey, value, depth }) {
  const isArray = Array.isArray(value)
  const isObject = value !== null && typeof value === 'object' && !isArray
  const isCollapsible = isArray || isObject
  const [expanded, setExpanded] = useState(depth < 2)

  const keyLabel = nodeKey !== null ? (
    <span className="text-sky-400">"{nodeKey}"</span>
  ) : null

  if (!isCollapsible) {
    let valueNode
    if (value === null) {
      valueNode = <span className="text-gray-500 italic">null</span>
    } else if (typeof value === 'string') {
      valueNode = <span className="text-emerald-400">"{value}"</span>
    } else if (typeof value === 'number') {
      valueNode = <span className="text-amber-400">{String(value)}</span>
    } else if (typeof value === 'boolean') {
      valueNode = <span className="text-purple-400">{String(value)}</span>
    } else {
      valueNode = <span className="text-gray-200">{String(value)}</span>
    }
    return (
      <div className="whitespace-pre">
        {keyLabel && <>{keyLabel}<span className="text-gray-500">: </span></>}
        {valueNode}
      </div>
    )
  }

  const entries = isArray ? value.map((v, i) => [i, v]) : Object.entries(value)
  const openBracket = isArray ? '[' : '{'
  const closeBracket = isArray ? ']' : '}'
  const count = entries.length

  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="inline-flex items-center gap-1 rounded px-0.5 text-left hover:bg-gray-800/60"
      >
        <CaretIcon expanded={expanded} />
        {keyLabel && <>{keyLabel}<span className="text-gray-500">: </span></>}
        <span className="text-gray-400">{openBracket}</span>
        {!expanded && (
          <span className="text-gray-600">
            {' '}{count} {isArray ? (count > 1 ? 'éléments' : 'élément') : (count > 1 ? 'clés' : 'clé')}{' '}
          </span>
        )}
        {!expanded && <span className="text-gray-400">{closeBracket}</span>}
      </button>
      {expanded && (
        <div className="ml-4 border-l border-gray-800 pl-3">
          {entries.map(([k, v]) => (
            <JsonNode key={k} nodeKey={isArray ? null : k} value={v} depth={depth + 1} />
          ))}
          <div className="text-gray-400">{closeBracket}</div>
        </div>
      )}
    </div>
  )
}

// Rendu Word (.docx) : paragraphes avec styles (titres, gras/italique, listes) + tableaux.
function DocxViewer({ document: doc }) {
  if (!doc) return null
  const headingClasses = {
    1: 'text-2xl font-bold text-white mt-4 mb-2',
    2: 'text-xl font-bold text-white mt-4 mb-2',
    3: 'text-lg font-semibold text-white mt-3 mb-1.5',
  }
  return (
    <div className="max-h-[60vh] overflow-auto rounded-lg bg-gray-950 p-6 border border-gray-800 select-text">
      {doc.paragraphs.map((para, i) => {
        if (para.heading > 0) {
          const cls = headingClasses[para.heading] || headingClasses[3]
          return <p key={i} className={cls}>{para.text}</p>
        }
        const textCls = [
          para.bold ? 'font-bold' : '',
          para.italic ? 'italic' : '',
        ].filter(Boolean).join(' ')
        if (para.list) {
          return (
            <p key={i} className={`ml-4 text-sm text-gray-200 leading-relaxed ${textCls}`}>
              <span className="text-gray-500">• </span>{para.text}
            </p>
          )
        }
        return (
          <p key={i} className={`mb-2 text-sm text-gray-200 leading-relaxed ${textCls}`}>{para.text}</p>
        )
      })}
      {doc.tables.map((table, ti) => (
        <div key={ti} className="my-4 overflow-auto">
          <table className="w-full border-collapse text-sm">
            <tbody>
              {table.rows.map((row, ri) => (
                <tr key={ri} className={ri === 0 ? 'bg-gray-800/60 font-medium text-white' : 'text-gray-200'}>
                  {row.map((cell, ci) => (
                    <td key={ci} className="border border-gray-800 px-3 py-1.5">{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {table.truncated && (
            <p className="mt-1 text-xs text-amber-400">Tableau tronqué (trop de lignes).</p>
          )}
        </div>
      ))}
      {doc.truncated && (
        <p className="mt-3 text-xs text-amber-400">Document volumineux, seuls les premiers paragraphes sont affichés.</p>
      )}
      {doc.paragraphs.length === 0 && doc.tables.length === 0 && (
        <p className="text-sm text-gray-500 italic">Document vide ou sans texte extractible.</p>
      )}
    </div>
  )
}

// Rendu Excel (.xlsx) : onglets par feuille + grille de cellules.
function XlsxViewer({ workbook }) {
  const [activeSheet, setActiveSheet] = useState(0)
  if (!workbook || workbook.sheets.length === 0) {
    return <p className="py-8 text-center text-sm text-gray-500 italic">Classeur vide.</p>
  }
  const sheet = workbook.sheets[Math.min(activeSheet, workbook.sheets.length - 1)]
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-950">
      {workbook.sheets.length > 1 && (
        <div className="flex gap-1 overflow-x-auto border-b border-gray-800 p-2">
          {workbook.sheets.map((s, i) => (
            <button
              key={s.name}
              type="button"
              onClick={() => setActiveSheet(i)}
              className={`shrink-0 rounded-md px-3 py-1.5 text-xs font-medium transition ${
                i === activeSheet ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {s.name}
            </button>
          ))}
        </div>
      )}
      <div className="max-h-[55vh] overflow-auto p-2">
        <table className="w-full border-collapse text-xs">
          <tbody>
            {sheet.rows.map((row, ri) => (
              <tr key={ri} className={ri === 0 ? 'bg-gray-800/60 font-medium text-white' : 'text-gray-200'}>
                {row.map((cell, ci) => (
                  <td key={ci} className="border border-gray-800 px-2 py-1 whitespace-nowrap">{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {sheet.rows.length === 0 && (
          <p className="py-6 text-center text-sm text-gray-500 italic">Feuille vide.</p>
        )}
      </div>
      {sheet.truncated && (
        <p className="border-t border-gray-800 px-3 py-1.5 text-xs text-amber-400">
          Feuille tronquée (trop de lignes/colonnes).
        </p>
      )}
    </div>
  )
}

// Rendu PowerPoint (.pptx) : liste des diapositives avec titre, contenu texte et notes.
function PptxViewer({ presentation }) {
  if (!presentation || presentation.slides.length === 0) {
    return <p className="py-8 text-center text-sm text-gray-500 italic">Présentation vide.</p>
  }
  return (
    <div className="max-h-[60vh] overflow-auto space-y-3 pr-1">
      {presentation.slides.map((slide) => (
        <div key={slide.index} className="rounded-lg border border-gray-800 bg-gray-950 p-4">
          <div className="mb-2 flex items-center gap-2">
            <span className="rounded bg-gray-800 px-2 py-0.5 text-xs font-medium text-gray-400">
              Slide {slide.index}
            </span>
            {slide.title && <h3 className="text-base font-semibold text-white">{slide.title}</h3>}
          </div>
          {slide.texts.map((text, ti) => (
            <p key={ti} className="mb-1 whitespace-pre-line text-sm text-gray-200 leading-relaxed">{text}</p>
          ))}
          {slide.notes && (
            <p className="mt-2 border-t border-gray-800 pt-2 text-xs italic text-gray-500">
              Notes : {slide.notes}
            </p>
          )}
        </div>
      ))}
      {presentation.truncated && (
        <p className="text-xs text-amber-400">Présentation volumineuse, seules les premières diapositives sont affichées.</p>
      )}
    </div>
  )
}

// Rendu base de données SQLite (.db/.sqlite) : onglets par table avec colonnes et lignes.
function DbViewer({ database }) {
  const [activeTable, setActiveTable] = useState(0)
  if (!database || database.tables.length === 0) {
    return <p className="py-8 text-center text-sm text-gray-500 italic">Base de données vide (aucune table).</p>
  }
  const table = database.tables[Math.min(activeTable, database.tables.length - 1)]
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-950">
      {database.tables.length > 1 && (
        <div className="flex gap-1 overflow-x-auto border-b border-gray-800 p-2">
          {database.tables.map((t, i) => (
            <button
              key={t.name}
              type="button"
              onClick={() => setActiveTable(i)}
              className={`shrink-0 rounded-md px-3 py-1.5 text-xs font-medium transition ${
                i === activeTable ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {t.name}
            </button>
          ))}
        </div>
      )}
      <div className="flex items-center justify-between border-b border-gray-800 px-3 py-1.5">
        <span className="text-xs font-medium text-gray-400">{table.row_count} ligne(s)</span>
      </div>
      <div className="max-h-[55vh] overflow-auto p-2">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr className="bg-gray-800/60 font-medium text-white">
              {table.columns.map((col, ci) => (
                <th key={ci} className="border border-gray-800 px-2 py-1 text-left whitespace-nowrap">{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, ri) => (
              <tr key={ri} className="text-gray-200">
                {row.map((cell, ci) => (
                  <td key={ci} className="border border-gray-800 px-2 py-1 whitespace-nowrap">{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {table.rows.length === 0 && (
          <p className="py-6 text-center text-sm text-gray-500 italic">Table vide.</p>
        )}
      </div>
      {table.truncated && (
        <p className="border-t border-gray-800 px-3 py-1.5 text-xs text-amber-400">
          Table tronquée (trop de lignes, aperçu limité).
        </p>
      )}
    </div>
  )
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5" aria-hidden="true">
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  )
}

function DownloadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4" aria-hidden="true">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
    </svg>
  )
}

function EyeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4" aria-hidden="true">
      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

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

function FilePreviewModal({ file, onClose }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [previewData, setPreviewData] = useState(null)

  useEffect(() => {
    if (!file) return
    let isCancelled = false
    setLoading(true)
    setError('')

    fetch(`${API_URL}/content?path=${encodeURIComponent(file.path)}`)
      .then(async (res) => {
        const data = await res.json()
        if (!res.ok) throw new Error(data.detail || 'Impossible de charger le fichier')
        return data
      })
      .then((data) => {
        if (!isCancelled) {
          setPreviewData(data)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!isCancelled) {
          setError(err.message)
          setLoading(false)
        }
      })

    return () => {
      isCancelled = true
    }
  }, [file])

  if (!file) return null

  const rawUrl = `${API_URL}/raw?path=${encodeURIComponent(file.path)}`
  const downloadUrl = `${API_URL}/raw?path=${encodeURIComponent(file.path)}&download=true`

  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex h-64 flex-col items-center justify-center gap-3 text-gray-400">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          <p className="text-sm">Chargement de l'aperçu...</p>
        </div>
      )
    }

    if (error) {
      return (
        <div className="flex h-48 flex-col items-center justify-center gap-3 text-center">
          <p className="text-sm text-red-400">{error}</p>
          <a
            href={downloadUrl}
            className="inline-flex items-center gap-2 rounded-md bg-gray-800 px-3 py-2 text-sm font-medium text-white transition hover:bg-gray-700"
          >
            <DownloadIcon />
            Télécharger quand même
          </a>
        </div>
      )
    }

    const type = previewData?.type || 'binary'

    if (type === 'image') {
      return (
        <div className="flex max-h-[70vh] items-center justify-center overflow-auto rounded-lg bg-black/40 p-4">
          <img
            src={rawUrl}
            alt={file.name}
            className="max-h-[60vh] max-w-full rounded object-contain shadow-lg"
          />
        </div>
      )
    }

    if (type === 'audio') {
      return (
        <div className="flex flex-col items-center justify-center gap-4 py-12">
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-blue-950/40 text-blue-400">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-10 w-10">
              <path d="M9 18V5l12-2v13" />
              <circle cx="6" cy="18" r="3" />
              <circle cx="18" cy="16" r="3" />
            </svg>
          </div>
          <p className="text-sm font-medium text-gray-200">{file.name}</p>
          <audio controls className="w-full max-w-md" src={rawUrl}>
            Votre navigateur ne supporte pas la lecture audio.
          </audio>
        </div>
      )
    }

    if (type === 'video') {
      return (
        <div className="flex max-h-[70vh] items-center justify-center overflow-hidden rounded-lg bg-black/50 p-2">
          <video controls className="max-h-[60vh] max-w-full rounded shadow-lg" src={rawUrl}>
            Votre navigateur ne supporte pas la lecture vidéo.
          </video>
        </div>
      )
    }

    if (type === 'docx') {
      return <DocxViewer document={previewData?.document} />
    }

    if (type === 'xlsx') {
      return <XlsxViewer workbook={previewData?.workbook} />
    }

    if (type === 'pptx') {
      return <PptxViewer presentation={previewData?.presentation} />
    }

    if (type === 'db') {
      return <DbViewer database={previewData?.database} />
    }

    if (type === 'pdf') {
      return (
        <div className="h-[65vh] w-full overflow-hidden rounded-lg bg-gray-900 border border-gray-800">
          <iframe
            src={rawUrl}
            title={file.name}
            className="h-full w-full border-0"
          />
        </div>
      )
    }

    if (type === 'text' && previewData?.extension === '.json' && previewData?.content !== null) {
      let parsed
      let parseError = false
      try {
        parsed = JSON.parse(previewData.content)
      } catch {
        parseError = true
      }
      if (!parseError) {
        return (
          <div className="relative">
            {previewData?.truncated && (
              <div className="mb-2 rounded bg-amber-950/40 border border-amber-800/60 px-3 py-1.5 text-xs text-amber-300">
                Ce fichier est volumineux, seul le premier mégaoctet est affiché.
              </div>
            )}
            <div className="max-h-[60vh] overflow-auto rounded-lg bg-gray-950 p-4 font-mono text-xs leading-relaxed border border-gray-800 select-text">
              <JsonNode nodeKey={null} value={parsed} depth={0} />
            </div>
          </div>
        )
      }
    }

    if (type === 'text' && previewData?.extension === '.md' && previewData?.content !== null) {
      const html = renderMarkdown(previewData.content)
      if (html !== null) {
        return (
          <div className="relative">
            {previewData?.truncated && (
              <div className="mb-2 rounded bg-amber-950/40 border border-amber-800/60 px-3 py-1.5 text-xs text-amber-300">
                Ce fichier est volumineux, seul le premier mégaoctet est affiché.
              </div>
            )}
            <div
              className="markdown-preview max-h-[60vh] overflow-auto rounded-lg bg-gray-950 p-6 border border-gray-800 select-text"
              dangerouslySetInnerHTML={{ __html: html }}
            />
          </div>
        )
      }
    }

    if (type === 'text' && previewData?.content !== null) {
      const highlighted = highlightCode(previewData.content, previewData?.extension)
      return (
        <div className="relative">
          {previewData?.truncated && (
            <div className="mb-2 rounded bg-amber-950/40 border border-amber-800/60 px-3 py-1.5 text-xs text-amber-300">
              Ce fichier est volumineux, seul le premier mégaoctet est affiché.
            </div>
          )}
          <pre className="max-h-[60vh] overflow-auto rounded-lg bg-gray-950 p-4 font-mono text-xs leading-relaxed border border-gray-800 select-text whitespace-pre-wrap break-words">
            {highlighted ? (
              <code
                className={`language-${EXTENSION_TO_LANGUAGE[(previewData?.extension || '').toLowerCase()]}`}
                dangerouslySetInnerHTML={{ __html: highlighted }}
              />
            ) : (
              <code className="text-gray-200">{previewData?.content}</code>
            )}
          </pre>
        </div>
      )
    }

    // Binary / non géré directement
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-12 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gray-800 text-gray-400">
          <FileIcon />
        </div>
        <div>
          <p className="text-base font-medium text-white">{file.name}</p>
          <p className="mt-1 text-sm text-gray-400">
            Aperçu direct non disponible pour ce type de fichier ({formatSize(file.size)})
          </p>
        </div>
        <a
          href={downloadUrl}
          className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500 px-4 py-2.5 text-sm font-medium text-white shadow-lg shadow-blue-950/40 transition hover:opacity-90"
        >
          <DownloadIcon />
          Télécharger le fichier
        </a>
      </div>
    )
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label={`Aperçu de ${file.name}`}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="flex max-h-[90vh] w-full max-w-4xl flex-col rounded-2xl border border-gray-700 bg-gray-900 shadow-2xl">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-gray-800 px-5 py-3.5">
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-950/50 text-blue-400">
              <FileIcon />
            </span>
            <div className="min-w-0">
              <h3 className="truncate text-base font-semibold text-white">{file.name}</h3>
              <p className="text-xs text-gray-400">{formatSize(file.size)} &bull; {file.path}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={downloadUrl}
              download={file.name}
              title="Télécharger"
              aria-label="Télécharger"
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-gray-700 bg-gray-800 px-3 text-xs font-medium text-gray-200 transition hover:bg-gray-700 hover:text-white"
            >
              <DownloadIcon />
              <span className="hidden sm:inline">Télécharger</span>
            </a>
            <button
              onClick={onClose}
              title="Fermer"
              aria-label="Fermer"
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-gray-700 text-gray-400 transition hover:bg-gray-800 hover:text-white"
            >
              <CloseIcon />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-auto p-5">
          {renderContent()}
        </div>
      </div>
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

// Convertit un motif type "glob" (ex: "*.csv", "rapport_?.xlsx") en RegExp insensible à la
// casse. `*` = n'importe quelle suite de caractères, `?` = un seul caractère. Les autres
// caractères spéciaux regex sont échappés pour rester un simple filtre de nom de fichier.
function globToRegExp(pattern) {
  const escaped = pattern.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.')
  return new RegExp(`^${escaped}$`, 'i')
}

export default function FileManager() {
  const [path, setPath] = useState('.')
  const [files, setFiles] = useState([])
  const [locations, setLocations] = useState([])
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selectedFileForPreview, setSelectedFileForPreview] = useState(null)
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
    const isGlob = /[*?]/.test(normalizedSearch)
    const globRegExp = isGlob ? globToRegExp(normalizedSearch) : null
    return files
      .filter((file) => filter === 'all' || (filter === 'folders' ? file.is_dir : !file.is_dir))
      .filter((file) => {
        if (!normalizedSearch) return true
        const name = file.name.toLowerCase()
        return isGlob ? globRegExp.test(name) : name.includes(normalizedSearch)
      })
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
              placeholder="Rechercher... (ex. *.csv)"
              className="w-full rounded-md border border-gray-700 bg-gray-900 py-2 pl-9 pr-3 text-sm text-white outline-none transition placeholder:text-gray-500 focus:border-blue-500"
              aria-label="Rechercher un fichier (nom ou motif type *.csv)"
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
                  className="grid w-full grid-cols-[minmax(0,1fr)_8rem_7rem] gap-3 border-b border-gray-800 px-4 py-3 text-left text-sm text-gray-200 transition last:border-b-0 hover:bg-gray-700/50 cursor-pointer"
                >
                  {rowContent}
                </button>
              ) : (
                <div
                  key={file.path}
                  onClick={() => setSelectedFileForPreview(file)}
                  className="grid w-full grid-cols-[minmax(0,1fr)_8rem_7rem] gap-3 border-b border-gray-800 px-4 py-3 text-sm text-gray-200 last:border-b-0 hover:bg-gray-800/80 cursor-pointer transition"
                  title="Cliquer pour prévisualiser"
                >
                  {rowContent}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {selectedFileForPreview && (
        <FilePreviewModal
          file={selectedFileForPreview}
          onClose={() => setSelectedFileForPreview(null)}
        />
      )}
    </section>
  )
}
