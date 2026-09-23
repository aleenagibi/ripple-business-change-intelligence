import { useEffect, useState } from 'react'
import type { ChangeEvent, ReactNode } from 'react'

import OverviewPage from '../pages/OverviewPage'
import DocumentsPage from '../pages/DocumentsPage'
import ImpactAnalysisPage from '../pages/ImpactAnalysisPage'

import {
  getDocument,
  getDocuments,
  uploadDocument as uploadDocumentRequest,
} from '../api/documents'

import { analyzeImpact } from '../api/impact'

import type { AuthOrganization, AuthUser } from '../api/auth'
import type {
  Document,
  UploadQueueItem,
} from '../api/documents'
import type { ImpactResult } from '../api/impact'

type Page =
  | 'overview'
  | 'documents'
  | 'impact'

interface AuthenticatedAppProps {
  user: AuthUser
  organization: AuthOrganization
  onLogout: () => void
}

const NAV_ITEMS: {
  id: Page
  label: string
  icon: ReactNode
}[] = [
    {
      id: 'overview',
      label: 'Overview',
      icon: (
        <img
          src="/overview-icon.png"
          alt="Overview"
        />
      ),
    },
    {
      id: 'documents',
      label: 'Documents',
      icon: (
        <img
          src="/doc-icon.png"
          alt="Documents"
        />
      ),
    },
    {
      id: 'impact',
      label: 'Impact Analysis',
      icon: (
        <img
          src="/insight-icon.png"
          alt="Impact Analysis"
        />
      ),
    },
  ]

const PAGE_TITLES: Record<Page, string> = {
  overview: 'Overview',
  documents: 'Documents',
  impact: 'Impact Analysis',
}
// function GitHubBadge() {
//   return (
//     <a
//       className="github-badge"
//       href="https://github.com/aleenagibi"
//       target="_blank"
//       rel="noreferrer"
//       aria-label="Visit Aleena Gibi on GitHub"
//     >
//       <svg
//         viewBox="0 0 24 24"
//         aria-hidden="true"
//       >
//         <path
//           fill="currentColor"
//           d="M12 .297c-6.63 0-12 5.373-12 12
//           0 5.303 3.438 9.8 8.205 11.385
//           .6.113.82-.258.82-.577
//           0-.285-.01-1.04-.015-2.04
//           -3.338.724-4.042-1.61-4.042-1.61
//           -.546-1.387-1.333-1.756-1.333-1.756
//           -1.089-.745.084-.729.084-.729
//           1.205.084 1.84 1.237 1.84 1.237
//           1.07 1.835 2.809 1.305 3.495.998
//           .108-.776.418-1.305.762-1.605
//           -2.665-.3-5.466-1.332-5.466-5.93
//           0-1.31.465-2.38 1.235-3.22
//           -.135-.303-.54-1.523.105-3.176
//           0 0 1.005-.322 3.3 1.23
//           .96-.267 1.98-.399 3-.405
//           1.02.006 2.04.138 3 .405
//           2.28-1.552 3.285-1.23 3.285-1.23
//           .645 1.653.24 2.873.12 3.176
//           .765.84 1.23 1.91 1.23 3.22
//           0 4.61-2.805 5.625-5.475 5.92
//           .42.36.81 1.096.81 2.22
//           0 1.606-.015 2.896-.015 3.286
//           0 .315.21.69.825.57
//           C20.565 22.092 24 17.592 24 12.297
//           c0-6.624-5.373-12-12-12"
//         />
//       </svg>

