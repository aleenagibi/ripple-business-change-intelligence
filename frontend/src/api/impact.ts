import { apiFetch } from './client'

export interface ImpactResult {
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

export interface ImpactAnalysisRequest {
  query: string
  top_k: number
  max_distance: number
}

export async function analyzeImpact(
  organizationId: string,
  request: ImpactAnalysisRequest,
): Promise<ImpactResult[]> {
  const response = await apiFetch(
    `/organizations/${organizationId}/retrieval/impact-analysis`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    },
  )

  return response.json()
}