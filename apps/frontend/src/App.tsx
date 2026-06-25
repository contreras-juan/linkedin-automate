import { type ReactNode, useState } from 'react'
import { generatePost, regeneratePost } from './services/api'

function App() {
  const [formState, setFormState] = useState({
    instructions:
      'Professional but approachable tone. Target audience: AI builders, founders, and product leaders.',
    categories: 'cs.CL, cs.AI, cs.LG',
    interests:
      'large language models for practical automation\nAI agents and autonomous workflows\nretrieval augmented generation and semantic search',
    minScore: 0.18,
    maxResults: 15,
    maxCuratedResults: 5,
    contentType: 'linkedin_post',
    contentFocus: 'Practical AI automation for technical leaders',
  })
  const [draft, setDraft] = useState(
    'Your generated LinkedIn draft will appear here after the agents finish researching, curating, writing, and reviewing the post.',
  )
  const [currentTitle, setCurrentTitle] = useState('Generated LinkedIn draft')
  const [currentPostId, setCurrentPostId] = useState<number | null>(null)
  const [regenerationInstructions, setRegenerationInstructions] = useState(
    'Make it more concise and emphasize the practical takeaway.',
  )
  const [isLoading, setIsLoading] = useState(false)
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleGeneratePost() {
    setIsLoading(true)
    setError(null)

    try {
      const response = await generatePost({
        instructions: formState.instructions,
        categories: parseCommaList(formState.categories),
        interests: parseLineList(formState.interests),
        min_score: formState.minScore,
        max_results: formState.maxResults,
        max_curated_results: formState.maxCuratedResults,
        content_type: formState.contentType,
        content_focus: formState.contentFocus,
      })
      setDraft(response.draft)
      setCurrentTitle(response.title)
      setCurrentPostId(response.post_id)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to generate the post. Please try again.',
      )
    } finally {
      setIsLoading(false)
    }
  }

  async function handleRegeneratePost() {
    setIsRegenerating(true)
    setError(null)

    try {
      const response = await regeneratePost({
        draft,
        instructions: regenerationInstructions,
        title: currentTitle,
        content_type: formState.contentType,
        content_focus: formState.contentFocus,
        post_id: currentPostId,
      })
      setDraft(response.draft)
      setCurrentTitle(response.title)
      setCurrentPostId(response.post_id)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to regenerate the post. Please try again.',
      )
    } finally {
      setIsRegenerating(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-6 text-slate-100 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="rounded-3xl border border-white/10 bg-white/[0.03] px-6 py-5 shadow-2xl shadow-slate-950/40">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-cyan-300">
            LinkedIn AI Automator
          </p>
          <div className="mt-3 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                Multi-Agent Post Studio
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
                Control the agent workflow from one panel and preview the reviewed
                LinkedIn draft before publishing.
              </p>
            </div>
            <div className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-4 py-2 text-sm font-medium text-emerald-200">
              Backend contract: POST /api/generate
            </div>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <AgentController
            formState={formState}
            isLoading={isLoading}
            error={error}
            onFormStateChange={setFormState}
            onGeneratePost={handleGeneratePost}
          />
          <LinkedInPreview draft={draft} isLoading={isLoading} />
          <RegenerationController
            instructions={regenerationInstructions}
            isRegenerating={isRegenerating}
            isDisabled={isLoading || !draft.trim() || !regenerationInstructions.trim()}
            onInstructionsChange={setRegenerationInstructions}
            onRegeneratePost={handleRegeneratePost}
          />
        </section>
      </div>
    </main>
  )
}

type RegenerationControllerProps = {
  instructions: string
  isRegenerating: boolean
  isDisabled: boolean
  onInstructionsChange: (value: string) => void
  onRegeneratePost: () => void
}

function RegenerationController({
  instructions,
  isRegenerating,
  isDisabled,
  onInstructionsChange,
  onRegeneratePost,
}: RegenerationControllerProps) {
  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.04] p-6 shadow-2xl shadow-slate-950/30 lg:col-start-2">
      <p className="text-sm font-semibold uppercase tracking-[0.25em] text-cyan-300">
        Regenerate Draft
      </p>
      <p className="mt-3 text-sm leading-6 text-slate-300">
        Rewrite the current post without re-running research. Use this for edits like
        “go deeper on X”, “make it shorter”, or “use a more executive tone”.
      </p>
      <textarea
        value={instructions}
        onChange={(event) => onInstructionsChange(event.target.value)}
        className="mt-4 min-h-24 w-full resize-none rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm leading-6 text-slate-100 outline-none focus:border-cyan-300/60 focus:ring-4 focus:ring-cyan-300/10"
        placeholder="Example: deepen the section about agent memory and make the intro shorter..."
      />
      <button
        type="button"
        onClick={onRegeneratePost}
        disabled={isDisabled}
        className="mt-4 inline-flex w-full items-center justify-center gap-3 rounded-2xl border border-cyan-300/30 bg-cyan-300/10 px-5 py-3 text-sm font-bold text-cyan-100 transition hover:bg-cyan-300/20 disabled:cursor-not-allowed disabled:border-slate-700 disabled:bg-slate-800 disabled:text-slate-500"
      >
        {isRegenerating ? <Spinner /> : null}
        {isRegenerating ? 'Regenerating...' : 'Regenerate Current Post'}
      </button>
    </section>
  )
}