//       <span>GitHub · Aleena Gibi</span>
//     </a>
//   )
// }
function AuthenticatedApp({
  user,
  organization,
  onLogout,
}: AuthenticatedAppProps) {
  const [documents, setDocuments] =
    useState<Document[]>([])

  const [selectedDocument, setSelectedDocument] =
    useState<Document | null>(null)

  const [loadingDocumentDetails, setLoadingDocumentDetails] =
    useState(false)
  const [selectedFiles, setSelectedFiles] =
    useState<File[]>([])
  
  const [uploadQueue, setUploadQueue] =
    useState<UploadQueueItem[]>([])

  const [query, setQuery] =
    useState('')

  const [results, setResults] =
    useState<ImpactResult[]>([])

  const [activePage, setActivePage] =
    useState<Page>('overview')

  const [sidebarCollapsed, setSidebarCollapsed] =
    useState(false)

  const [loadingDocuments, setLoadingDocuments] =
    useState(true)

  const [uploading, setUploading] =
    useState(false)

  const [analyzing, setAnalyzing] =
    useState(false)

  const [error, setError] =
    useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function loadDocuments() {
      try {
        const data =
          await getDocuments(
            organization.id,
          )

        if (cancelled) {
          return
        }

        setDocuments(data)
      } catch (err) {
        if (cancelled) {
          return
        }

        setError(
          err instanceof Error
            ? err.message
            : 'Failed to load documents.',
        )
      } finally {
        if (!cancelled) {
          setLoadingDocuments(false)
        }
      }
    }

    void loadDocuments()

    return () => {
      cancelled = true
    }
  }, [organization.id])

  async function uploadDocuments() {
  if (selectedFiles.length === 0) {
    setError('Select at least one document to upload.')
    return
  }

  setUploading(true)
  setError(null)

  const queue: UploadQueueItem[] = selectedFiles.map(
    (file) => ({
      id: `${file.name}-${file.size}-${file.lastModified}`,
      file,
      status: 'waiting',
    }),
  )

  setUploadQueue(queue)

  try {
    for (const item of queue) {
      setUploadQueue((current) =>
        current.map((queueItem) =>
          queueItem.id === item.id
            ? {
                ...queueItem,
                status: 'uploading',
                error: undefined,
              }
            : queueItem,
        ),
      )

      try {
        const document =
          await uploadDocumentRequest(
            organization.id,
            item.file,
          )

        setDocuments((current) => [
          document,
          ...current.filter(
            (existing) =>
              existing.id !== document.id,
          ),
        ])

        const processingStatus =
          document.processing_status.toLowerCase()

        if (
          processingStatus === 'completed' ||
          processingStatus === 'complete' ||
          processingStatus === 'ready'
        ) {
          setUploadQueue((current) =>
            current.map((queueItem) =>
              queueItem.id === item.id
                ? {
                    ...queueItem,
                    status: 'completed',
                    document,
                  }
                : queueItem,
            ),
          )

          continue
        }

        if (
          processingStatus === 'failed' ||
          processingStatus === 'error'
        ) {
          setUploadQueue((current) =>
            current.map((queueItem) =>
              queueItem.id === item.id
                ? {
                    ...queueItem,
                    status: 'failed',
                    document,
                    error:
                      'Document processing failed.',
                  }
                : queueItem,
            ),
          )

          continue
        }

        setUploadQueue((current) =>
          current.map((queueItem) =>
            queueItem.id === item.id
              ? {
                  ...queueItem,
                  status: 'processing',
                  document,
                }
              : queueItem,
          ),
        )
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : 'Failed to upload document.'

        setUploadQueue((current) =>
          current.map((queueItem) =>
            queueItem.id === item.id
              ? {
                  ...queueItem,
                  status: 'failed',
                  error: message,
                }
              : queueItem,
          ),
        )
      }
    }

    setSelectedFiles([])
  } finally {
    setUploading(false)
  }
}
  async function handleViewDocumentDetails(
    documentId: string,
  ) {
    setLoadingDocumentDetails(true)
    setError(null)

    try {
      const document = await getDocument(
        organization.id,
        documentId,
      )

      setSelectedDocument(document)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to load document details.',
      )
    } finally {
      setLoadingDocumentDetails(false)
    }
  }
  function handleCloseDocumentDetails() {
    setSelectedDocument(null)
  }
  async function runImpactAnalysis() {
    if (!query.trim()) {
      setError(
        'Enter a requirement change to analyze.',
      )
      return
    }

    setAnalyzing(true)
    setError(null)
    setResults([])

    try {
      const data =
        await analyzeImpact(
          organization.id,
          {
            query: query.trim(),
            top_k: 10,
            max_distance: 3,
          },
        )

      setResults(data)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Impact analysis failed.',
      )
    } finally {
      setAnalyzing(false)
    }
  }

