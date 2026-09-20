import type { ChangeEvent } from 'react'
import { useMemo, useState } from 'react'
import ReactFlow, {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  type Edge,
  type Node,
  type NodeProps,
} from 'reactflow'
import 'reactflow/dist/style.css'

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

interface ImpactAnalysisPageProps {
  organization: Organization
  query: string
  results: ImpactResult[]
  analyzing: boolean
  error: string | null
  onQueryChange: (
    event: ChangeEvent<HTMLTextAreaElement>,
  ) => void
  onAnalyze: () => void
}

type ViewMode = 'cascade' | 'list'

type SortMode =
  | 'risk'
  | 'relevance'
  | 'proximity'

interface ExampleQuery {
  label: string
  query: string
}

interface CascadeNodeData {
  kind: 'root' | 'entity'
  result?: ImpactResult
  query?: string
  selected?: boolean
  onSelect?: (entityId: string) => void
}

const EXAMPLE_QUERIES: ExampleQuery[] = [
  {
    label: 'Threshold 15m → 5m',
    query:
      'If we change the rate-freshness threshold in RDP-002 from 15 minutes to 5 minutes, which documents and systems need updating?',
  },
  {
    label: 'Token v1 → JWT Bearer',
    query:
      'If the CarrierConnect API changes authentication from Token v1 to JWT Bearer, which APIs, documentation, and workflows are affected?',
  },
  {
    label: 'RATE-409 hold window',
    query:
      'Change the RATE-409 held quote resolution window from 4 business hours to 1 business hour.',
  },
]

function formatPercent(value: number) {
  return `${(value * 100).toFixed(0)}%`
}

function getImpactClass(level: string) {
  const normalized = level.toLowerCase()

  if (
    normalized === 'critical' ||
    normalized === 'high'
  ) {
    return 'critical'
  }

  if (
    normalized === 'medium' ||
    normalized === 'moderate'
  ) {
    return 'medium'
  }

  return 'low'
}

function getEntityInitials(name: string) {
  const words = name
    .trim()
    .split(/\s+/)
    .filter(Boolean)

  if (words.length === 0) {
    return '?'
  }

  if (words.length === 1) {
    return words[0]
      .slice(0, 2)
      .toUpperCase()
  }

  return `${words[0][0]}${words[1][0]}`.toUpperCase()
}

function CascadeEntityNode({
  data,
}: NodeProps<CascadeNodeData>) {
  const result = data.result

  if (!result) {
    return null
  }

  const impactClass = getImpactClass(
    result.impact_level,
  )

  return (
    <div
      className={`ripple-cascade-entity-node ${impactClass}${data.selected ? ' selected' : ''
        }`}
      onClick={() =>
        data.onSelect?.(result.entity_id)
      }
    >
      <Handle
        type="target"
        position={Position.Left}
        className="ripple-cascade-handle"
      />

      <div className="ripple-cascade-node-top">
        <span className="ripple-cascade-node-icon">
          {getEntityInitials(result.name)}
        </span>

        <span
          className={`ripple-cascade-severity ${impactClass}`}
        >
          {result.impact_level}
        </span>

        <strong>
          {formatPercent(result.impact_score)}
        </strong>
      </div>

      <div className="ripple-cascade-node-name">
        {result.name}
      </div>

      <div className="ripple-cascade-node-type">
        {result.entity_type}
      </div>

      <p className="ripple-cascade-node-explanation">
        {result.explanation}
      </p>

      <div className="ripple-cascade-node-footer">
        <span>
          {result.propagation_distance === 0
            ? 'Direct impact'
            : `${result.propagation_distance}${result.propagation_distance === 1
              ? 'st'
              : result.propagation_distance === 2
                ? 'nd'
                : result.propagation_distance === 3
                  ? 'rd'
                  : 'th'
            } hop`}
        </span>

        <span>
          {result.path.length > 1
            ? `${result.path.length} path nodes`
            : 'Semantic match'}
        </span>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="ripple-cascade-handle"
      />
    </div>
  )
}