type AgentControllerProps = {
  formState: {
    instructions: string
    categories: string
    interests: string
    minScore: number
    maxResults: number
    maxCuratedResults: number
    contentType: string
    contentFocus: string
  }
  isLoading: boolean
  error: string | null
  onFormStateChange: (value: AgentControllerProps['formState']) => void
  onGeneratePost: () => void
}

function AgentController({
  formState,
  isLoading,
  error,
  onFormStateChange,
  onGeneratePost,
}: AgentControllerProps) {
  function updateForm<K extends keyof AgentControllerProps['formState']>(
    key: K,
    value: AgentControllerProps['formState'][K],
  ) {
    onFormStateChange({ ...formState, [key]: value })
  }

  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.04] p-6 shadow-2xl shadow-slate-950/30">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-cyan-300">
            Agent Controller
          </p>
          <h2 className="mt-3 text-2xl font-semibold text-white">
            Content Instructions
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            Configure research topics, semantic criteria, and generation style
            before running the multi-agent workflow.
          </p>
        </div>
        <div className="rounded-2xl border border-cyan-300/20 bg-cyan-300/10 px-3 py-2 text-xs font-medium text-cyan-100">
          4 agents
        </div>
      </div>

      <label
        htmlFor="instructions"
        className="mt-8 block text-sm font-medium text-slate-200"
      >
        Content Instructions
      </label>
      <textarea
        id="instructions"
        value={formState.instructions}
        onChange={(event) => updateForm('instructions', event.target.value)}
        className="mt-3 min-h-32 w-full resize-none rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-4 text-sm leading-6 text-slate-100 outline-none ring-0 transition placeholder:text-slate-500 focus:border-cyan-300/60 focus:ring-4 focus:ring-cyan-300/10"
        placeholder="Example: friendly tone, CTO audience, focus on practical AI automation..."
      />

      <div className="mt-5 grid gap-4">
        <Field label="arXiv Categories">
          <input
            value={formState.categories}
            onChange={(event) => updateForm('categories', event.target.value)}
            className="w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none focus:border-cyan-300/60 focus:ring-4 focus:ring-cyan-300/10"
            placeholder="cs.CL, cs.AI, cs.CV"
          />
        </Field>

        <Field label="Topics / Semantic Interests">
          <textarea
            value={formState.interests}
            onChange={(event) => updateForm('interests', event.target.value)}
            className="min-h-32 w-full resize-none rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm leading-6 text-slate-100 outline-none focus:border-cyan-300/60 focus:ring-4 focus:ring-cyan-300/10"
            placeholder="One topic per line: LLM agents, computer vision, robotics..."
          />
        </Field>

        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Min Score">
            <input
              type="number"
              step="0.01"
              min="-1"
              max="1"
              value={formState.minScore}
              onChange={(event) => updateForm('minScore', Number(event.target.value))}
              className="w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none focus:border-cyan-300/60 focus:ring-4 focus:ring-cyan-300/10"
            />
          </Field>
          <Field label="Search Limit">
            <input
              type="number"
              min="1"
              max="50"
              value={formState.maxResults}
              onChange={(event) => updateForm('maxResults', Number(event.target.value))}
              className="w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none focus:border-cyan-300/60 focus:ring-4 focus:ring-cyan-300/10"
            />
          </Field>
          <Field label="Curated Limit">
            <input
              type="number"
              min="1"
              max="20"
              value={formState.maxCuratedResults}
              onChange={(event) =>
                updateForm('maxCuratedResults', Number(event.target.value))
              }
              className="w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none focus:border-cyan-300/60 focus:ring-4 focus:ring-cyan-300/10"
            />
          </Field>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Content Type">
            <select
              value={formState.contentType}
              onChange={(event) => updateForm('contentType', event.target.value)}
              className="w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none focus:border-cyan-300/60 focus:ring-4 focus:ring-cyan-300/10"
            >
              <option value="linkedin_post">LinkedIn post</option>
              <option value="technical_summary">Technical summary</option>
              <option value="founder_insight">Founder insight</option>
              <option value="thread_outline">Thread outline</option>
            </select>
          </Field>
          <Field label="Content Focus">
            <input
              value={formState.contentFocus}
              onChange={(event) => updateForm('contentFocus', event.target.value)}
              className="w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none focus:border-cyan-300/60 focus:ring-4 focus:ring-cyan-300/10"
              placeholder="Only LLMs, agent systems, computer vision..."
            />
          </Field>
        </div>
      </div>

      {error ? (
        <div className="mt-4 rounded-2xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-100">
          {error}
        </div>
      ) : null}

      <button
        type="button"
        onClick={onGeneratePost}
        disabled={
          isLoading ||
          !formState.instructions.trim() ||
          parseLineList(formState.interests).length === 0 ||
          parseCommaList(formState.categories).length === 0
        }
        className="mt-6 inline-flex w-full items-center justify-center gap-3 rounded-2xl bg-cyan-300 px-5 py-4 text-sm font-bold text-slate-950 shadow-lg shadow-cyan-300/20 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:bg-slate-600 disabled:text-slate-300 disabled:shadow-none"
      >
        {isLoading ? <Spinner /> : null}
        {isLoading ? 'Generating...' : 'Generate Post'}
      </button>

      <div className="mt-6 grid gap-3 text-sm text-slate-300">
        {['Researcher', 'Curator', 'Writer', 'Reviewer'].map((agent) => (
          <div
            key={agent}
            className="flex items-center justify-between rounded-2xl border border-white/10 bg-slate-900/50 px-4 py-3"
          >
            <span>{agent} Agent</span>
            <span className="text-xs font-medium text-emerald-300">Ready</span>
          </div>
        ))}
      </div>
    </section>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-200">{label}</span>
      {children}
    </label>
  )
}

