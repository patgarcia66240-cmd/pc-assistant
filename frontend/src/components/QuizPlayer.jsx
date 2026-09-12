import { useEffect, useState } from 'react'
import { shuffleQuizQuestions } from '../quizUtils'

const API_URL = '/api/quiz'

function QuizIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-7 w-7" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M9.8 9a2.3 2.3 0 1 1 3.6 1.9c-.9.6-1.4 1-1.4 2.1M12 16.8h.01" />
    </svg>
  )
}

async function readApiResponse(response) {
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || 'Le quiz est indisponible')
  return data
}

export default function QuizPlayer() {
  const [theme, setTheme] = useState('Histoire')
  const [questionType, setQuestionType] = useState('qcm')
  const [difficulty, setDifficulty] = useState('facile')
  const [count, setCount] = useState(5)
  const [catalog, setCatalog] = useState([])
  const [questions, setQuestions] = useState([])
  const [questionIndex, setQuestionIndex] = useState(0)
  const [selectedAnswer, setSelectedAnswer] = useState('')
  const [score, setScore] = useState(0)
  const [loading, setLoading] = useState('')
  const [error, setError] = useState('')

  const currentQuestion = questions[questionIndex]
  const finished = questions.length > 0 && questionIndex >= questions.length

  async function loadCatalog() {
    try {
      const response = await fetch(`${API_URL}/catalog`)
      const data = await readApiResponse(response)
      setCatalog(data.entries)
    } catch (loadError) {
      setError(loadError.message)
    }
  }

  useEffect(() => {
    loadCatalog()
  }, [])

  useEffect(() => {
    if (!selectedAnswer) return undefined
    const timeoutId = window.setTimeout(() => {
      setQuestionIndex((current) => current + 1)
      setSelectedAnswer('')
    }, 2000)
    return () => window.clearTimeout(timeoutId)
  }, [selectedAnswer])

  function startQuiz(nextQuestions) {
    setQuestions(shuffleQuizQuestions(nextQuestions))
    setQuestionIndex(0)
    setSelectedAnswer('')
    setScore(0)
    setError('')
  }

  async function generateQuiz() {
    setLoading('generate')
    setError('')
    try {
      const response = await fetch(`${API_URL}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          theme: theme.trim(),
          question_type: questionType,
          difficulty,
          count,
        }),
      })
      const data = await readApiResponse(response)
      startQuiz(data.questions)
      await loadCatalog()
    } catch (generateError) {
      setError(generateError.message)
    } finally {
      setLoading('')
    }
  }

  async function startNextSeries() {
    setLoading('next')
    setError('')
    try {
      const response = await fetch(`${API_URL}/next`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          theme: theme.trim(),
          question_type: questionType,
          difficulty,
          count,
        }),
      })
      const data = await readApiResponse(response)
      startQuiz(data.questions)
      if (data.source === 'generated') await loadCatalog()
    } catch (nextError) {
      setError(nextError.message)
    } finally {
      setLoading('')
    }
  }

  async function playStoredQuiz() {
    setLoading('play')
    setError('')
    try {
      const params = new URLSearchParams({
        theme: theme.trim(),
        question_type: questionType,
        difficulty,
        count: String(count),
      })
      const response = await fetch(`${API_URL}/play?${params}`)
      const data = await readApiResponse(response)
      startQuiz(data.questions)
    } catch (playError) {
      setError(playError.message)
    } finally {
      setLoading('')
    }
  }

  async function playSavedQuiz(quiz) {
    setLoading(quiz.id)
    setError('')
    try {
      const response = await fetch(`${API_URL}/saved/${encodeURIComponent(quiz.id)}`)
      const data = await readApiResponse(response)
      setTheme(quiz.theme)
      setQuestionType(quiz.question_type)
      setDifficulty(quiz.difficulty)
      setCount(quiz.count)
      startQuiz(data.questions)
    } catch (playError) {
      setError(playError.message)
    } finally {
      setLoading('')
    }
  }

  function answer(choice) {
    if (selectedAnswer) return
    setSelectedAnswer(choice)
    if (choice === currentQuestion.correct_answer) setScore((current) => current + 1)
  }

  if (finished) {
    return (
      <section className="mx-auto max-w-2xl rounded-2xl border border-gray-700 bg-gray-800/80 p-6 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-blue-600/20 text-blue-300"><QuizIcon /></div>
        <h2 className="mt-4 text-2xl font-semibold">Quiz terminé</h2>
        <p className="mt-2 text-lg text-gray-300">Score : <strong className="text-white">{score} / {questions.length}</strong></p>
        <p className="mt-4 text-gray-300">Veux-tu faire une autre série&nbsp;?</p>
        {error && <p className="mt-4 rounded-lg border border-red-800 bg-red-950/40 p-3 text-sm text-red-300">{error}</p>}
        <div className="mt-5 flex flex-wrap justify-center gap-3">
          <button
            type="button"
            onClick={startNextSeries}
            disabled={Boolean(loading)}
            className="min-h-[44px] rounded-lg bg-blue-600 px-5 font-semibold hover:bg-blue-500 disabled:opacity-50"
          >
            {loading === 'next' ? 'Recherche d’une série…' : 'Oui, nouvelle série'}
          </button>
          <button
            type="button"
            onClick={() => startQuiz(questions)}
            disabled={Boolean(loading)}
            className="min-h-[44px] rounded-lg border border-gray-600 px-5 font-semibold text-gray-200 hover:bg-gray-700 disabled:opacity-50"
          >
            Rejouer cette série
          </button>
          <button
            type="button"
            onClick={() => setQuestions([])}
            disabled={Boolean(loading)}
            className="min-h-[44px] rounded-lg border border-gray-600 px-5 text-gray-300 hover:bg-gray-700 disabled:opacity-50"
          >
            Changer de quiz
          </button>
        </div>
      </section>
    )
  }

  if (currentQuestion) {
    return (
      <section className="mx-auto max-w-2xl rounded-2xl border border-gray-700 bg-gray-800/80 p-6">
        <div className="flex items-center justify-between text-sm text-gray-400">
          <span>{currentQuestion.theme} · {currentQuestion.difficulty}</span>
          <span>{questionIndex + 1} / {questions.length}</span>
        </div>
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-gray-700">
          <div className="h-full bg-blue-500 transition-all" style={{ width: `${((questionIndex + 1) / questions.length) * 100}%` }} />
        </div>
        <h2 className="mt-6 text-xl font-semibold leading-8 text-white">{currentQuestion.question}</h2>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {currentQuestion.choices.map((choice) => {
            const correct = selectedAnswer && choice === currentQuestion.correct_answer
            const wrong = selectedAnswer === choice && !correct
            return (
              <button
                key={choice}
                type="button"
                onClick={() => answer(choice)}
                disabled={Boolean(selectedAnswer)}
                className={`min-h-[56px] rounded-xl border px-4 py-3 text-left transition ${
                  correct
                    ? 'border-emerald-500 bg-emerald-950/50 text-emerald-200'
                    : wrong
                      ? 'border-red-500 bg-red-950/50 text-red-200'
                      : 'border-gray-600 bg-gray-900/50 text-gray-200 hover:border-blue-500 hover:bg-gray-700'
                }`}
              >
                {choice}
              </button>
            )
          })}
        </div>
        {selectedAnswer && (
          <div className="mt-5 rounded-xl border border-gray-700 bg-gray-900/50 p-4">
            <p className={selectedAnswer === currentQuestion.correct_answer ? 'text-emerald-300' : 'text-red-300'}>
              {selectedAnswer === currentQuestion.correct_answer ? 'Bonne réponse !' : `Réponse correcte : ${currentQuestion.correct_answer}`}
            </p>
            {currentQuestion.explanation && <p className="mt-2 text-sm text-gray-300">{currentQuestion.explanation}</p>}
            <p className="mt-4 inline-flex min-h-[42px] items-center rounded-lg bg-blue-600/60 px-4 font-semibold text-blue-100">
              {questionIndex + 1 === questions.length ? 'Résultat dans 2 secondes…' : 'Question suivante dans 2 secondes…'}
            </p>
          </div>
        )}
      </section>
    )
  }

  return (
    <section className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl rounded-2xl border border-gray-700 bg-gray-800/80 p-6">
        <div className="flex items-center gap-3 text-blue-300"><QuizIcon /><div><p className="text-xs uppercase tracking-widest">Plugin ARIA</p><h2 className="text-2xl font-semibold text-white">Créer ou rejouer un quiz</h2></div></div>
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <label className="text-sm text-gray-300 sm:col-span-2">
            Thème
            <input value={theme} onChange={(event) => setTheme(event.target.value)} maxLength={80} className="mt-1 block w-full rounded-lg border border-gray-600 bg-gray-900 px-3 py-2 text-white" placeholder="Histoire, sciences, cinéma…" />
          </label>
          <label className="text-sm text-gray-300">
            Type
            <select value={questionType} onChange={(event) => setQuestionType(event.target.value)} className="mt-1 block w-full rounded-lg border border-gray-600 bg-gray-900 px-3 py-2 text-white">
              <option value="qcm">QCM — 4 réponses</option>
              <option value="true_false">Vrai ou Faux</option>
            </select>
          </label>
          <label className="text-sm text-gray-300">
            Difficulté
            <select value={difficulty} onChange={(event) => setDifficulty(event.target.value)} className="mt-1 block w-full rounded-lg border border-gray-600 bg-gray-900 px-3 py-2 text-white">
              <option value="facile">Facile</option>
              <option value="moyen">Moyen</option>
              <option value="difficile">Difficile</option>
            </select>
          </label>
          <label className="text-sm text-gray-300 sm:col-span-2">
            Nombre de questions : <span className="font-semibold text-white">{count}</span>
            <input type="range" min="1" max="20" value={count} onChange={(event) => setCount(Number(event.target.value))} className="mt-2 w-full accent-blue-500" />
          </label>
        </div>
        {error && <p className="mt-4 rounded-lg border border-red-800 bg-red-950/40 p-3 text-sm text-red-300">{error}</p>}
        <div className="mt-6 flex flex-wrap gap-3">
          <button type="button" onClick={playStoredQuiz} disabled={Boolean(loading) || theme.trim().length < 2} className="min-h-[44px] rounded-lg bg-blue-600 px-5 font-semibold hover:bg-blue-500 disabled:opacity-50">
            {loading === 'play' ? 'Chargement…' : 'Jouer les questions stockées'}
          </button>
          <button type="button" onClick={generateQuiz} disabled={Boolean(loading) || theme.trim().length < 2} className="min-h-[44px] rounded-lg border border-blue-500 px-5 font-semibold text-blue-200 hover:bg-blue-950/40 disabled:opacity-50">
            {loading === 'generate' ? 'ARIA génère le quiz…' : 'Générer avec ARIA et enregistrer'}
          </button>
        </div>
      </div>

      <div className="mx-auto mt-5 max-w-3xl rounded-2xl border border-gray-700 bg-gray-800/60 p-5">
        <div className="flex items-center justify-between gap-3">
          <h3 className="font-semibold text-white">Mes quiz sauvegardés</h3>
          <span className="rounded-full bg-blue-500/10 px-3 py-1 text-xs text-blue-200">
            {catalog.length} quiz
          </span>
        </div>
        {catalog.length === 0 ? (
          <p className="mt-2 text-sm text-gray-400">Aucun quiz enregistré pour le moment.</p>
        ) : (
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {catalog.map((entry) => (
              <article key={entry.id} className="rounded-xl border border-gray-700 bg-gray-900/60 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="font-semibold text-white">{entry.theme}</h4>
                    <p className="mt-1 text-xs text-gray-400">
                      {entry.question_type === 'qcm' ? 'QCM' : 'Vrai/Faux'} · {entry.difficulty} · {entry.count} question{entry.count > 1 ? 's' : ''}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">
                      Sauvegardé le {new Date(entry.created_at).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => playSavedQuiz(entry)}
                    disabled={Boolean(loading)}
                    className="min-h-[40px] shrink-0 rounded-lg bg-blue-600 px-4 text-sm font-semibold hover:bg-blue-500 disabled:opacity-50"
                  >
                    {loading === entry.id ? 'Chargement…' : 'Jouer'}
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