function CascadeRootNode({
  data,
}: NodeProps<CascadeNodeData>) {
  return (
    <div className="ripple-cascade-root-node">
      <Handle
        type="source"
        position={Position.Right}
        className="ripple-cascade-root-handle"
      />

      <span className="ripple-cascade-root-label">
        QUERY ORIGIN
      </span>

      <strong>
        {data.query || 'Proposed business change'}
      </strong>

      <span className="ripple-cascade-root-description">
        Ripple is tracing the semantic and
        graph relationships affected by this
        change.
      </span>

      <div className="ripple-cascade-root-footer">
        <span>Scope: Full topology</span>
        <span>Origin</span>
      </div>
    </div>
  )
}

const cascadeNodeTypes = {
  cascadeEntity: CascadeEntityNode,
  cascadeRoot: CascadeRootNode,
}

function getNodeId(result: ImpactResult) {
  return `entity-${result.entity_id}`
}

function getResultImpactColor(
  result: ImpactResult,
) {
  const impactClass = getImpactClass(
    result.impact_level,
  )

  if (impactClass === 'critical') {
    return '#d71945'
  }

  if (impactClass === 'medium') {
    return '#f59e0b'
  }

  return '#059669'
}

function buildCascadeGraph(
  results: ImpactResult[],
  query: string,
  selectedResultId: string | null,
  onSelect: (entityId: string) => void,
): {
  nodes: Node<CascadeNodeData>[]
  edges: Edge[]
} {
  const resultsByName = new Map(
    results.map((result) => [
      result.name.trim().toLowerCase(),
      result,
    ]),
  )

  const resultsById = new Map(
    results.map((result) => [
      result.entity_id,
      result,
    ]),
  )

  const levels = new Map<
    number,
    ImpactResult[]
  >()

  results.forEach((result) => {
    const level =
      result.propagation_distance

    const current = levels.get(level) ?? []

    levels.set(level, [
      ...current,
      result,
    ])
  })

  const maxLevel =
    results.length > 0
      ? Math.max(
        ...results.map(
          (result) =>
            result.propagation_distance,
        ),
      )
      : 0

  const nodes: Node<CascadeNodeData>[] = [
    {
      id: 'cascade-root',
      type: 'cascadeRoot',
      position: {
        x: 40,
        y:
          Math.max(
            0,
            ((levels.get(0)?.length ?? 1) - 1) *
            85,
          ),
      },
      data: {
        kind: 'root',
        query:
          query.length > 110
            ? `${query.slice(0, 110)}...`
            : query,
      },
      draggable: false,
    },
  ]

  for (
    let level = 0;
    level <= maxLevel;
    level += 1
  ) {
    const levelResults =
      levels.get(level) ?? []

    levelResults.forEach(
      (result, index) => {
        nodes.push({
          id: getNodeId(result),
          type: 'cascadeEntity',
          position: {
            x: 420 + level * 390,
            y: 70 + index * 205,
          },
          data: {
            kind: 'entity',
            result,
            selected:
              result.entity_id ===
              selectedResultId,
            onSelect,
          },
          draggable: false,
        })
      },
    )
  }

  const edges: Edge[] = []

  results.forEach((result) => {
    let parent: ImpactResult | undefined

    const path = result.path
      .map((item) => item.trim())
      .filter(Boolean)

    for (
      let index = path.length - 2;
      index >= 0;
      index -= 1
    ) {
      const candidate =
        resultsByName.get(
          path[index].toLowerCase(),
        )

      if (
        candidate &&
        candidate.entity_id !==
        result.entity_id
      ) {
        parent = candidate
        break
      }
    }

    if (!parent) {
      const directCandidates =
        results.filter(
          (candidate) =>
            candidate.propagation_distance ===
            result.propagation_distance -
            1,
        )

      if (directCandidates.length === 1) {
        parent = directCandidates[0]
      }
    }

    const source = parent
      ? getNodeId(parent)
      : 'cascade-root'

    const target = getNodeId(result)

    edges.push({
      id: `edge-${source}-${target}`,
      source,
      target,
      type: 'smoothstep',
      animated: false,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 18,
        height: 18,
      },
      style: {
        stroke: getResultImpactColor(
          result,
        ),
        strokeWidth:
          result.impact_score >= 0.7
            ? 3
            : 2,
      },
    })
  })

  /*
   * Remove accidental duplicate edges.
   */
  const uniqueEdges = Array.from(
    new Map(
      edges.map((edge) => [
        `${edge.source}-${edge.target}`,
        edge,
      ]),
    ).values(),
  )

  /*
   * Keep TypeScript aware that the lookup
   * maps are intentionally created for the
   * relationship-building phase.
   */
  void resultsById

  return {
    nodes,
    edges: uniqueEdges,
  }
}

