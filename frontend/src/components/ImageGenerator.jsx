import { useEffect, useState } from 'react'

const API_URL = '/api/images'

function ImageIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-7 w-7" aria-hidden="true">
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <circle cx="9" cy="9" r="2" />
      <path d="m4 17 5-5 3.5 3.5 2.5-2.5 5 5" />
    </svg>
  )
}

async function readApiResponse(response) {
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || 'La génération d’image est indisponible')
  return data
}

export default function ImageGenerator() {
  const [prompt, setPrompt] = useState('')
  const [size, setSize] = useState('1024x1024')
  const [quality, setQuality] = useState('medium')
  const [images, setImages] = useState([])
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function loadPlugin() {
    try {
      const [statusResponse, imagesResponse] = await Promise.all([
        fetch(`${API_URL}/status`),
        fetch(API_URL),
      ])
      const nextStatus = await readApiResponse(statusResponse)
      const gallery = await readApiResponse(imagesResponse)
      setStatus(nextStatus)
      setImages(gallery.images)
    } catch (loadError) {
      setError(loadError.message)
    }
  }

  useEffect(() => {
    loadPlugin()
  }, [])

  async function generateImage(event) {
    event.preventDefault()
    const cleanPrompt = prompt.trim()
    if (!cleanPrompt || loading) return
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${API_URL}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: cleanPrompt, size, quality }),
      })
      const image = await readApiResponse(response)
      setImages((current) => [image, ...current])
    } catch (generateError) {
      setError(generateError.message)
    } finally {
      setLoading(false)
    }
  }

  async function deleteImage(imageId) {
    if (!window.confirm('Supprimer définitivement cette image ?')) return
    setError('')
    try {
      const response = await fetch(`${API_URL}/${encodeURIComponent(imageId)}`, { method: 'DELETE' })
      await readApiResponse(response)
      setImages((current) => current.filter((image) => image.id !== imageId))
    } catch (deleteError) {
      setError(deleteError.message)
    }
  }

  return (
    <section className="h-full overflow-y-auto pr-1">
      <div className="mx-auto max-w-6xl space-y-5 pb-6">
        <header className="rounded-2xl border border-gray-700 bg-gray-800/80 p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-fuchsia-500/15 text-fuchsia-300">
              <ImageIcon />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white">Génération d’images</h2>
              <p className="text-sm text-gray-400">
                {status?.available
                  ? `${status.provider} · ${status.model}`
                  : 'Une clé API OpenAI est nécessaire dans les paramètres.'}
              </p>
            </div>
          </div>

          <form onSubmit={generateImage} className="mt-5">
            <label className="block text-sm font-medium text-gray-200" htmlFor="image-prompt">
              Décris précisément l’image à créer
            </label>
            <textarea
              id="image-prompt"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              rows={4}
              maxLength={4000}
              placeholder="Exemple : un petit robot français dans un bureau futuriste, illustration 3D, lumière douce…"
              className="mt-2 w-full resize-y rounded-xl border border-gray-600 bg-gray-900 p-3 text-white outline-none placeholder:text-gray-500 focus:border-fuchsia-500"
            />
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <label className="text-sm text-gray-300">
                Format
                <select
                  value={size}
                  onChange={(event) => setSize(event.target.value)}
                  className="mt-1 min-h-[42px] w-full rounded-lg border border-gray-600 bg-gray-900 px-3 text-white"
                >
                  <option value="1024x1024">Carré — 1024 × 1024</option>
                  <option value="1536x1024">Paysage — 1536 × 1024</option>
                  <option value="1024x1536">Portrait — 1024 × 1536</option>
                </select>
              </label>
              <label className="text-sm text-gray-300">
                Qualité
                <select
                  value={quality}
                  onChange={(event) => setQuality(event.target.value)}
                  className="mt-1 min-h-[42px] w-full rounded-lg border border-gray-600 bg-gray-900 px-3 text-white"
                >
                  <option value="low">Basse — économique</option>
                  <option value="medium">Moyenne</option>
                  <option value="high">Haute — plus coûteuse</option>
                </select>
              </label>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                type="submit"
                disabled={loading || !prompt.trim() || !status?.available}
                className="min-h-[44px] rounded-lg bg-fuchsia-600 px-5 font-semibold text-white hover:bg-fuchsia-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? 'Création en cours…' : 'Générer l’image'}
              </button>
              <p className="text-xs text-gray-500">La génération utilise des crédits OpenAI et peut prendre quelques secondes.</p>
            </div>
          </form>
          {error && <p className="mt-4 rounded-lg border border-red-800 bg-red-950/40 p-3 text-sm text-red-300">{error}</p>}
        </header>

        <div>
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-400">Galerie locale</h3>
          {images.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-gray-700 p-10 text-center text-gray-500">
              Tes images générées apparaîtront ici.
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {images.map((image) => (
                <article key={image.id} className="overflow-hidden rounded-2xl border border-gray-700 bg-gray-800">
                  <img src={image.url} alt={image.prompt} loading="lazy" className="aspect-square w-full bg-gray-900 object-cover" />
                  <div className="p-4">
                    <p className="line-clamp-3 text-sm text-gray-200">{image.prompt}</p>
                    <p className="mt-2 text-xs text-gray-500">{image.size} · qualité {image.quality}</p>
                    <div className="mt-3 flex gap-2">
                      <a
                        href={image.download_url}
                        download
                        className="flex min-h-[40px] flex-1 items-center justify-center rounded-lg bg-blue-600 px-3 text-sm font-medium text-white hover:bg-blue-500"
                      >
                        Télécharger
                      </a>
                      <button
                        type="button"
                        onClick={() => deleteImage(image.id)}
                        className="min-h-[40px] rounded-lg border border-red-800 px-3 text-sm text-red-300 hover:bg-red-950/40"
                      >
                        Supprimer
                      </button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
