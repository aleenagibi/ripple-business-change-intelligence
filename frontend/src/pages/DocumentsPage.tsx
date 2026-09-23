import { useMemo, useRef, useState } from 'react'
import type {
  ChangeEvent,
  DragEvent,
  InputHTMLAttributes,
  KeyboardEvent,
} from 'react'
import type {
  Document,
  UploadQueueItem,
} from '../api/documents'

interface Organization {
  id: string
  name: string
  slug: string
}

interface DocumentsPageProps {
  organization: Organization
  documents: Document[]
  selectedFiles: File[]
  loadingDocuments: boolean
  uploading: boolean
  error: string | null
  onFileChange: (event: ChangeEvent<HTMLInputElement>) => void
  onUploadDocuments: () => void
uploadQueue: UploadQueueItem[]
  selectedDocument: Document | null
  loadingDocumentDetails: boolean
  onViewDocumentDetails: (
    documentId: string,
  ) => void
  onCloseDocumentDetails: () => void
}

interface FileSystemEntryLike {
  isFile: boolean
  isDirectory: boolean
  name: string
}

interface FileSystemFileEntryLike
  extends FileSystemEntryLike {
  isFile: true
  file: (
    successCallback: (file: File) => void,
    errorCallback?: (error: DOMException) => void,
  ) => void
}

interface FileSystemDirectoryReaderLike {
  readEntries: (
    successCallback: (
      entries: FileSystemEntryLike[],
    ) => void,
    errorCallback?: (error: DOMException) => void,
  ) => void
}

interface FileSystemDirectoryEntryLike
  extends FileSystemEntryLike {
  isDirectory: true
  createReader: () => FileSystemDirectoryReaderLike
}

function fileExtension(filename: string) {
  const parts = filename.split('.')

  if (parts.length < 2) {
    return '?'
  }

  return parts[parts.length - 1]
    .slice(0, 4)
    .toUpperCase()
}

function formatDate(value: string) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return '—'
  }

  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
  }).format(date)
}