function ImpactAnalysisPage({
  organization,
  query,
  results,
  analyzing,
  error,
  onQueryChange,
  onAnalyze,
}: ImpactAnalysisPageProps) {
  const [viewMode, setViewMode] =
    useState<ViewMode>('cascade')

  const [severityFilter, setSeverityFilter] =
    useState('all')

  const [entityTypeFilter, setEntityTypeFilter] =
    useState('all')

  const [sortMode, setSortMode] =
    useState<SortMode>('risk')

  const [selectedResultId, setSelectedResultId] =
    useState<string | null>(null)

  const entityTypes = useMemo(() => {
    return Array.from(
      new Set(
        results.map(
          (result) => result.entity_type,
        ),
      ),
    ).sort()
  }, [results])

  const filteredResults = useMemo(() => {
    const filtered = results.filter(
      (result) => {
        const impactClass =
          getImpactClass(
            result.impact_level,
          )

        const matchesSeverity =
          severityFilter === 'all' ||
          impactClass === severityFilter

        const matchesEntityType =
          entityTypeFilter === 'all' ||
          result.entity_type ===
          entityTypeFilter

        return (
          matchesSeverity &&
          matchesEntityType
        )
      },
    )

    return [...filtered].sort(
      (first, second) => {
        if (sortMode === 'relevance') {
          return (
            second.semantic_relevance -
            first.semantic_relevance
          )
        }

        if (sortMode === 'proximity') {
          return (
            first.propagation_distance -
            second.propagation_distance
          )
        }

        return (
          second.impact_score -
          first.impact_score
        )
      },
    )
  }, [
    results,
    severityFilter,
    entityTypeFilter,
    sortMode,
  ])

  const handleExampleQuery = (
    example: ExampleQuery,
  ) => {
    onQueryChange({
      target: {
        value: example.query,
      },
      currentTarget: {
        value: example.query,
      },
    } as ChangeEvent<HTMLTextAreaElement>)
  }

  const selectedResult = useMemo(() => {
    if (!selectedResultId) {
      return null
    }

    return (
      filteredResults.find(
        (result) =>
          result.entity_id ===
          selectedResultId,
      ) ?? null
    )
  }, [filteredResults, selectedResultId])

  const maxPropagationDistance =
    filteredResults.length > 0
      ? Math.max(
        ...filteredResults.map(
          (result) =>
            result.propagation_distance,
        ),
      )
      : 0

  const cascadeGraph = useMemo(() => {
    return buildCascadeGraph(
      filteredResults,
      query,
      selectedResultId,
      setSelectedResultId,
    )
  }, [
    filteredResults,
    query,
    selectedResultId,
  ])

  return (
    <div className="page impact-page">
      <div className="impact-intro">
        <span className="eyebrow">
          Business Change Intelligence
        </span>

        <h1>
          What will this change impact?
        </h1>

        <p>
          Describe a proposed requirement
          change. Ripple combines semantic
          retrieval with the organization's
          knowledge graph to identify
          potentially affected business
          entities.
        </p>
      </div>

      <div className="analysis-form">
        <div className="analysis-form-header">
          <span className="analysis-form-title">
            Proposed change specification
          </span>

          <div className="analysis-form-target">
            <span>Target:</span>

            <strong>
              {organization
                ? organization.name
                : 'Select organization'}
            </strong>
          </div>
        </div>

        <textarea
          value={query}
          onChange={onQueryChange}
          placeholder="Describe the proposed business requirement change..."
          rows={4}
          disabled={!organization || analyzing}
        />

        <div className="analysis-form-footer">
          <div className="analysis-example-queries">
            <span>Example queries:</span>

            <div className="analysis-example-list">
              {EXAMPLE_QUERIES.map(
                (example) => (
                  <button
                    key={example.label}
                    type="button"
                    className="analysis-example-button"
                    onClick={() =>
                      handleExampleQuery(
                        example,
                      )
                    }
                    disabled={
                      !organization ||
                      analyzing
                    }
                  >
                    {example.label}
                  </button>
                ),
              )}
            </div>
          </div>

          <button
            type="button"
            className="primary-button"
            onClick={onAnalyze}
            disabled={
              !organization ||
              !query.trim() ||
              analyzing
            }
          >
            {analyzing
              ? 'Analyzing...'
              : 'Analyze impact'}
          </button>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      {results.length === 0 && (
        <div className="analysis-explanation">
          <div className="analysis-step">
            <span>01</span>

            <div>
              <strong>
                Semantic retrieval
              </strong>

              <p>
                Your query is embedded and
                matched against indexed
                document content.
              </p>
            </div>
          </div>

          <div className="analysis-step">
            <span>02</span>

            <div>
              <strong>
                Graph traversal
              </strong>

              <p>
                Matched entities are expanded
                through the knowledge graph to
                surface related, potentially
                affected entities.
              </p>
            </div>
          </div>

          <div className="analysis-step">
            <span>03</span>

            <div>
              <strong>
                Impact scoring
              </strong>

              <p>
                Each entity is scored on
                relevance, relationship
                strength, proximity, and
                importance to produce a
                ranked impact list.
              </p>
            </div>
          </div>
        </div>
      )}

      {results.length > 0 && (
        <div className="results-section">
          <div className="results-heading">
            <div>
              <span className="eyebrow">
                Impact analysis
              </span>

              <h2>
                {filteredResults.length}{' '}
                affected entit
                {filteredResults.length === 1
                  ? 'y'
                  : 'ies'}
              </h2>
            </div>

            <div className="impact-result-summary">
              <span>
                {maxPropagationDistance}{' '}
                max hop
                {maxPropagationDistance === 1
                  ? ''
                  : 's'}
              </span>

              <span>
                {results.length} total
                results
              </span>
            </div>
          </div>

          <div className="impact-controls">
            <div className="impact-filters">
              <label className="impact-filter">
                <span>Severity</span>

                <select
                  value={severityFilter}
                  onChange={(event) =>
                    setSeverityFilter(
                      event.target.value,
                    )
                  }
                >
                  <option value="all">
                    All
                  </option>

                  <option value="critical">
                    Critical / High
                  </option>

                  <option value="medium">
                    Medium
                  </option>

                  <option value="low">
                    Low / Minimal
                  </option>
                </select>
              </label>

              <label className="impact-filter">
                <span>Entity type</span>

                <select
                  value={entityTypeFilter}
                  onChange={(event) =>
                    setEntityTypeFilter(
                      event.target.value,
                    )
                  }
                >
                  <option value="all">
                    All
                  </option>

                  {entityTypes.map(
                    (entityType) => (
                      <option
                        key={entityType}
                        value={entityType}
                      >
                        {entityType}
                      </option>
                    ),
                  )}
                </select>
              </label>

              <label className="impact-filter">
                <span>Sort by</span>

                <select
                  value={sortMode}
                  onChange={(event) =>
                    setSortMode(
                      event.target
                        .value as SortMode,
                    )
                  }
                >
                  <option value="risk">
                    Highest risk
                  </option>

                  <option value="relevance">
                    Highest relevance
                  </option>

                  <option value="proximity">
                    Closest first
                  </option>
                </select>
              </label>
            </div>

            <div className="impact-view-switcher">
              <button
                type="button"
                className={
                  viewMode === 'cascade'
                    ? 'active'
                    : ''
                }
                onClick={() =>
                  setViewMode('cascade')
                }
              >
                Cascade view
              </button>

              <button
                type="button"
                className={
                  viewMode === 'list'
                    ? 'active'
                    : ''
                }
                onClick={() =>
                  setViewMode('list')
                }
              >
                List view
              </button>
            </div>
          </div>

          {filteredResults.length === 0 ? (
            <div className="impact-filter-empty">
              <strong>
                No matching impact results
              </strong>

              <p>
                Adjust the filters to view
                the affected entities.
              </p>
            </div>
          ) : (
            <div className="impact-results-layout">
              <div className="impact-results-main">
                {viewMode === 'cascade' ? (
                  <div className="impact-cascade ripple-cascade">
                    <div className="impact-cascade-header">
                      <div>
                        <h3>
                          Visual cascade &
                          blast radius
                        </h3>

                        <p>
                          Click any node to
                          inspect Ripple's
                          impact factors.
                        </p>
                      </div>

                      <div className="ripple-cascade-legend">
                        <span>
                          <i className="critical" />
                          Critical
                        </span>

                        <span>
                          <i className="medium" />
                          Moderate
                        </span>

                        <span>
                          <i className="low" />
                          Low
                        </span>
                      </div>
                    </div>

                    <div className="ripple-cascade-stage">
                      <div className="ripple-cascade-level-labels">
                        <span>
                          ROOT CHANGE
                        </span>

                        {Array.from(
                          {
                            length:
                              maxPropagationDistance +
                              1,
                          },
                          (_, index) => (
                            <span
                              key={index}
                            >
                              {index === 0
                                ? 'DIRECT IMPACT'
                                : `${index}${index ===
                                  1
                                  ? 'ST'
                                  : index ===
                                    2
                                    ? 'ND'
                                    : index ===
                                      3
                                      ? 'RD'
                                      : 'TH'
                                } HOP`}
                            </span>
                          ),
                        )}
                      </div>

                      <ReactFlow
                        nodes={
                          cascadeGraph.nodes
                        }
                        edges={
                          cascadeGraph.edges
                        }
                        nodeTypes={
                          cascadeNodeTypes
                        }
                        fitView
                        fitViewOptions={{
                          padding: 0.18,
                          minZoom: 0.65,
                          maxZoom: 1.1,
                        }}
                        minZoom={0.45}
                        maxZoom={1.4}
                        nodesDraggable={false}
                        nodesConnectable={false}
                        elementsSelectable
                        proOptions={{
                          hideAttribution: true,
                        }}
                      >
                        <Background
                          gap={22}
                          size={1}
                          color="#ddd7d2"
                        />

                        <Controls
                          showInteractive={false}
                        />
                      </ReactFlow>
                    </div>
                  </div>
                ) : (
                  <div className="results-list">
                    {filteredResults.map(
                      (result) => {
                        const selected =
                          selectedResult?.entity_id ===
                          result.entity_id

                        return (
                          <button
                            type="button"
                            className={`impact-result impact-result-selectable${selected
                                ? ' selected'
                                : ''
                              }`}
                            key={
                              result.entity_id
                            }
                            onClick={() =>
                              setSelectedResultId(
                                result.entity_id,
                              )
                            }
                          >
                            <div className="impact-score">
                              <strong>
                                {formatPercent(
                                  result.impact_score,
                                )}
                              </strong>

                              <span>
                                Impact
                              </span>
                            </div>

                            <div className="impact-result-main">
                              <div className="result-title-row">
                                <h3>
                                  {
                                    result.name
                                  }
                                </h3>

                                <span className="entity-type">
                                  {
                                    result.entity_type
                                  }
                                </span>

                                <span
                                  className={`impact-level ${result.impact_level.toLowerCase()}`}
                                >
                                  {
                                    result.impact_level
                                  }
                                </span>
                              </div>

                              <p>
                                {
                                  result.explanation
                                }
                              </p>

                              <div className="result-factors">
                                <div className="factor">
                                  <span>
                                    Relevance
                                  </span>

                                  <strong>
                                    {formatPercent(
                                      result.semantic_relevance,
                                    )}
                                  </strong>
                                </div>

                                <div className="factor">
                                  <span>
                                    Relationship
                                  </span>

                                  <strong>
                                    {formatPercent(
                                      result.relationship_strength,
                                    )}
                                  </strong>
                                </div>

                                <div className="factor">
                                  <span>
                                    Proximity
                                  </span>

                                  <strong>
                                    {formatPercent(
                                      result.graph_proximity,
                                    )}
                                  </strong>
                                </div>

                                <div className="factor">
                                  <span>
                                    Importance
                                  </span>

                                  <strong>
                                    {formatPercent(
                                      result.entity_importance,
                                    )}
                                  </strong>
                                </div>

                                <span className="propagation-distance">
                                  {
                                    result.propagation_distance
                                  }{' '}
                                  hop
                                  {result.propagation_distance ===
                                    1
                                    ? ''
                                    : 's'}{' '}
                                  away
                                </span>
                              </div>
                            </div>
                          </button>
                        )
                      },
                    )}
                  </div>
                )}
              </div>

              {selectedResult && (
                <div
                  className="impact-detail-overlay"
                  role="presentation"
                  onMouseDown={(event) => {
                    if (event.target === event.currentTarget) {
                      setSelectedResultId(null)
                    }
                  }}
                >
                  <section
                    className="impact-detail-panel"
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="impact-detail-title"
                    onMouseDown={(event) =>
                      event.stopPropagation()
                    }
                  >
                    <div className="impact-detail-header">
                      <div>
                        <span>Selected entity</span>

                        <h2 id="impact-detail-title">
                          {selectedResult.name}
                        </h2>
                      </div>

                      <button
                        type="button"
                        className="impact-detail-close"
                        aria-label="Close impact details"
                        onClick={() =>
                          setSelectedResultId(null)
                        }
                      >
                        ×
                      </button>
                    </div>

                    <div className="impact-detail-summary">
                      <div
                        className={`impact-detail-score ${getImpactClass(
                          selectedResult.impact_level,
                        )}`}
                      >
                        <strong>
                          {formatPercent(
                            selectedResult.impact_score,
                          )}
                        </strong>

                        <span>Impact score</span>
                      </div>

                      <div>
                        <span
                          className={`impact-level ${selectedResult.impact_level.toLowerCase()}`}
                        >
                          {selectedResult.impact_level}
                        </span>

                        <p>
                          {selectedResult.entity_type}
                        </p>
                      </div>
                    </div>

                    <div className="impact-detail-section">
                      <span className="impact-detail-section-title">
                        Impact factors
                      </span>

                      <div className="impact-detail-factors">
                        {[
                          [
                            'Relevance',
                            selectedResult.semantic_relevance,
                          ],
                          [
                            'Relationship',
                            selectedResult.relationship_strength,
                          ],
                          [
                            'Proximity',
                            selectedResult.graph_proximity,
                          ],
                          [
                            'Importance',
                            selectedResult.entity_importance,
                          ],
                        ].map(([label, value]) => (
                          <div
                            className="impact-detail-factor"
                            key={label}
                          >
                            <div>
                              <span>{label}</span>

                              <strong>
                                {formatPercent(
                                  Number(value),
                                )}
                              </strong>
                            </div>

                            <div className="impact-factor-bar">
                              <span
                                style={{
                                  width: `${Math.min(
                                    100,
                                    Math.max(
                                      0,
                                      Number(value) * 100,
                                    ),
                                  )}%`,
                                }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="impact-detail-section">
                      <span className="impact-detail-section-title">
                        Graph information
                      </span>

                      <div className="impact-graph-summary">
                        <strong>
                          {selectedResult.propagation_distance}
                        </strong>

                        <span>
                          hop
                          {selectedResult.propagation_distance ===
                            1
                            ? ''
                            : 's'}{' '}
                          away
                        </span>
                      </div>
                    </div>

                    <div className="impact-detail-section">
                      <span className="impact-detail-section-title">
                        Impact path
                      </span>

                      <div className="impact-detail-path">
                        {selectedResult.path.length > 0 ? (
                          selectedResult.path.map(
                            (item, index) => (
                              <div
                                className="impact-detail-path-item"
                                key={`${item}-${index}`}
                              >
                                <span>{index + 1}</span>

                                <strong>{item}</strong>

                                {index <
                                  selectedResult.path.length -
                                  1 && (
                                    <i>↓</i>
                                  )}
                              </div>
                            ),
                          )
                        ) : (
                          <span>
                            Direct semantic evidence
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="impact-detail-section">
                      <span className="impact-detail-section-title">
                        Why Ripple identified this
                      </span>

                      <p className="impact-detail-explanation">
                        {selectedResult.explanation}
                      </p>

                      <div className="impact-detail-reason-meta">
                        <span>
                          {selectedResult.propagation_distance ===
                            0
                            ? 'Direct semantic impact'
                            : 'Graph-propagated impact'}
                        </span>

                        <span>
                          {formatPercent(
                            selectedResult.semantic_relevance,
                          )}{' '}
                          semantic relevance
                        </span>
                      </div>
                    </div>
                  </section>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default ImpactAnalysisPage