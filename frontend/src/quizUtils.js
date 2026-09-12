function shuffled(items) {
  const result = [...items]
  for (let index = result.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1))
    ;[result[index], result[swapIndex]] = [result[swapIndex], result[index]]
  }
  return result
}

export function shuffleQuizQuestions(questions) {
  return shuffled(questions).map((question) => ({
    ...question,
    choices: shuffled(question.choices),
  }))
}
