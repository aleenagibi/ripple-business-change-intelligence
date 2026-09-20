import { useEffect, useMemo, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import './App.css'

const API_BASE_URL = 'http://localhost:8000/api'

interface Organization {
  id: string
  name: string
  slug: string
}

interface Document {
  id: string
  organization_id: string
  filename: string
  document_type: string
  mime_type: string
  processing_status: string
  created_at: string
}

interface ImpactResult {
  entity_id: string
  name: string
  entity_type: string
  impact_score: number
  impact_level: string
  semantic_relevance: number
  relationship_strength: number
  graph_proximity: number
  entity_importance: number
  propagation_distance: number
  path: string[]
  explanation: string
}

type Page = 'overview' | 'documents' | 'impact'

const NAV_ITEMS: { id: Page; label: string; icon: React.ReactNode }[] = [
  { id: 'overview', label: 'Overview', icon: <img src="/overview-icon.png" alt="Overview" /> },
  { id: 'documents', label: 'Documents', icon: <img src="/doc-icon.png" alt="Documents" /> },
  { id: 'impact', label: 'Impact Analysis', icon: <img src="/insight-icon.png" alt="Impact Analysis" /> },
]

const PAGE_TITLES: Record<Page, string> = {
  overview: 'Overview',
  documents: 'Documents',
  impact: 'Impact Analysis',
}

function fileExtension(filename: string) {
  const parts = filename.split('.')
  if (parts.length < 2) return '?'
  return parts[parts.length - 1].slice(0, 4).toUpperCase()
}

function App() {
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [organization, setOrganization] = useState<Organization | null>(null)

  const [organizationName, setOrganizationName] = useState('')
  const [organizationSlug, setOrganizationSlug] = useState('')

  const [documents, setDocuments] = useState<Document[]>([])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const [query, setQuery] = useState('')
  const [results, setResults] = useState<ImpactResult[]>([])

  const [activePage, setActivePage] = useState<Page>('overview')

  const [loadingOrganization, setLoadingOrganization] = useState(false)
  const [creatingOrganization, setCreatingOrganization] = useState(false)
  const [loadingDocuments, setLoadingDocuments] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)

  const [error, setError] = useState<string | null>(null)

  async function loadDocumentsForOrganization(organizationId: string) {
    setLoadingDocuments(true)
    setError(null)

    try {
      const response = await fetch(
        `${API_BASE_URL}/organizations/${organizationId}/documents`,
      )

      if (!response.ok) {
        throw new Error('Failed to load documents.')
      }

      const data: Document[] = await response.json()
      setDocuments(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents.')
    } finally {
      setLoadingDocuments(false)
    }
  }

  async function createOrganization(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!organizationName.trim() || !organizationSlug.trim()) {
      setError('Organization name and slug are required.')
      return
    }

    setCreatingOrganization(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/organizations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: organizationName.trim(),
          slug: organizationSlug.trim(),
        }),
      })

      if (!response.ok) {
        const body = await response.json().catch(() => null)
        throw new Error(body?.detail ?? 'Failed to create organization.')
      }

      const created: Organization = await response.json()

      setOrganizations((current) => [...current, created])
      setOrganization(created)

      setOrganizationName('')
      setOrganizationSlug('')

      await loadDocumentsForOrganization(created.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create organization.')
    } finally {
      setCreatingOrganization(false)
    }
  }

  async function uploadDocument() {
    if (!organization) {
      setError('Select an organization first.')
      return
    }

    if (!selectedFile) {
      setError('Select a document to upload.')
      return
    }

    setUploading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      const response = await fetch(
        `${API_BASE_URL}/organizations/${organization.id}/documents`,
        { method: 'POST', body: formData },
      )

      if (!response.ok) {
        const body = await response.json().catch(() => null)
        throw new Error(body?.detail ?? 'Failed to upload document.')
      }

      const document: Document = await response.json()

      setDocuments((current) => [document, ...current])
      setSelectedFile(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload document.')
    } finally {
      setUploading(false)
    }
  }

  async function runImpactAnalysis() {
    if (!organization) {
      setError('Select an organization first.')
      return
    }

    if (!query.trim()) {
      setError('Enter a requirement change to analyze.')
      return
    }

    setAnalyzing(true)
    setError(null)
    setResults([])

    try {
      const response = await fetch(
        `${API_BASE_URL}/organizations/${organization.id}/retrieval/impact-analysis`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: query.trim(),
            top_k: 10,
            max_distance: 3,
          }),
        },
      )

      if (!response.ok) {
        const body = await response.json().catch(() => null)
        throw new Error(body?.detail ?? 'Impact analysis failed.')
      }

      const data: ImpactResult[] = await response.json()
      setResults(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impact analysis failed.')
    } finally {
      setAnalyzing(false)
    }
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null
    setSelectedFile(file)
    setError(null)
  }

  function selectOrganization(event: ChangeEvent<HTMLSelectElement>) {
    const selected = organizations.find((item) => item.id === event.target.value)

    setOrganization(selected ?? null)
    setResults([])
    setError(null)

    if (selected) {
      void loadDocumentsForOrganization(selected.id)
    } else {
      setDocuments([])
    }
  }

  useEffect(() => {
    let cancelled = false

    async function initialize() {
      setLoadingOrganization(true)
      setError(null)

      try {
        const response = await fetch(`${API_BASE_URL}/organizations`)

        if (!response.ok) {
          throw new Error('Failed to load organizations.')
        }

        const data: Organization[] = await response.json()

        if (cancelled) return

        setOrganizations(data)

        if (data.length > 0) {
          setOrganization(data[0])
          setLoadingDocuments(true)

          try {
            const documentsResponse = await fetch(
              `${API_BASE_URL}/organizations/${data[0].id}/documents`,
            )

            if (!documentsResponse.ok) {
              throw new Error('Failed to load documents.')
            }

            const documentsData: Document[] = await documentsResponse.json()

            if (!cancelled) {
              setDocuments(documentsData)
            }
          } finally {
            if (!cancelled) {
              setLoadingDocuments(false)
            }
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load organizations.')
        }
      } finally {
        if (!cancelled) {
          setLoadingOrganization(false)
        }
      }
    }

    void initialize()

    return () => {
      cancelled = true
    }
  }, [])

  const processedCount = useMemo(
    () => documents.filter((d) => d.processing_status.toLowerCase() === 'completed').length,
    [documents],
  )

  const pendingCount = useMemo(
    () =>
      documents.filter((d) =>
        ['pending', 'processing'].includes(d.processing_status.toLowerCase()),
      ).length,
    [documents],
  )

  const failedCount = useMemo(
    () => documents.filter((d) => d.processing_status.toLowerCase() === 'failed').length,
    [documents],
  )

  const topResults = useMemo(() => results.slice(0, 4), [results])

  // ---------------------------------------------------------------------
  // Loading / empty-organization states
  // ---------------------------------------------------------------------

  if (loadingOrganization) {
    return (
      <div className="app-loading">
        <div className="loading-mark">R</div>
        <p>Loading Ripple...</p>
      </div>
    )
  }

  if (!organization) {
    return (
      <div className="organization-empty">
        <div className="empty-card">
          <div className="brand-mark"><img src="/logo.png" alt="Ripple" /></div>
          <h1>Welcome to Ripple</h1>
          <p>
            Create an organization workspace to start uploading documents and
            running semantic business impact analysis.
          </p>

          {error && <div className="error-banner">{error}</div>}

          <form
            className="flex flex-col gap-2 text-left"
            onSubmit={createOrganization}
          >
            <input
              type="text"
              placeholder="Organization name"
              value={organizationName}
              onChange={(event) => setOrganizationName(event.target.value)}
              className="h-10 rounded-lg border border-zinc-700 bg-zinc-900 px-3 text-sm text-zinc-100 outline-none focus:border-violet-500"
            />

            <input
              type="text"
              placeholder="organization-slug"
              value={organizationSlug}
              onChange={(event) => setOrganizationSlug(event.target.value)}
              className="h-10 rounded-lg border border-zinc-700 bg-zinc-900 px-3 text-sm text-zinc-100 outline-none focus:border-violet-500"
            />

            <button
              type="submit"
              className="primary-button justify-center"
              disabled={creatingOrganization}
            >
              {creatingOrganization ? 'Creating...' : 'Create organization'}
            </button>
          </form>
        </div>
      </div>
    )
  }

  // ---------------------------------------------------------------------
  // Main app shell
  // ---------------------------------------------------------------------

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="brand">
            <div className="brand-mark"><img src="/logo.png" alt="Ripple" /></div>
            <div>
              <div className="brand-name">Ripple</div>
              <div className="brand-subtitle">Business Impact Analysis</div>
            </div>
          </div>
        </div>

        <div className="organization-selector">
          <span className="section-label">Organization</span>

          <select
            id="organization"
            value={organization.id}
            onChange={selectOrganization}
            disabled={loadingOrganization || organizations.length === 0}
          >
            {organizations.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </div>

        <nav className="navigation">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`nav-item${activePage === item.id ? ' active' : ''}`}
              onClick={() => setActivePage(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="system-status">
            <span className="status-dot" />
            API connected
          </div>
        </div>
      </aside>

      <div className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            {organization.name}
            <span className="breadcrumb-separator">/</span>
            <span className="breadcrumb-current">{PAGE_TITLES[activePage]}</span>
          </div>

          <div className="topbar-right">
            <div className="environment-badge">
              <span className="status-dot" />
              Local
            </div>

            <div className="avatar">{organization.slug.slice(0, 2).toUpperCase()}</div>
          </div>
        </header>

        {activePage === 'overview' && (
          <div className="page">
            <div className="page-heading">
              <div>
                <span className="eyebrow">Workspace</span>
                <h1>{organization.name}</h1>
                <p>
                  A snapshot of what Ripple knows about this organization, from
                  ingested documents to the most recent impact analysis.
                </p>
              </div>

              <button
                type="button"
                className="primary-button"
                onClick={() => setActivePage('documents')}
              >
                Upload document
              </button>
            </div>

            {error && <div className="error-banner">{error}</div>}

            <div className="metric-grid">
              <div className="metric-card">
                <span className="metric-label">Documents</span>
                <span className="metric-value">{documents.length}</span>
                <span className="metric-detail">total uploaded</span>
              </div>

              <div className="metric-card">
                <span className="metric-label">Processed</span>
                <span className="metric-value">{processedCount}</span>
                <span className="metric-detail">ready for retrieval</span>
              </div>

              <div className="metric-card">
                <span className="metric-label">Pending</span>
                <span className="metric-value">{pendingCount}</span>
                <span className="metric-detail">
                  {failedCount > 0 ? `${failedCount} failed` : 'in progress'}
                </span>
              </div>

              <div className="metric-card">
                <span className="metric-label">Entities found</span>
                <span className="metric-value">{results.length}</span>
                <span className="metric-detail">last analysis run</span>
              </div>
            </div>

            <div className="overview-grid">
              <div className="panel">
                <div className="panel-header">
                  <div>
                    <h2>Latest impact analysis</h2>
                    <p>Top affected entities from your most recent query.</p>
                  </div>
                </div>

                {topResults.length === 0 ? (
                  <div className="empty-state">
                    <div className="empty-icon"><img src="/empty-icon.png" alt="Empty" /> </div>
                    <h3>No analysis yet</h3>
                    <p>
                      Run an impact analysis to see which entities are affected
                      by a proposed change.
                    </p>
                  </div>
                ) : (
                  topResults.map((result) => (
                    <button
                      type="button"
                      className="impact-entry"
                      key={result.entity_id}
                      onClick={() => setActivePage('impact')}
                    >
                      <div className="impact-entry-icon">◈</div>
                      <div>
                        <strong>{result.name}</strong>
                        <span>{result.explanation}</span>
                      </div>
                      <span className="entry-arrow">→</span>
                    </button>
                  ))
                )}
              </div>

              <div className="panel">
                <div className="panel-header">
                  <div>
                    <h2>Knowledge graph coverage</h2>
                    <p>How much of your workspace is analysis-ready.</p>
                  </div>
                </div>

                <div className="coverage-placeholder">
                  <div className="coverage-ring">
                    <span>
                      {documents.length === 0
                        ? '0%'
                        : `${Math.round((processedCount / documents.length) * 100)}%`}
                    </span>
                  </div>

                  <div>
                    <strong>{processedCount} of {documents.length} documents processed</strong>
                    <p>
                      Processed documents are indexed into the knowledge graph
                      and available to impact analysis queries.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activePage === 'documents' && (
          <div className="page">
            <div className="page-heading compact">
              <div>
                <span className="eyebrow">Knowledge base</span>
                <h1>Documents</h1>
                <p>Upload the organization's business documents into Ripple.</p>
              </div>

              <label className="primary-button upload-button">
                {uploading ? 'Uploading...' : 'Choose file'}
                <input
                  type="file"
                  onChange={handleFileChange}
                  disabled={!organization || uploading}
                />
              </label>
            </div>

            {error && <div className="error-banner">{error}</div>}

            {selectedFile && (
              <div className="analysis-form-footer" style={{ marginBottom: 18 }}>
                <span>{selectedFile.name}</span>
                <button
                  type="button"
                  className="primary-button"
                  onClick={() => void uploadDocument()}
                  disabled={!organization || uploading}
                >
                  {uploading ? 'Uploading...' : 'Upload document'}
                </button>
              </div>
            )}

            <div className="panel document-panel">
              <div className="panel-header">
                <div>
                  <h2>All documents</h2>
                  <p>{documents.length} uploaded</p>
                </div>
              </div>

              {loadingDocuments ? (
                <div className="empty-state">
                  <div className="empty-icon"><img src="/empty-icon.png" alt="Empty" /></div>
                  <h3>Loading documents...</h3>
                </div>
              ) : documents.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon"><img src="/empty-icon.png" alt="Empty" /></div>
                  <h3>No documents uploaded yet</h3>
                  <p>Choose a file above to start building the knowledge graph.</p>
                </div>
              ) : (
                <div className="document-list">
                  {documents.map((document) => (
                    <div className="document-row" key={document.id}>
                      <div className="document-icon">{fileExtension(document.filename)}</div>

                      <div className="document-info">
                        <strong>{document.filename}</strong>
                        <span>{document.document_type}</span>
                      </div>

                      <div
                        className={`processing-status ${document.processing_status.toLowerCase()}`}
                      >
                        <span className="status-dot" />
                        {document.processing_status}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activePage === 'impact' && (
          <div className="page impact-page">
            <div className="impact-intro">
              <span className="eyebrow">Business Change Intelligence</span>
              <h1>What will this change impact?</h1>
              <p>
                Describe a proposed requirement change. Ripple combines semantic
                retrieval with the organization's knowledge graph to identify
                potentially affected business entities.
              </p>
            </div>

            <div className="analysis-form">
              <textarea
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Example: The payment gateway will now charge a 2% processing fee."
                rows={5}
                disabled={!organization || analyzing}
              />

              <div className="analysis-form-footer">
                <span>
                  {organization ? `Analyzing ${organization.name}` : 'Select an organization'}
                </span>

                <button
                  type="button"
                  className="primary-button"
                  onClick={() => void runImpactAnalysis()}
                  disabled={!organization || !query.trim() || analyzing}
                >
                  {analyzing ? 'Analyzing...' : 'Analyze impact'}
                </button>
              </div>
            </div>

            {error && <div className="error-banner">{error}</div>}

            {results.length === 0 && (
              <div className="analysis-explanation">
                <div className="analysis-step">
                  <span>01</span>
                  <div>
                    <strong>Semantic retrieval</strong>
                    <p>Your query is embedded and matched against indexed document content.</p>
                  </div>
                </div>

                <div className="analysis-step">
                  <span>02</span>
                  <div>
                    <strong>Graph traversal</strong>
                    <p>
                      Matched entities are expanded through the knowledge graph to
                      surface related, potentially affected entities.
                    </p>
                  </div>
                </div>

                <div className="analysis-step">
                  <span>03</span>
                  <div>
                    <strong>Impact scoring</strong>
                    <p>
                      Each entity is scored on relevance, relationship strength,
                      proximity, and importance to produce a ranked impact list.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {results.length > 0 && (
              <div className="results-section">
                <div className="results-heading">
                  <h2>Impact analysis</h2>
                  <span className="result-count">{results.length} entities</span>
                </div>

                <div className="results-list">
                  {results.map((result) => (
                    <article className="impact-result" key={result.entity_id}>
                      <div className="impact-score">
                        <strong>{(result.impact_score * 100).toFixed(0)}%</strong>
                        <span>Impact</span>
                      </div>

                      <div className="impact-result-main">
                        <div className="result-title-row">
                          <h3>{result.name}</h3>
                          <span className="entity-type">{result.entity_type}</span>
                          <span
                            className={`impact-level ${result.impact_level.toLowerCase()}`}
                          >
                            {result.impact_level}
                          </span>
                        </div>

                        <p>{result.explanation}</p>

                        <div className="result-factors">
                          <div className="factor">
                            <span>Relevance</span>
                            <strong>{(result.semantic_relevance * 100).toFixed(0)}%</strong>
                          </div>

                          <div className="factor">
                            <span>Relationship</span>
                            <strong>{(result.relationship_strength * 100).toFixed(0)}%</strong>
                          </div>

                          <div className="factor">
                            <span>Proximity</span>
                            <strong>{(result.graph_proximity * 100).toFixed(0)}%</strong>
                          </div>

                          <div className="factor">
                            <span>Importance</span>
                            <strong>{(result.entity_importance * 100).toFixed(0)}%</strong>
                          </div>

                          <span className="propagation-distance">
                            {result.propagation_distance} hop{result.propagation_distance === 1 ? '' : 's'} away
                          </span>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default App