function handleFileChange(
  event: ChangeEvent<HTMLInputElement>,
) {
  const files = Array.from(
    event.target.files ?? [],
  )

  setSelectedFiles(files)

  setUploadQueue(
    files.map((file) => ({
      id: `${file.name}-${file.size}-${file.lastModified}`,
      file,
      status: 'waiting',
    })),
  )

  setError(null)

  /*
   * Reset the input value so the same file/folder
   * can be selected again after an upload.
   */
  event.target.value = ''
}

  return (
    <div
      className={`app-shell${sidebarCollapsed
        ? ' sidebar-collapsed'
        : ''
        }`}
    >
      <aside
        className={`sidebar${sidebarCollapsed
          ? ' collapsed'
          : ''
          }`}
      >
        <div className="sidebar-header">
          <div className="brand">
            <div className="brand-mark">
              <img
                src="/logo.png"
                alt="Ripple"
              />
            </div>

            <div>
              <div className="brand-copy">
                <div className="brand-name">
                  Ripple
                </div>

                <div className="brand-subtitle">
                  Business Impact Analysis
                </div>
              </div>
            </div>
            <button
              type="button"
              className="sidebar-collapse-button"
              onClick={() =>
                setSidebarCollapsed(
                  (current) => !current,
                )
              }
              aria-label={
                sidebarCollapsed
                  ? 'Expand sidebar'
                  : 'Collapse sidebar'
              }
              title={
                sidebarCollapsed
                  ? 'Expand sidebar'
                  : 'Collapse sidebar'
              }
            >
              {sidebarCollapsed ? '→' : '←'}
            </button>

          </div>
        </div>

        <div className="organization-selector">
          <span className="section-label">
            Organization
          </span>

          <div className="organization-current">
            {organization.name}
          </div>
        </div>

        <nav className="navigation">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`nav-item${activePage === item.id
                ? ' active'
                : ''
                }`}
              onClick={() =>
                setActivePage(item.id)
              }
            >
              <span className="nav-icon">
                {item.icon}
              </span>

              <span className="nav-label">
                {item.label}
              </span>
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">

          <button
            type="button"
            className="primary-button nav-item"
            onClick={onLogout}
          >
            <span className="nav-icon">
              ↪
            </span>

            <span className="nav-label">
              Sign out
            </span>
          </button>
        </div>
      </aside>

      <div className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            {organization.name}

            <span className="breadcrumb-separator">
              /
            </span>

            <span className="breadcrumb-current">
              {PAGE_TITLES[activePage]}
            </span>
          </div>

          <div className="topbar-right">

            <div
              className="avatar"
              title={user.email}
            >
              {organization.slug
                .slice(0, 2)
                .toUpperCase()}
            </div>
          </div>
        </header>

        {loadingDocuments ? (
          <div className="app-loading">
            <div className="loading-mark">
              <img src="/logo.png" alt="Ripple" />
            </div>

            <p>
              Loading workspace...
            </p>
          </div>
        ) : (
          <>
            {activePage === 'overview' && (
              <OverviewPage
                organization={organization}
                documents={documents}
                results={results}
                error={error}
                onUploadDocument={() =>
                  setActivePage(
                    'documents',
                  )
                }
                onOpenImpactAnalysis={() =>
                  setActivePage(
                    'impact',
                  )
                }
              />
            )}

            {activePage === 'documents' && (
              <DocumentsPage
                organization={organization}
                documents={documents}
                selectedFiles={selectedFiles}
                uploadQueue={uploadQueue}
                loadingDocuments={loadingDocuments}
                uploading={uploading}
                error={error}
                onFileChange={
                  handleFileChange
                }
                onUploadDocuments={() =>
                  void uploadDocuments()
                }
                selectedDocument={selectedDocument}
                loadingDocumentDetails={
                  loadingDocumentDetails
                }
                onViewDocumentDetails={
                  handleViewDocumentDetails
                }
                onCloseDocumentDetails={
                  handleCloseDocumentDetails
                }
              />
            )}

            {activePage === 'impact' && (
              <ImpactAnalysisPage
                organization={organization}
                query={query}
                results={results}
                analyzing={analyzing}
                error={error}
                onQueryChange={(event) =>
                  setQuery(
                    event.target.value,
                  )
                }
                onAnalyze={() =>
                  void runImpactAnalysis()
                }
              />
            )}
          </>
        )}
      </div>
      {/* <GitHubBadge /> */}

    </div>
  )
}

export default AuthenticatedApp