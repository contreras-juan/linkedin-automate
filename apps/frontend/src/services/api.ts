const GENERATE_API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/generate'
const REGENERATE_API_URL =
  import.meta.env.VITE_REGENERATE_API_URL ?? 'http://localhost:8000/api/regenerate'

export type GeneratePostRequest = {
  instructions: string
  categories: string[]
  interests: string[]
  min_score: number
  max_results: number
  max_curated_results: number
  content_type: string
  content_focus: string
}

export type GeneratePostResponse = {
  post_id: number | null
  generation_id: number | null
  draft: string
  title: string
  score: number
  approved: boolean
  hashtags: string[]
}

export type RegeneratePostRequest = {
  draft: string
  instructions: string
  title: string
  content_type: string
  content_focus: string
  post_id?: number | null
}

type BackendGenerateResponse = {
  draft?: unknown
  content?: unknown
  post?: unknown
  markdown?: unknown
  title?: unknown
  post_id?: unknown
  generation_id?: unknown
  score?: unknown
  approved?: unknown
  hashtags?: unknown
}

export async function generatePost(
  payload: GeneratePostRequest,
): Promise<GeneratePostResponse> {
  const response = await fetch(GENERATE_API_URL, {
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

  return {
    post_id: typeof data.post_id === 'number' ? data.post_id : null,
    generation_id: typeof data.generation_id === 'number' ? data.generation_id : null,
    draft,
    title: firstString(data.title) ?? 'Generated LinkedIn draft',
    score: typeof data.score === 'number' ? data.score : 0,
    approved: typeof data.approved === 'boolean' ? data.approved : false,
    hashtags: Array.isArray(data.hashtags)
      ? data.hashtags.filter((value): value is string => typeof value === 'string')
      : [],
  }
}

export async function regeneratePost(
  payload: RegeneratePostRequest,
): Promise<GeneratePostResponse> {
  const response = await fetch(REGENERATE_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(`Regenerate request failed with status ${response.status}`)
  }

  const data = (await response.json()) as BackendGenerateResponse
  const draft = firstString(data.draft, data.content, data.post, data.markdown)

  if (!draft) {
    throw new Error('Regenerate response did not include a markdown draft')
  }

  return {
    post_id: typeof data.post_id === 'number' ? data.post_id : null,
    generation_id: typeof data.generation_id === 'number' ? data.generation_id : null,
    draft,
    title: firstString(data.title) ?? payload.title,
    score: typeof data.score === 'number' ? data.score : 0,
    approved: typeof data.approved === 'boolean' ? data.approved : false,
    hashtags: Array.isArray(data.hashtags)
      ? data.hashtags.filter((value): value is string => typeof value === 'string')
      : [],
  }
}

function firstString(...values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) {
      return value
    }
  }

  return null
}