function formatFileSize(bytes: number) {
  if (bytes === 0) {
    return '0 B'
  }

  if (bytes < 1024) {
    return `${bytes} B`
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }

  if (bytes < 1024 * 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

function formatCategory(value: string) {
  if (!value) {
    return 'OTHER'
  }

  return value
    .replace(/[_-]+/g, ' ')
    .trim()
    .toUpperCase()
}

function createFileInputEvent(
  files: File[],
): ChangeEvent<HTMLInputElement> {
  const input = document.createElement('input')
  input.type = 'file'

  const dataTransfer = new DataTransfer()

  for (const file of files) {
    dataTransfer.items.add(file)
  }

  Object.defineProperty(input, 'files', {
    value: dataTransfer.files,
    writable: false,
  })

  return {
    target: input,
    currentTarget: input,
  } as ChangeEvent<HTMLInputElement>
}

function readFileEntry(
  entry: FileSystemFileEntryLike,
): Promise<File> {
  return new Promise((resolve, reject) => {
    entry.file(resolve, reject)
  })
}

function readDirectoryEntries(
  directory: FileSystemDirectoryEntryLike,
): Promise<FileSystemEntryLike[]> {
  const reader = directory.createReader()

  return new Promise((resolve, reject) => {
    const entries: FileSystemEntryLike[] = []

    const readBatch = () => {
      reader.readEntries(
        (batch) => {
          if (batch.length === 0) {
            resolve(entries)
            return
          }

          entries.push(...batch)
          readBatch()
        },
        reject,
      )
    }

    readBatch()
  })
}

async function collectEntryFiles(
  entry: FileSystemEntryLike,
): Promise<File[]> {
  if (entry.isFile) {
    return readFileEntry(
      entry as FileSystemFileEntryLike,
    ).then((file) => [file])
  }

  if (entry.isDirectory) {
    const directory =
      entry as FileSystemDirectoryEntryLike

    const children =
      await readDirectoryEntries(directory)

    const nestedFiles = await Promise.all(
      children.map(collectEntryFiles),
    )

    return nestedFiles.flat()
  }

  return []
}

function deduplicateFiles(files: File[]) {
  const seen = new Set<string>()
  const uniqueFiles: File[] = []

  for (const file of files) {
    const key = [
      file.name,
      file.size,
      file.lastModified,
      file.type,
    ].join('|')

    if (seen.has(key)) {
      continue
    }

    seen.add(key)
    uniqueFiles.push(file)
  }

  return uniqueFiles
}

function DocumentsPage({
  organization,
  documents,
  selectedFiles,
   uploadQueue,
  loadingDocuments,
  uploading,
  error,
  onFileChange,
  onUploadDocuments,
  selectedDocument,
  loadingDocumentDetails,
  onViewDocumentDetails,
  onCloseDocumentDetails,
}: DocumentsPageProps) {
  const [dragActive, setDragActive] = useState(false)
  const [processingDrop, setProcessingDrop] =
    useState(false)

  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('ALL')
  const [openMenuId, setOpenMenuId] =
    useState<string | null>(null)

  const dropInputRef =
    useRef<HTMLInputElement | null>(null)

  const categories = useMemo(() => {
    return Array.from(
      new Set(
        documents
          .map((document) =>
            formatCategory(document.document_type),
          )
          .filter(Boolean),
      ),
    ).sort()
  }, [documents])

  const filteredDocuments = useMemo(() => {
    const normalizedSearch =
      search.trim().toLowerCase()

    return documents.filter((document) => {
      const matchesSearch =
        !normalizedSearch ||
        document.filename
          .toLowerCase()
          .includes(normalizedSearch) ||
        document.document_type
          .toLowerCase()
          .includes(normalizedSearch)

      const matchesCategory =
        category === 'ALL' ||
        formatCategory(document.document_type) ===
        category

      return matchesSearch && matchesCategory
    })
  }, [documents, search, category])

  const handleDropZoneClick = () => {
    if (
      !organization ||
      uploading ||
      processingDrop
    ) {
      return
    }

    dropInputRef.current?.click()
  }

  const handleDropZoneKeyDown = (
    event: KeyboardEvent<HTMLDivElement>,
  ) => {
    if (
      event.key !== 'Enter' &&
      event.key !== ' '
    ) {
      return
    }

    event.preventDefault()
    handleDropZoneClick()
  }

  const handleDragEnter = (
    event: DragEvent<HTMLDivElement>,
  ) => {
    event.preventDefault()
    event.stopPropagation()

    if (
      !organization ||
      uploading ||
      processingDrop
    ) {
      return
    }

    setDragActive(true)
  }

  const handleDragOver = (
    event: DragEvent<HTMLDivElement>,
  ) => {
    event.preventDefault()
    event.stopPropagation()

    if (
      !organization ||
      uploading ||
      processingDrop
    ) {
      return
    }

    event.dataTransfer.dropEffect = 'copy'
    setDragActive(true)
  }

  const handleDragLeave = (
    event: DragEvent<HTMLDivElement>,
  ) => {
    event.preventDefault()
    event.stopPropagation()

    if (
      event.currentTarget.contains(
        event.relatedTarget as Node | null,
      )
    ) {
      return
    }

    setDragActive(false)
  }

  const handleDrop = async (
    event: DragEvent<HTMLDivElement>,
  ) => {
    event.preventDefault()
    event.stopPropagation()

    setDragActive(false)

    if (
      !organization ||
      uploading ||
      processingDrop
    ) {
      return
    }

    setProcessingDrop(true)

    try {
      const items = Array.from(
        event.dataTransfer.items,
      )

      const entries = items
        .map((item) => {
          const getEntry = (
            item as DataTransferItem & {
              webkitGetAsEntry?: () =>
                | FileSystemEntryLike
                | null
            }
          ).webkitGetAsEntry

          return getEntry
            ? getEntry.call(item)
            : null
        })
        .filter(
          (
            entry,
          ): entry is FileSystemEntryLike =>
            entry !== null,
        )

      let files: File[] = []

      if (entries.length > 0) {
        const nestedFiles = await Promise.all(
          entries.map(collectEntryFiles),
        )

        files = nestedFiles.flat()
      } else {
        files = Array.from(
          event.dataTransfer.files,
        )
      }

      const uniqueFiles =
        deduplicateFiles(files)

      if (uniqueFiles.length === 0) {
        return
      }

      const changeEvent =
        createFileInputEvent(uniqueFiles)

      onFileChange(changeEvent)
    } finally {
      setProcessingDrop(false)
    }
  }

  const handleDropInputChange = (
    event: ChangeEvent<HTMLInputElement>,
  ) => {
    onFileChange(event)

    if (dropInputRef.current) {
      dropInputRef.current.value = ''
    }
  }

  const handleActionMenuToggle = (
    documentId: string,
  ) => {
    setOpenMenuId((current) =>
      current === documentId
        ? null
        : documentId,
    )
  }

  return (
    <div className="page">
      <div className="page-heading compact">
        <div>
          <span className="eyebrow">
            Knowledge base
          </span>

          <h1>Documents</h1>

          <p>
            Upload the organization's business
            documents into Ripple.
          </p>
        </div>

        <div className="document-upload-actions">
          <label className="primary-button upload-button">
            {uploading
              ? 'Uploading...'
              : 'Choose files'}

            <input
              type="file"
              multiple
              onChange={onFileChange}
              disabled={
                !organization || uploading
              }
            />
          </label>

          <label className="secondary-button upload-button">
            Choose folder

            <input
              type="file"
              multiple
              onChange={onFileChange}
              disabled={
                !organization || uploading
              }
              {...({
                webkitdirectory: '',
              } as InputHTMLAttributes<HTMLInputElement>)}
            />
          </label>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      <div
        className={`document-drop-zone${dragActive
          ? ' document-drop-zone-active'
          : ''
          }${processingDrop
            ? ' document-drop-zone-processing'
            : ''
          }`}
        role="button"
        tabIndex={
          organization && !uploading
            ? 0
            : -1
        }
        aria-label="Upload documents"
        onClick={handleDropZoneClick}
        onKeyDown={handleDropZoneKeyDown}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          ref={dropInputRef}
          type="file"
          multiple
          onChange={handleDropInputChange}
          disabled={
            !organization || uploading
          }
          className="document-drop-input"
        />

        <div className="document-drop-icon">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M12 16V4" />
            <path d="M7 9l5-5 5 5" />
            <path d="M5 14v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4" />
          </svg>
        </div>

        <h3>
          {processingDrop
            ? 'Reading files...'
            : dragActive
              ? 'Drop files here'
              : 'Drag and drop files or folders here'}
        </h3>

        <p>
          {dragActive
            ? 'Release to add them to your upload queue'
            : 'Supports Markdown, PDF, DOCX, TXT, OpenAPI JSON and YAML schemas'}
        </p>
      </div>

{selectedFiles.length > 0 && (
  <section className="upload-queue" aria-label="Document upload queue">
    <div className="upload-queue-header">
      <div>
        <span className="eyebrow">Upload queue</span>

        <h2>
          {selectedFiles.length}{' '}
          {selectedFiles.length === 1
            ? 'document'
            : 'documents'}
        </h2>

        <p>
          Documents are processed and indexed into Ripple's
          semantic and knowledge graph layers.
        </p>
      </div>

      <button
        type="button"
        className="primary-button upload-queue-submit"
        onClick={onUploadDocuments}
        disabled={
          !organization ||
          uploading ||
          processingDrop
        }
      >
        {uploading
          ? 'Processing...'
          : `Upload ${selectedFiles.length} ${
              selectedFiles.length === 1
                ? 'document'
                : 'documents'
            }`}
      </button>
    </div>

    <div className="upload-queue-list">
      {selectedFiles.map((file) => {
        const queueId = `${file.name}-${file.size}-${file.lastModified}`
        const queueItem = uploadQueue.find(
          (item) => item.id === queueId,
        )

        const status = queueItem?.status ?? 'waiting'

        return (
          <div
            className={`upload-queue-item upload-queue-item-${status}`}
            key={queueId}
          >
            <div className="upload-queue-file-icon">
              {fileExtension(file.name)}
            </div>

            <div className="upload-queue-file">
              <strong title={file.name}>
                {file.name}
              </strong>

              <span>
                {(file.size / 1024).toFixed(1)} KB
              </span>
            </div>

            <div className="upload-queue-status">
              {status === 'waiting' && (
                <>
                  <span className="upload-status-dot" />
                  Waiting
                </>
              )}

              {status === 'uploading' && (
                <>
                  <span className="upload-status-spinner" />
                  Uploading
                </>
              )}

              {status === 'processing' && (
                <>
                  <span className="upload-status-spinner" />
                  Indexing
                </>
              )}

              {status === 'completed' && (
                <>
                  <span className="upload-status-check">
                    ✓
                  </span>
                  Indexed
                </>
              )}

              {status === 'failed' && (
                <>
                  <span className="upload-status-error">
                    !
                  </span>
                  Failed
                </>
              )}
            </div>

            {status === 'failed' && queueItem?.error && (
              <span
                className="upload-queue-error"
                title={queueItem.error}
              >
                {queueItem.error}
              </span>
            )}
          </div>
        )
      })}
    </div>
  </section>
)}

      <div className="panel document-panel document-table-panel">
        <div className="document-table-header">
          <div>
            <h2>All documents</h2>

            <p>
              {documents.length}{' '}
              {documents.length === 1
                ? 'document'
                : 'documents'}{' '}
              indexed
            </p>
          </div>

          <div className="document-table-controls">
            <div className="document-category-filter">
              <select
                value={category}
                onChange={(event) =>
                  setCategory(
                    event.target.value,
                  )
                }
                aria-label="Filter documents by category"
              >
                <option value="ALL">
                  All Categories
                </option>

                {categories.map((item) => (
                  <option
                    key={item}
                    value={item}
                  >
                    {item}
                  </option>
                ))}
              </select>
            </div>

            <label className="document-search">
              <svg
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <circle
                  cx="11"
                  cy="11"
                  r="6.5"
                />
                <path d="m16 16 4.5 4.5" />
              </svg>

              <input
                type="search"
                value={search}
                onChange={(event) =>
                  setSearch(
                    event.target.value,
                  )
                }
                placeholder="Search documents..."
                aria-label="Search documents"
              />
            </label>
          </div>
        </div>

        {loadingDocuments ? (
          <div className="empty-state">
            <div className="empty-icon">
              <img
                src="/empty-icon.png"
                alt="Empty"
              />
            </div>

            <h3>
              Loading documents...
            </h3>
          </div>
        ) : filteredDocuments.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">
              <img
                src="/empty-icon.png"
                alt="Empty"
              />
            </div>

            <h3>
              {documents.length === 0
                ? 'No documents uploaded yet'
                : 'No matching documents'}
            </h3>

            <p>
              {documents.length === 0
                ? 'Choose files or a folder above to start building the knowledge graph.'
                : 'Try changing your search or category filter.'}
            </p>
          </div>
        ) : (
          <div className="document-table">
            <div className="document-table-head">
              <span>NAME</span>
              <span>UPLOADED</span>
              <span>VECTOR STATUS</span>
              <span>ACTIONS</span>
            </div>

            {filteredDocuments.map(
              (document) => {
            

                return (
                  <div
                    className="document-table-row"
                    key={document.id}
                  >
                    <div className="document-name-cell">
                      <div className="document-table-icon">
                        {fileExtension(
                          document.filename,
                        )}
                      </div>

                      <div>
                        <strong>
                          {document.filename}
                        </strong>

                        <span>
                          {document.document_type ||
                            'Document'}
                        </span>
                      </div>
                    </div>

                    

                    <div className="document-meta-cell">
                      {formatDate(
                        document.created_at,
                      )}
                    </div>

                    <div>
                      <span className="document-vector-status">
                        <span className="document-vector-dot" />

                        {document.processing_status}
                      </span>
                    </div>

                    <div className="document-action-cell">
                      <button
                        type="button"
                        className="document-action-button"
                        aria-label={`Actions for ${document.filename}`}
                        aria-expanded={
                          openMenuId ===
                          document.id
                        }
                        onClick={() =>
                          handleActionMenuToggle(
                            document.id,
                          )
                        }
                      >
                        ⋮
                      </button>

                      {openMenuId ===
                        document.id && (
                          <div className="document-action-menu">
                            <button
                              type="button"
                              onClick={() => {
                                onViewDocumentDetails(document.id)
                                setOpenMenuId(null)
                              }}
                            >
                              View details
                            </button>
                          </div>
                        )}
                    </div>
                  </div>
                )
              },
            )}
          </div>
        )}
      </div>

      {selectedDocument && (
        <div className="document-details-overlay">
          <aside
            className="document-details-panel"
            aria-label="Document details"
          >
            <div className="document-details-header">
              <div>
                <span className="document-details-section-title">
                  DOCUMENT DETAILS
                </span>

                <h2>Document</h2>
              </div>

              <button
                type="button"
                className="document-details-close"
                onClick={onCloseDocumentDetails}
                aria-label="Close document details"
              >
                ×
              </button>
            </div>

            {loadingDocumentDetails ? (
              <div className="document-details-loading">
                Loading document details...
              </div>
            ) : (
              <>
                <div className="document-details-file">
                  <div className="document-table-icon">
                    {fileExtension(
                      selectedDocument.filename,
                    )}
                  </div>

                  <div>
                    <strong>
                      {selectedDocument.filename}
                    </strong>

                    <span>
                      {selectedDocument.document_type.toUpperCase()}
                    </span>
                  </div>
                </div>

                <div className="document-details-section">
                  <span className="document-details-section-title">
                    INFORMATION
                  </span>

                  <div className="document-details-row">
                    <span>Type</span>

                    <strong>
                      {selectedDocument.document_type.toUpperCase()}
                    </strong>
                  </div>

                  <div className="document-details-row">
                    <span>MIME type</span>

                    <strong>
                      {selectedDocument.mime_type}
                    </strong>
                  </div>

                  <div className="document-details-row">
                    <span>Processing status</span>

                    <strong className="document-details-status">
                      <span>●</span>
                      {selectedDocument.processing_status}
                    </strong>
                  </div>

                  <div className="document-details-row">
                    <span>Uploaded</span>

                    <strong>
                      {formatDate(
                        selectedDocument.created_at,
                      )}
                    </strong>
                  </div>
                </div>
                <div className="document-details-section">
                  <span className="document-details-section-title">
                    RIPPLE INDEX
                  </span>

                  <div className="document-details-row">
                    <span>File size</span>

                    <strong>
                      {selectedDocument.index_stats
                        ? formatFileSize(
                          selectedDocument.index_stats.file_size_bytes,
                        )
                        : '—'}
                    </strong>
                  </div>

                  <div className="document-details-row">
                    <span>Chunks</span>

                    <strong>
                      {selectedDocument.index_stats
                        ? selectedDocument.index_stats.chunk_count.toLocaleString()
                        : '—'}
                    </strong>
                  </div>

                  <div className="document-details-row">
                    <span>Entities</span>

                    <strong>
                      {selectedDocument.index_stats
                        ? selectedDocument.index_stats.entity_count.toLocaleString()
                        : '—'}
                    </strong>
                  </div>

                  <div className="document-details-row">
                    <span>Relationships</span>

                    <strong>
                      {selectedDocument.index_stats
                        ? selectedDocument.index_stats.relationship_count.toLocaleString()
                        : '—'}
                    </strong>
                  </div>

                  <div className="document-details-row">
                    <span>Retrieval</span>

                    <strong>
                      {selectedDocument.index_stats?.retrieval_method ?? '—'}
                    </strong>
                  </div>
                </div>
                {/* <div className="document-details-section">
                  <span className="document-details-section-title">
                    IDENTIFIERS
                  </span>

                  <div className="document-details-row stacked">
                    <span>Document ID</span>

                    <code>
                      {selectedDocument.id}
                    </code>
                  </div>

                  <div className="document-details-row stacked">
                    <span>Organization ID</span>

                    <code>
                      {selectedDocument.organization_id}
                    </code>
                  </div>
                </div> */}
              </>
            )}
          </aside>
        </div>
      )}
    </div>
  )
}

export default DocumentsPage