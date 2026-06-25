import { useState } from 'react'
import { generatePost } from './services/api'

function App() {
  const [instructions, setInstructions] = useState(
    'Professional but approachable tone. Target audience: AI builders, founders, and product leaders.',
  )
  const [draft, setDraft] = useState(
    'Your generated LinkedIn draft will appear here after the agents finish researching, curating, writing, and reviewing the post.',
  )
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleGeneratePost() {
    setIsLoading(true)
    setError(null)

    try {
      const response = await generatePost({ instructions })
      setDraft(response.draft)
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
            instructions={instructions}
            isLoading={isLoading}
            error={error}
            onInstructionsChange={setInstructions}
            onGeneratePost={handleGeneratePost}
          />
          <LinkedInPreview draft={draft} isLoading={isLoading} />
        </section>
      </div>
    </main>
  )
}

type AgentControllerProps = {
  instructions: string
  isLoading: boolean
  error: string | null
  onInstructionsChange: (value: string) => void
  onGeneratePost: () => void
}

function AgentController({
  instructions,
  isLoading,
  error,
  onInstructionsChange,
  onGeneratePost,
}: AgentControllerProps) {
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
            Tell the backend agents how to shape the final LinkedIn post: tone,
            audience, angle, and constraints.
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
        value={instructions}
        onChange={(event) => onInstructionsChange(event.target.value)}
        className="mt-3 min-h-56 w-full resize-none rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-4 text-sm leading-6 text-slate-100 outline-none ring-0 transition placeholder:text-slate-500 focus:border-cyan-300/60 focus:ring-4 focus:ring-cyan-300/10"
        placeholder="Example: friendly tone, CTO audience, focus on practical AI automation..."
      />

      {error ? (
        <div className="mt-4 rounded-2xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-100">
          {error}
        </div>
      ) : null}

      <button
        type="button"
        onClick={onGeneratePost}
        disabled={isLoading || !instructions.trim()}
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

export default App
