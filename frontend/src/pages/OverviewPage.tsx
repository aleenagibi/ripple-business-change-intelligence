import { useMemo } from 'react'

interface Document {
  id: string
  organization_id: string
  filename: string
  document_type: string
  mime_type: string
  processing_status: string
  created_at: string
}

interface Organization {
  id: string
  name: string
  slug: string
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

interface OverviewPageProps {
  organization: Organization
  documents: Document[]
  results: ImpactResult[]
  error: string | null
  onUploadDocument: () => void
  onOpenImpactAnalysis: () => void
}

function OverviewPage({
  organization,
  documents,
  results,
  error,
  onUploadDocument,
  onOpenImpactAnalysis,
}: OverviewPageProps) {
  const processedCount = useMemo(
    () =>
      documents.filter(
        (document) =>
          document.processing_status.toLowerCase() === 'completed',
      ).length,
    [documents],
  )

  const pendingCount = useMemo(
    () =>
      documents.filter((document) =>
        ['pending', 'processing'].includes(
          document.processing_status.toLowerCase(),
        ),
      ).length,
    [documents],
  )

  const failedCount = useMemo(
    () =>
      documents.filter(
        (document) =>
          document.processing_status.toLowerCase() === 'failed',
      ).length,
    [documents],
  )

  const topResults = useMemo(() => results.slice(0, 4), [results])

  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Workspace Overview</span>
          <h1>{organization.name}</h1>
          <p>

            Continuous business change intelligence across all organizational assets. Ripple monitors ingested requirements, structural schemas, and live dependencies to project downstream blast radius before deployments occur.

          </p>
        </div>

        <button
          type="button"
          className="primary-button"
          onClick={onUploadDocument}
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
              <div className="empty-icon">
                <img src="/empty-icon.png" alt="Empty" />
              </div>

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
                onClick={onOpenImpactAnalysis}
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
                  : `${Math.round(
                    (processedCount / documents.length) * 100,
                  )}%`}
              </span>
            </div>

            <div>
              <strong>
                {processedCount} of {documents.length} documents processed
              </strong>

              <p>
                Processed documents are indexed into the knowledge graph
                and available to impact analysis queries.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default OverviewPage