type LinkedInPreviewProps = {
  draft: string
  isLoading: boolean
}

function LinkedInPreview({ draft, isLoading }: LinkedInPreviewProps) {
  return (
    <section className="rounded-3xl border border-white/10 bg-slate-100 p-4 text-slate-900 shadow-2xl shadow-slate-950/30 sm:p-6">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-slate-500">
            LinkedIn Preview
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-950">
            Reviewed Draft
          </h2>
        </div>
        <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-500 shadow-sm">
          Preview mode
        </span>
      </div>

      <article className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-200/70">
        <div className="p-5">
          <div className="flex items-start gap-3">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-cyan-500 to-blue-700 text-sm font-bold text-white">
              AI
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold leading-tight text-slate-950">
                    LinkedIn AI Automator
                  </h3>
                  <p className="text-xs leading-5 text-slate-500">
                    Multi-Agent Research and Content System
                  </p>
                  <p className="text-xs text-slate-400">Just now • Public</p>
                </div>
                <button
                  type="button"
                  className="rounded-full px-2 py-1 text-xl leading-none text-slate-400 hover:bg-slate-100"
                  aria-label="Post options"
                >
                  ...
                </button>
              </div>
            </div>
          </div>

          <div className="mt-5 min-h-72">
            {isLoading ? <PreviewSkeleton /> : <MarkdownDraft draft={draft} />}
          </div>
        </div>

        <div className="border-t border-slate-100 px-5 py-3">
          <div className="grid grid-cols-3 gap-2 text-sm font-semibold text-slate-500">
            {['Like', 'Comment', 'Share'].map((action) => (
              <button
                key={action}
                type="button"
                className="rounded-xl px-3 py-2 transition hover:bg-slate-100 hover:text-slate-700"
              >
                {action}
              </button>
            ))}
          </div>
        </div>
      </article>
    </section>
  )
}

function MarkdownDraft({ draft }: { draft: string }) {
  return (
    <div className="space-y-3 whitespace-pre-wrap text-[15px] leading-7 text-slate-800">
      {draft}
    </div>
  )
}

function PreviewSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-4 w-11/12 rounded-full bg-slate-200" />
      <div className="h-4 w-10/12 rounded-full bg-slate-200" />
      <div className="h-4 w-full rounded-full bg-slate-200" />
      <div className="h-4 w-8/12 rounded-full bg-slate-200" />
      <div className="mt-8 h-32 rounded-2xl bg-slate-200" />
      <div className="h-4 w-9/12 rounded-full bg-slate-200" />
    </div>
  )
}

function Spinner() {
  return (
    <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-950/30 border-t-slate-950" />
  )
}

function parseCommaList(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function parseLineList(value: string): string[] {
  return value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

export default App
