const API_URL = 'http://localhost:8000/api/generate'

export type GeneratePostRequest = {
  instructions: string
}

export type GeneratePostResponse = {
  draft: string
}

type BackendGenerateResponse = {
  draft?: unknown
  content?: unknown
  post?: unknown
  markdown?: unknown
}

export async function generatePost(
  payload: GeneratePostRequest,
): Promise<GeneratePostResponse> {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(`Generate request failed with status ${response.status}`)
  }

  const data = (await response.json()) as BackendGenerateResponse
  const draft = firstString(data.draft, data.content, data.post, data.markdown)

  if (!draft) {
    throw new Error('Generate response did not include a markdown draft')
  }

  return { draft }
}

function firstString(...values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) {
      return value
    }
  }

  return null
}
