import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { knowledgeBasesApi } from '../api'
import { useKnowledgeBasesStore } from '../stores/knowledgeBases'

export default function KnowledgeBases() {
  const navigate = useNavigate()
  const bases = useKnowledgeBasesStore((state) => state.bases)
  const isLoading = useKnowledgeBasesStore((state) => state.isLoading)
  const error = useKnowledgeBasesStore((state) => state.error)
  const loadBases = useKnowledgeBasesStore((state) => state.loadBases)
  const refreshBases = useKnowledgeBasesStore((state) => state.refreshBases)

  const [query, setQuery] = useState('')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [isCreating, setIsCreating] = useState(false)

  useEffect(() => {
    loadBases()
  }, [loadBases])

  const [showCreateModal, setShowCreateModal] = useState(false)

  const filtered = useMemo(() => {
    if (!query.trim()) return bases
    const q = query.toLowerCase()
    return bases.filter((kb) => kb.name.toLowerCase().includes(q))
  }, [bases, query])

  const handleCreateClick = () => {
    setShowCreateModal(true)
  }

  const handleCreateSubmit = async () => {
    if (!name.trim()) return
    setIsCreating(true)
    try {
      const created = await knowledgeBasesApi.create({
        name: name.trim(),
        description: description.trim() || undefined,
      })
      setName('')
      setDescription('')
      setShowCreateModal(false)
      await refreshBases()
      navigate(`/knowledge-bases/${created.id}`)
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex h-screen bg-slate-950 text-white overflow-hidden"
    >
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b border-slate-800 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold">Knowledge Bases</h1>
              <p className="text-sm text-slate-400 mt-1">Manage your documents and knowledge sources</p>
            </div>
            <button
              onClick={() => navigate('/')}
              className="px-4 py-2 rounded-lg border border-slate-700 text-sm hover:bg-slate-800 transition-colors"
            >
              Back to Chat
            </button>
          </div>
        </div>

        {/* Toolbar */}
        <div className="border-b border-slate-800 px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex-1 max-w-md">
            <div className="relative">
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search knowledge bases..."
                className="w-full pl-10 pr-4 py-2 rounded-lg border border-slate-700 bg-slate-900/60 text-sm focus:outline-none focus:border-slate-600"
              />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => refreshBases()}
              className="p-2 rounded-lg border border-slate-700 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
              title="Refresh"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
            <button
              onClick={handleCreateClick}
              className="px-4 py-2 rounded-lg bg-blue-600 text-sm font-medium hover:bg-blue-500 transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Knowledge Base
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
            {/* Table Header */}
            <div className="grid grid-cols-12 gap-4 px-6 py-4 text-xs font-medium text-slate-400 border-b border-slate-800 bg-slate-900/60">
              <div className="col-span-5">Knowledge Base</div>
              <div className="col-span-4">Description</div>
              <div className="col-span-2">Last Updated</div>
              <div className="col-span-1 text-right">Actions</div>
            </div>
            
            {/* Table Body */}
            {isLoading ? (
              <div className="flex items-center justify-center py-16">
                <div className="text-sm text-slate-400">Loading knowledge bases...</div>
              </div>
            ) : error ? (
              <div className="flex items-center justify-center py-16">
                <div className="text-sm text-rose-400">{error}</div>
              </div>
            ) : filtered.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 px-6">
                <svg className="w-16 h-16 text-slate-700 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                  />
                </svg>
                <p className="text-sm text-slate-400 mb-1">
                  {query.trim() ? 'No knowledge bases found' : 'No knowledge bases yet'}
                </p>
                <p className="text-xs text-slate-500 mb-4">
                  {query.trim() ? 'Try a different search term' : 'Create your first knowledge base to organize documents'}
                </p>
                {!query.trim() && (
                  <button
                    onClick={handleCreateClick}
                    className="px-4 py-2 rounded-lg bg-blue-600 text-sm font-medium hover:bg-blue-500 transition-colors"
                  >
                    Create Knowledge Base
                  </button>
                )}
              </div>
            ) : (
              filtered.map((kb, index) => (
                <div
                  key={kb.id}
                  className={`grid grid-cols-12 gap-4 px-6 py-4 text-sm hover:bg-slate-900/60 cursor-pointer transition-colors ${
                    index < filtered.length - 1 ? 'border-b border-slate-800/60' : ''
                  }`}
                  onClick={() => navigate(`/knowledge-bases/${kb.id}`)}
                >
                  <div className="col-span-5 flex items-center gap-3 min-w-0">
                    <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                      <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                        />
                      </svg>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="font-medium text-slate-200 truncate">{kb.name}</div>
                      <div className="text-xs text-slate-500 mt-0.5">ID: {kb.id.slice(0, 8)}...</div>
                    </div>
                  </div>
                  <div className="col-span-4 flex items-center text-slate-400 min-w-0">
                    <div className="truncate">{kb.description || 'No description'}</div>
                  </div>
                  <div className="col-span-2 flex items-center text-slate-500">
                    {new Date(kb.updated_at).toLocaleDateString()}
                  </div>
                  <div className="col-span-1 flex items-center justify-end">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        navigate(`/knowledge-bases/${kb.id}`)
                      }}
                      className="px-3 py-1.5 rounded hover:bg-blue-500/10 text-blue-400 text-xs font-medium transition-colors"
                    >
                      Open
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-slate-900 rounded-xl border border-slate-800 p-6 w-full max-w-md"
          >
            <h2 className="text-lg font-semibold mb-4">Create Knowledge Base</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-2">Name *</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="My Documents"
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:outline-none focus:border-slate-600"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-2">Description (optional)</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="A collection of important documents..."
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:outline-none focus:border-slate-600 resize-none"
                  rows={3}
                />
              </div>
            </div>
            <div className="flex items-center gap-3 mt-6">
              <button
                onClick={() => {
                  setShowCreateModal(false)
                  setName('')
                  setDescription('')
                }}
                className="flex-1 px-4 py-2 rounded-lg border border-slate-700 text-sm hover:bg-slate-800 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateSubmit}
                disabled={isCreating || !name.trim()}
                className="flex-1 px-4 py-2 rounded-lg bg-blue-600 text-sm font-medium hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isCreating ? 'Creating...' : 'Create'}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </motion.div>
  )
}
