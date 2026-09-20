import { apiFetch } from './client'

export interface Document {
  id: string
  organization_id: string
  filename: string
  document_type: string
  mime_type: string
  processing_status: string
  created_at: string
}

export async function getDocuments(
  organizationId: string,
): Promise<Document[]> {
  const response = await apiFetch(
    `/organizations/${organizationId}/documents`,
  )

  return response.json()
}

export async function getDocument(
  organizationId: string,
  documentId: string,
): Promise<Document> {
  const response = await apiFetch(
    `/organizations/${organizationId}/documents/${documentId}`,
  )

  return response.json()
}

export async function uploadDocument(
  organizationId: string,
  file: File,
): Promise<Document> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await apiFetch(
    `/organizations/${organizationId}/documents`,
    {
      method: 'POST',
      body: formData,
    },
  )

  return response.json()
}