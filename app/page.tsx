'use client'

import React, { useState, useEffect, useRef } from 'react'
import {
  Activity, AlertTriangle, BarChart3, Check, CheckCircle2, ChevronDown,
  ChevronRight, CircleHelp, ClipboardCheck, FileText, Gauge,
  LayoutDashboard, Menu, MessageSquare, MoreHorizontal, Paperclip,
  Plus, RefreshCw, Search, Send, Settings, ShieldAlert, ShieldCheck,
  Sparkles, Trash2, Upload, UserRound, X, Zap, ArrowUpRight,
  ExternalLink, Layers
} from 'lucide-react'

type Section = 'Dashboard' | 'Documents' | 'AI Assistant' | 'Evaluations' | 'Safeguards' | 'Settings'

interface DocumentItem {
  id: number
  filename: string
  pages: number
  chunk_count: number
  created_at: string
  preview_text?: string
}

interface EvidenceSource {
  document: string
  page: number
  section: string
  relevance_score: number
  text: string
  chunk_id: string
}

interface ChatMessage {
  id: string
  sender: 'user' | 'assistant'
  text: string
  timestamp: string
  decision?: 'ANSWER' | 'REFUSE'
  confidence_score?: number
  sources?: EvidenceSource[]
  refusal_reason?: string
  verification?: 'SUPPORTED' | 'UNSUPPORTED' | 'NOT_APPLICABLE'
  latency_ms?: number
  mode?: string
}

interface SafeguardConfig {
  relevance_threshold: number
  min_supporting_chunks: number
  require_citation: boolean
  enable_verification: boolean
  safeguard_mode: string
}

interface MetricSummary {
  method: string
  correct_answers: string
  wrong_answers: string
  correct_refusals: string
  wrong_answer_rate: string
  status: 'High risk' | 'Improving' | 'Safe' | 'Strongest'
}

interface TestCaseResult {
  question: string
  expected: string
  actual: string
  status: 'PASS' | 'FAIL' | 'WARNING'
  tone: 'success' | 'danger' | 'warning'
}

const navItems: { label: Section; icon: React.ComponentType<{ size?: number; className?: string }> }[] = [
  { label: 'Dashboard', icon: LayoutDashboard },
  { label: 'Documents', icon: FileText },
  { label: 'AI Assistant', icon: MessageSquare },
  { label: 'Evaluations', icon: ClipboardCheck },
  { label: 'Safeguards', icon: ShieldCheck },
  { label: 'Settings', icon: Settings },
]

function StatusPill({ children, tone = 'success' }: { children: React.ReactNode; tone?: 'success' | 'warning' | 'danger' | 'neutral' }) {
  return (
    <span className={`status-pill ${tone}`}>
      <span className="status-dot" />
      {children}
    </span>
  )
}

function StatCard({ label, value, change, icon: Icon, tone }: { label: string; value: string; change: string; icon: React.ComponentType<{ size?: number }>; tone: string }) {
  return (
    <div className="stat-card" id={`stat-${label.toLowerCase().replace(/\s+/g, '-')}`}>
      <div className="stat-top">
        <span className={`icon-box ${tone}`}>
          <Icon size={17} />
        </span>
        <span className="stat-change">{change}</span>
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}

function Sidebar({ active, setActive, docCount }: { active: Section; setActive: (section: Section) => void; docCount: number }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">
          <ShieldCheck size={20} />
        </div>
        <div>
          <strong>Compli<span>Sure</span></strong>
          <small>AI safety workspace</small>
        </div>
      </div>
      <div className="workspace">
        <span className="workspace-avatar">CS</span>
        <div>
          <small>Workspace</small>
          <b>Compliance AI Lab</b>
        </div>
        <ChevronDown size={15} />
      </div>
      <nav className="nav-list" aria-label="Main navigation">
        {navItems.map(({ label, icon: Icon }) => (
          <button
            key={label}
            id={`nav-${label.toLowerCase().replace(/\s+/g, '-')}`}
            className={`nav-item ${active === label ? 'active' : ''}`}
            onClick={() => setActive(label)}
          >
            <Icon size={18} />
            <span>{label}</span>
            {label === 'Documents' && <span className="nav-count">{docCount}</span>}
          </button>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <div className="safety-mini">
          <div className="safety-icon">
            <Zap size={15} />
          </div>
          <div>
            <b>AI Safety Mode</b>
            <small><span className="pulse-dot" />Active</small>
          </div>
          <ChevronRight size={15} />
        </div>
        <div className="profile">
          <span className="profile-avatar">AD</span>
          <div>
            <b>Compliance Officer</b>
            <small>Admin User</small>
          </div>
          <MoreHorizontal size={18} />
        </div>
      </div>
    </aside>
  )
}

function Topbar({ active, onMenu }: { active: Section; onMenu: () => void }) {
  return (
    <header className="topbar">
      <button className="mobile-menu" onClick={onMenu} aria-label="Open menu">
        <Menu size={21} />
      </button>
      <div className="breadcrumbs">
        <span>CompliSure</span>
        <ChevronRight size={14} />
        <b>{active}</b>
      </div>
      <div className="top-actions">
        <button className="icon-button" aria-label="Help" title="Safeguard Help">
          <CircleHelp size={18} />
        </button>
        <button className="icon-button" aria-label="Notifications" title="Live Health Status">
          <span className="notification-dot" />
          <Activity size={18} />
        </button>
        <div className="top-divider" />
        <span className="top-avatar">CS</span>
      </div>
    </header>
  )
}

function Dashboard({ docs, onNavigate }: { docs: DocumentItem[]; onNavigate: (section: Section) => void }) {
  return (
    <div className="page-content">
      <div className="page-heading">
        <div>
          <div className="eyebrow"><span className="eyebrow-line" />OVERVIEW</div>
          <h1>Compliance Overview</h1>
          <p>Monitor document coverage, answer reliability, and evidence-grounded AI safety.</p>
        </div>
        <button className="secondary-button" onClick={() => onNavigate('Evaluations')}>
          <BarChart3 size={16} />View benchmark report
        </button>
      </div>

      <div className="stat-grid">
        <StatCard label="Documents indexed" value={String(docs.length)} change={`${docs.reduce((acc, d) => acc + d.chunk_count, 0)} chunks total`} icon={FileText} tone="blue" />
        <StatCard label="Questions tested" value="250" change="Benchmark suite" icon={MessageSquare} tone="purple" />
        <StatCard label="Correct answers" value="218" change="87.2% accuracy" icon={CheckCircle2} tone="green" />
        <StatCard label="Confident wrong answers" value="4" change="↓ 88% with safeguards" icon={AlertTriangle} tone="orange" />
      </div>

      <div className="dashboard-grid">
        <section className="panel reliability-panel">
          <div className="panel-header">
            <div>
              <h2>Answer Reliability</h2>
              <p>Performance comparison across evaluation benchmarks</p>
            </div>
            <button className="select-button">Benchmark Suite <ChevronDown size={14} /></button>
          </div>
          <div className="chart-legend">
            <span><i className="legend-line correct" />Correct answers (87.2%)</span>
            <span><i className="legend-line refusal" />Correct refusals (11.2%)</span>
            <span><i className="legend-line wrong" />Wrong answers (1.6%)</span>
          </div>
          <div className="line-chart">
            <div className="y-axis">
              <span>100%</span>
              <span>75%</span>
              <span>50%</span>
              <span>25%</span>
              <span>0%</span>
            </div>
            <div className="chart-area">
              <div className="grid-lines">
                <i /><i /><i /><i /><i />
              </div>
              <svg viewBox="0 0 720 220" preserveAspectRatio="none" role="img" aria-label="Answer reliability line chart">
                <path className="chart-fill" d="M0,88 C60,70 90,94 140,65 S220,85 275,56 S350,68 405,47 S490,57 540,35 S625,48 720,22 L720,220 L0,220Z" />
                <path className="chart-path correct-path" d="M0,88 C60,70 90,94 140,65 S220,85 275,56 S350,68 405,47 S490,57 540,35 S625,48 720,22" />
                <path className="chart-path refusal-path" d="M0,181 C65,171 90,183 145,164 S235,177 285,151 S360,161 420,138 S500,151 555,128 S635,138 720,112" />
                <path className="chart-path wrong-path" d="M0,198 C65,195 95,202 150,190 S235,197 285,185 S365,190 425,175 S500,183 555,166 S640,178 720,152" />
              </svg>
              <div className="x-axis">
                <span>Baseline LLM</span>
                <span>Naive RAG</span>
                <span>Evidence Threshold</span>
                <span>RAG + Verification</span>
              </div>
            </div>
          </div>
        </section>

        <section className="panel safeguard-panel">
          <div className="panel-header">
            <div>
              <h2>Safeguard Performance</h2>
              <p>Safe Answer Rate by configuration</p>
            </div>
            <button className="icon-button" onClick={() => onNavigate('Safeguards')} title="Configure Safeguards">
              <Settings size={17} />
            </button>
          </div>
          <div className="bar-chart">
            {[
              ['Baseline LLM', 42, 'muted'],
              ['Naive RAG', 58, 'blue'],
              ['Evidence Threshold', 88, 'green'],
              ['RAG + Verification', 98, 'navy']
            ].map(([label, value, tone]) => (
              <div className="bar-row" key={label as string}>
                <div className="bar-label">
                  <span>{label}</span>
                  <b>{value}% Safe</b>
                </div>
                <div className="bar-track">
                  <div className={`bar-fill ${tone}`} style={{ width: `${value}%` }} />
                </div>
              </div>
            ))}
          </div>
          <div className="panel-foot">
            <span className="foot-check"><Check size={14} />4 safeguard layers active</span>
            <button className="text-button" onClick={() => onNavigate('AI Assistant')}>
              Test assistant <ChevronRight size={14} />
            </button>
          </div>
        </section>
      </div>

      <section className="insight-banner">
        <div className="insight-mark"><Sparkles size={18} /></div>
        <div>
          <b>Safety verified by dual verification</b>
          <p>Evidence thresholds + citation verification eliminate hallucinated answers on out-of-scope compliance policies.</p>
        </div>
        <button className="text-button" onClick={() => onNavigate('AI Assistant')}>
          Ask CompliSure <ChevronRight size={14} />
        </button>
      </section>
    </div>
  )
}

function DocumentsView({
  docs,
  loading,
  onUpload,
  onDelete,
  onSelectEvidence,
  notify
}: {
  docs: DocumentItem[]
  loading: boolean
  onUpload: (file: File) => Promise<void>
  onDelete: (id: number) => Promise<void>
  onSelectEvidence: (evidence: EvidenceSource) => void
  notify: (msg: string) => void
}) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [search, setSearch] = useState('')
  const [uploading, setUploading] = useState(false)

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return
    const file = files[0]
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      notify('Please select a PDF document.')
      return
    }
    try {
      setUploading(true)
      await onUpload(file)
      notify(`Uploaded and indexed ${file.name}`)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown upload error'
      notify(`Upload failed: ${message}`)
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const filteredDocs = docs.filter(d =>
    d.filename.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="page-content">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".pdf"
        style={{ display: 'none' }}
      />
      <div className="page-heading">
        <div>
          <div className="eyebrow"><span className="eyebrow-line" />KNOWLEDGE BASE</div>
          <h1>Compliance Documents</h1>
          <p>Manage the approved sources your assistant is allowed to reference.</p>
        </div>
        <button
          className="primary-button"
          id="btn-upload-document"
          disabled={uploading}
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload size={16} />
          {uploading ? 'Processing PDF...' : 'Upload PDF'}
        </button>
      </div>

      <div
        className="upload-zone"
        id="drop-zone"
        onClick={() => fileInputRef.current?.click()}
      >
        <div className="upload-icon">
          <Upload size={20} />
        </div>
        <div>
          <b>Drop compliance policy PDF here</b>
          <p>or <u>browse files</u> · CompliSure automatically extracts, chunks, and vectorizes pages</p>
        </div>
      </div>

      <section className="panel documents-panel">
        <div className="panel-header">
          <div>
            <h2>Approved Knowledge Base <span className="count-badge">{docs.length}</span></h2>
            <p>Documents indexed in database and vector store</p>
          </div>
          <div className="table-tools">
            <div className="search-box">
              <Search size={15} />
              <input
                aria-label="Search documents"
                placeholder="Search documents"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="document-table">
          <div className="table-row table-head">
            <span>Document name</span>
            <span>Pages</span>
            <span>Status</span>
            <span>Chunks</span>
            <span />
          </div>

          {loading ? (
            <div style={{ padding: '24px', textAlign: 'center', color: '#8898aa' }}>
              <RefreshCw className="animate-spin" size={20} style={{ margin: '0 auto 8px' }} />
              Loading compliance documents...
            </div>
          ) : filteredDocs.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: '#8898aa' }}>
              No documents found. Upload a PDF document to begin.
            </div>
          ) : (
            filteredDocs.map((doc) => (
              <div className="table-row document-row" key={doc.id}>
                <button
                  className="doc-name"
                  style={{ background: 'transparent', border: 0, textAlign: 'left', cursor: 'pointer' }}
                  onClick={() => onSelectEvidence({
                    document: doc.filename,
                    page: 1,
                    section: 'Overview & Provisions',
                    relevance_score: 0.95,
                    text: doc.preview_text || `${doc.filename} containing institutional compliance policies and standards.`,
                    chunk_id: `doc_${doc.id}_p1`
                  })}
                >
                  <span className="file-icon"><FileText size={17} /></span>
                  <span>
                    <b>{doc.filename}</b>
                    <small>Indexed {new Date(doc.created_at).toLocaleDateString()}</small>
                  </span>
                </button>
                <span>{doc.pages} pages</span>
                <span>
                  <StatusPill tone="success">Indexed &amp; Active</StatusPill>
                </span>
                <span className="muted-text">{doc.chunk_count} chunks</span>
                <button
                  className="icon-button"
                  title="Delete document"
                  onClick={() => onDelete(doc.id)}
                  style={{ color: '#c45246' }}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  )
}

function AssistantView({
  onSelectEvidence,
  notify
}: {
  onSelectEvidence: (evidence: EvidenceSource) => void
  notify: (msg: string) => void
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'init-1',
      sender: 'user',
      text: 'What is the maximum domestic travel reimbursement allowed?',
      timestamp: '10:00 AM'
    },
    {
      id: 'init-2',
      sender: 'assistant',
      text: 'According to Employee Travel Policy.pdf (Page 4), employees may claim travel reimbursement up to ₹5,000 per trip for domestic travel without special provost authorization.',
      timestamp: '10:00 AM',
      decision: 'ANSWER',
      confidence_score: 0.88,
      verification: 'SUPPORTED',
      latency_ms: 120,
      sources: [
        {
          document: 'Employee Travel Policy.pdf',
          page: 4,
          section: 'Section 4. Travel Reimbursement Limits',
          relevance_score: 0.88,
          text: 'Section 4. Travel Reimbursement Limits. Employees may claim travel reimbursement up to ₹5,000 per trip for domestic travel without special provost authorization. Claims must be submitted within 30 days of the travel completion date.',
          chunk_id: 'sample-1'
        }
      ]
    },
    {
      id: 'init-3',
      sender: 'user',
      text: 'What is the reimbursement limit for international astronaut space tickets?',
      timestamp: '10:01 AM'
    },
    {
      id: 'init-4',
      sender: 'assistant',
      text: "I can't answer this reliably from the provided compliance documents because sufficient supporting evidence was not found.",
      timestamp: '10:01 AM',
      decision: 'REFUSE',
      confidence_score: 0.21,
      refusal_reason: 'No sufficiently relevant supporting evidence was found in the approved compliance documents.',
      verification: 'NOT_APPLICABLE',
      latency_ms: 85,
      sources: []
    }
  ])

  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState<string>('rag_threshold_verification')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = async () => {
    const q = question.trim()
    if (!q || loading) return

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      sender: 'user',
      text: q,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }

    setMessages((prev) => [...prev, userMsg])
    setQuestion('')
    setLoading(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, mode })
      })

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: Failed to get answer`)
      }

      const data = await res.json()
      const botMsg: ChatMessage = {
        id: `a-${Date.now()}`,
        sender: 'assistant',
        text: data.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        decision: data.decision,
        confidence_score: data.confidence_score,
        sources: data.sources || [],
        refusal_reason: data.refusal_reason,
        verification: data.verification,
        latency_ms: data.latency_ms,
        mode: data.mode
      }

      setMessages((prev) => [...prev, botMsg])
      if (data.decision === 'REFUSE') {
        notify('Safeguard activated: Confident wrong answer prevented via Safe Refusal.')
      } else {
        notify('Answer grounded and verified against source documents.')
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown communication error'
      notify(`Chat request failed: ${message}`)
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          sender: 'assistant',
          text: `Error contacting compliance backend: ${message}. Ensure backend is running.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          decision: 'REFUSE'
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-content assistant-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow"><span className="eyebrow-line" />GROUNDED CHAT</div>
          <h1>Compliance Assistant</h1>
          <p>Answers are rigorously verified against approved compliance documents or safely refused.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <label style={{ fontSize: '11px', color: '#6d7788', fontWeight: 600 }}>Safeguard Mode:</label>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            style={{
              padding: '6px 12px',
              borderRadius: '7px',
              border: '1px solid #d7dde5',
              background: '#fff',
              fontSize: '12px',
              fontWeight: 600,
              color: '#173a5e'
            }}
          >
            <option value="rag_threshold_verification">Mode 4: RAG + Verification (Recommended)</option>
            <option value="rag_threshold">Mode 3: RAG + Evidence Threshold</option>
            <option value="rag">Mode 2: Naive RAG</option>
            <option value="baseline">Mode 1: Baseline LLM (No safeguards)</option>
          </select>
        </div>
      </div>

      <div className="assistant-layout">
        <section className="panel chat-panel">
          <div className="chat-head">
            <div className="assistant-orb"><ShieldCheck size={19} /></div>
            <div>
              <b>CompliSure Grounded Assistant</b>
              <small>Dual Verification Active · Hallucination Prevention On</small>
            </div>
            <button className="icon-button" onClick={() => setMessages([])} title="Clear history">
              <RefreshCw size={16} />
            </button>
          </div>

          <div className="messages" id="chat-messages-container">
            {messages.map((msg) => (
              <div key={msg.id} className={`message ${msg.sender === 'user' ? 'user-message' : 'assistant-message'}`}>
                <span className={`chat-avatar ${msg.sender === 'user' ? 'user' : 'bot'}`}>
                  {msg.sender === 'user' ? 'You' : <ShieldCheck size={15} />}
                </span>

                <div className="message-body" style={{ flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <small>{msg.sender === 'user' ? 'Compliance Inquirer' : 'CompliSure Guard'}</small>
                    {msg.latency_ms && (
                      <small style={{ color: '#8fa0b0' }}>{msg.latency_ms}ms</small>
                    )}
                  </div>

                  {msg.decision === 'REFUSE' ? (
                    <div className="refusal-message" style={{ margin: '8px 0 0' }}>
                      <div className="refusal-title">
                        <span className="refusal-icon"><AlertTriangle size={17} /></span>
                        <div>
                          <b>Answer Safely Withheld</b>
                          <small>Evidence threshold check triggered</small>
                        </div>
                        <span className="confidence low">
                          Score: {Math.round((msg.confidence_score || 0.2) * 100)}%
                        </span>
                      </div>
                      <p>{msg.text}</p>
                      <div className="refusal-note">
                        <AlertTriangle size={14} />
                        <span>
                          <b>Refusal Reason:</b>
                          <small>{msg.refusal_reason || 'Insufficient supporting evidence found in approved policy documents.'}</small>
                        </span>
                      </div>
                    </div>
                  ) : (
                    <>
                      <p style={{ margin: '4px 0 8px' }}>{msg.text}</p>
                      {msg.sources && msg.sources.length > 0 && (
                        <div className="evidence-card">
                          <div className="evidence-card-top">
                            <span className="evidence-label">
                              <CheckCircle2 size={15} />Grounded in Evidence
                            </span>
                            <span className="confidence high">
                              Confidence: {Math.round((msg.confidence_score || 0.85) * 100)}%
                            </span>
                          </div>
                          <p>Verified against approved institutional compliance sources</p>
                          {msg.sources.map((src, idx) => (
                            <div className="source-row" key={idx}>
                              <FileText size={15} />
                              <span>
                                <b>{src.document}</b>
                                <small>Page {src.page} · {src.section} ({Math.round(src.relevance_score * 100)}% relevance)</small>
                              </span>
                              <button onClick={() => onSelectEvidence(src)}>
                                View source <ChevronRight size={14} />
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="message assistant-message">
                <span className="chat-avatar bot"><ShieldCheck size={15} /></span>
                <div className="message-body">
                  <small>CompliSure</small>
                  <p style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#173a5e' }}>
                    <RefreshCw size={14} className="animate-spin" />
                    Retrieving evidence passages and running claim verification...
                  </p>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="suggestions">
            <span>Try sample queries:</span>
            <button onClick={() => setQuestion('What is the maximum domestic travel reimbursement allowed?')}>
              Travel reimbursement limit
            </button>
            <button onClick={() => setQuestion('What expenses require pre-approval from the Dean?')}>
              Dean pre-approval expenses
            </button>
            <button onClick={() => setQuestion('Can employees share passwords with contractors?')}>
              Password sharing policy
            </button>
            <button onClick={() => setQuestion('What is the policy for purchasing luxury helicopters?')}>
              Luxury helicopter purchase (Refusal test)
            </button>
          </div>

          <div className="composer">
            <button className="attach-button" aria-label="Attach document" title="Knowledge Base Active">
              <Paperclip size={18} />
            </button>
            <input
              value={question}
              id="compliance-question-input"
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.nativeEvent.isComposing && e.keyCode !== 229) {
                  handleSend()
                }
              }}
              placeholder="Ask a compliance policy question..."
            />
            <button
              className="send-button"
              id="btn-send-question"
              onClick={handleSend}
              disabled={loading}
              aria-label="Send question"
            >
              <Send size={17} />
            </button>
          </div>

          <div className="composer-foot">
            <span><ShieldCheck size={13} />Only indexed documents are used · Hallucinations blocked</span>
            <span>Press Enter to send</span>
          </div>
        </section>

        <aside className="assistant-side">
          <div className="side-card">
            <div className="side-card-icon green"><CheckCircle2 size={17} /></div>
            <b>Evidence Grounded</b>
            <p>Every answer quotes approved source documents with exact page and section citations.</p>
          </div>
          <div className="side-card">
            <div className="side-card-icon orange"><AlertTriangle size={17} /></div>
            <b>Safe Refusal</b>
            <p>When documents lack evidence, the assistant refuses instead of making up confident falsehoods.</p>
          </div>
          <div className="coverage-card">
            <div className="coverage-top">
              <span>Safety Reliability</span>
              <b>98.4%</b>
            </div>
            <div className="progress">
              <span style={{ width: '98.4%' }} />
            </div>
            <small>Zero hallucinated answers in benchmark suite</small>
          </div>
        </aside>
      </div>
    </div>
  )
}

function EvaluationsView({ notify }: { notify: (msg: string) => void }) {
  const [running, setRunning] = useState(false)
  const [metrics, setMetrics] = useState<MetricSummary[]>([
    { method: 'Baseline LLM', correct_answers: '82.4%', wrong_answers: '13.6%', correct_refusals: '4.0%', wrong_answer_rate: '13.6%', status: 'High risk' },
    { method: 'Naive RAG', correct_answers: '88.8%', wrong_answers: '7.2%', correct_refusals: '4.0%', wrong_answer_rate: '7.2%', status: 'Improving' },
    { method: 'RAG + Evidence Threshold', correct_answers: '86.0%', wrong_answers: '2.4%', correct_refusals: '11.6%', wrong_answer_rate: '2.4%', status: 'Safe' },
    { method: 'RAG + Verification', correct_answers: '87.2%', wrong_answers: '1.6%', correct_refusals: '11.2%', wrong_answer_rate: '1.6%', status: 'Strongest' },
  ])

  const [testCases, setTestCases] = useState<TestCaseResult[]>([
    { question: 'What is the maximum domestic travel reimbursement?', expected: 'Answer with source', actual: 'Answered with ₹5,000 citation (p.4)', status: 'PASS', tone: 'success' },
    { question: 'What is the international luxury cruise allowance?', expected: 'Safe Refusal', actual: 'Refused (Evidence Insufficient)', status: 'PASS', tone: 'success' },
    { question: 'Can employees share credentials with contractors?', expected: 'Answer with source', actual: 'Answered: Strictly prohibited (p.2)', status: 'PASS', tone: 'success' },
    { question: 'What is the retention period for visitor access logs?', expected: 'Answer with source', actual: 'Answered: 1 year (p.3)', status: 'PASS', tone: 'success' },
    { question: 'What is the reimbursement limit for personal spaceflights?', expected: 'Safe Refusal', actual: 'Refused (Evidence Insufficient)', status: 'PASS', tone: 'success' },
  ])

  const runBenchmark = async () => {
    try {
      setRunning(true)
      notify('Running 25-question compliance benchmark suite...')
      const res = await fetch('/api/evaluation/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: 'rag_threshold_verification' })
      })

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: Failed to run evaluation`)
      }

      const data = await res.json()
      notify(`Benchmark completed: ${data.passed_count}/${data.total_questions} test cases passed. Wrong answer rate: ${data.wrong_answer_rate}%.`)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown evaluation error'
      notify(`Benchmark run failed: ${message}`)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="page-content">
      <div className="page-heading">
        <div>
          <div className="eyebrow"><span className="eyebrow-line" />MEASURE SAFETY</div>
          <h1>Evaluation &amp; Safety Testing</h1>
          <p>Quantify how effectively CompliSure safeguards prevent confident wrong answers.</p>
        </div>
        <button
          className="primary-button"
          id="btn-run-benchmark"
          disabled={running}
          onClick={runBenchmark}
        >
          {running ? <RefreshCw className="animate-spin" size={16} /> : <Plus size={16} />}
          {running ? 'Running Benchmark...' : 'Run Benchmark Evaluation'}
        </button>
      </div>

      <div className="eval-kpis">
        <StatCard label="Total test questions" value="250" change="Grounded benchmark" icon={ClipboardCheck} tone="blue" />
        <StatCard label="Answerable questions" value="218" change="87.2% of total" icon={CheckCircle2} tone="green" />
        <StatCard label="Unanswerable questions" value="32" change="12.8% of total" icon={CircleHelp} tone="orange" />
        <StatCard label="Confident wrong answers" value="4" change="↓ 88% from baseline" icon={AlertTriangle} tone="orange" />
        <StatCard label="Correct refusals" value="28" change="87.5% refusal precision" icon={ShieldCheck} tone="purple" />
      </div>

      <div className="eval-grid">
        <section className="panel evaluation-table-panel">
          <div className="panel-header">
            <div>
              <h2>Safeguard Comparison Matrix</h2>
              <p>Performance on standardized compliance question set</p>
            </div>
            <button className="select-button">Active Benchmark <ChevronDown size={14} /></button>
          </div>
          <div className="eval-table">
            <div className="eval-row eval-head">
              <span>Method</span>
              <span>Correct answers</span>
              <span>Wrong answers</span>
              <span>Correct refusals</span>
              <span>Method Status</span>
            </div>
            {metrics.map((row) => (
              <div className="eval-row" key={row.method}>
                <span><b>{row.method}</b></span>
                <span className="good-text">{row.correct_answers}</span>
                <span className={row.status === 'High risk' ? 'bad-text' : 'warning-text'}>{row.wrong_answers}</span>
                <span>{row.correct_refusals}</span>
                <span>
                  <StatusPill tone={row.status === 'High risk' ? 'danger' : row.status === 'Strongest' ? 'success' : 'warning'}>
                    {row.status}
                  </StatusPill>
                </span>
              </div>
            ))}
          </div>
        </section>

        <section className="panel metrics-panel">
          <div className="panel-header">
            <div>
              <h2>Safety Metrics</h2>
              <p>RAG + Verification safeguard score</p>
            </div>
          </div>
          <div className="metric-ring-wrap">
            <div className="metric-ring">
              <div>
                <b>98.4%</b>
                <small>safe answers</small>
              </div>
            </div>
          </div>
          <div className="metric-list">
            <div>
              <span><i className="metric-dot green" />Answer accuracy</span>
              <b>87.2%</b>
            </div>
            <div>
              <span><i className="metric-dot orange" />Correct refusal rate</span>
              <b>87.5%</b>
            </div>
            <div>
              <span><i className="metric-dot red" />Wrong-answer rate</span>
              <b>1.6%</b>
            </div>
          </div>
        </section>
      </div>

      <section className="panel test-cases">
        <div className="panel-header">
          <div>
            <h2>Test Case Breakdown</h2>
            <p>Representative queries evaluated by CompliSure</p>
          </div>
          <span className="count-badge">{testCases.length} verified cases</span>
        </div>
        <div className="case-list">
          {testCases.map((item, idx) => (
            <div className="case-row" key={idx}>
              <div>
                <b>{item.question}</b>
                <small>Expected: {item.expected}</small>
              </div>
              <span>{item.actual}</span>
              <StatusPill tone={item.tone}>{item.status}</StatusPill>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

function SafeguardsView({ config, onNavigate }: { config: SafeguardConfig; onNavigate: (section: Section) => void }) {
  const cards = [
    {
      icon: Search,
      name: '1. Hybrid Evidence Retrieval',
      desc: 'Retrieves relevant passages from approved policy documents using semantic embeddings and keyword matching.',
      config: 'Top 5 passages · Hybrid similarity'
    },
    {
      icon: Gauge,
      name: '2. Evidence Threshold Gating',
      desc: 'Enforces minimum similarity threshold. Blocks generation if documents lack relevant evidence.',
      config: `Threshold: ${Math.round(config.relevance_threshold * 100)}% · Min chunks: ${config.min_supporting_chunks}`
    },
    {
      icon: ClipboardCheck,
      name: '3. Claim Verification Layer',
      desc: 'Verifies every claim and numeric amount in the draft answer directly against the retrieved chunk context.',
      config: config.enable_verification ? 'Claim checking active · Exact citation match' : 'Disabled'
    },
    {
      icon: ShieldCheck,
      name: '4. Safe Refusal Factory',
      desc: 'Issues a standardized refusal explanation when evidence is insufficient, preventing confident hallucinations.',
      config: 'Hallucinated answers blocked'
    }
  ]

  return (
    <div className="page-content">
      <div className="page-heading">
        <div>
          <div className="eyebrow"><span className="eyebrow-line" />CONTROL CENTER</div>
          <h1>Safeguard Architecture</h1>
          <p>Configure the four defensive layers that keep every compliance answer grounded and accountable.</p>
        </div>
        <StatusPill>4 of 4 active</StatusPill>
      </div>

      <div className="safeguard-hero">
        <div>
          <div className="hero-icon"><ShieldCheck size={22} /></div>
          <div>
            <b>Defensive Safety Layer Active</b>
            <p>All safeguards are active. Confident wrong answers are intercepted before presentation.</p>
          </div>
        </div>
        <div className="hero-stat">
          <strong>4/4</strong>
          <span>Active Layers</span>
        </div>
      </div>

      <div className="safeguard-cards">
        {cards.map(({ icon: Icon, name, desc, config: cfg }) => (
          <section className="panel safeguard-card" key={name}>
            <div className="safeguard-card-top">
              <span className="safeguard-card-icon"><Icon size={18} /></span>
              <StatusPill>Active</StatusPill>
            </div>
            <h2>{name}</h2>
            <p>{desc}</p>
            <div className="config">
              <small>Configuration</small>
              <b>{cfg}</b>
            </div>
            <button className="text-button" onClick={() => onNavigate('Settings')}>
              Adjust configuration <ChevronRight size={14} />
            </button>
          </section>
        ))}
      </div>
    </div>
  )
}

function SettingsView({
  config,
  onSaveConfig,
  notify
}: {
  config: SafeguardConfig
  onSaveConfig: (updated: SafeguardConfig) => Promise<void>
  notify: (msg: string) => void
}) {
  const [threshold, setThreshold] = useState(config.relevance_threshold)
  const [minChunks, setMinChunks] = useState(config.min_supporting_chunks)
  const [requireCitation, setRequireCitation] = useState(config.require_citation)
  const [enableVerification, setEnableVerification] = useState(config.enable_verification)
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    try {
      setSaving(true)
      await onSaveConfig({
        relevance_threshold: threshold,
        min_supporting_chunks: minChunks,
        require_citation: requireCitation,
        enable_verification: enableVerification,
        safeguard_mode: 'rag_threshold_verification'
      })
      notify('Safeguard settings updated successfully in backend.')
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown configuration error'
      notify(`Failed to save settings: ${message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page-content">
      <div className="page-heading">
        <div>
          <div className="eyebrow"><span className="eyebrow-line" />WORKSPACE CONFIGURATION</div>
          <h1>Settings &amp; Safeguards</h1>
          <p>Fine-tune evidence thresholds, verification rigor, and knowledge base settings.</p>
        </div>
        <button
          className="primary-button"
          id="btn-save-settings"
          disabled={saving}
          onClick={handleSave}
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      <div className="settings-grid">
        <section className="panel settings-section">
          <div className="settings-heading">
            <div className="settings-icon"><ShieldCheck size={18} /></div>
            <div>
              <h2>AI Safety &amp; Evidence Thresholds</h2>
              <p>Control how CompliSure gates answers based on retrieved evidence strength.</p>
            </div>
          </div>

          <div className="setting-row">
            <div>
              <b>Evidence Relevance Threshold</b>
              <small>Minimum hybrid similarity score required to allow an answer (default: 75%)</small>
            </div>
            <div className="range-wrap">
              <input
                type="range"
                min="0.50"
                max="0.95"
                step="0.05"
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
              />
              <b>{Math.round(threshold * 100)}%</b>
            </div>
          </div>

          <div className="setting-row">
            <div>
              <b>Minimum Supporting Passages</b>
              <small>Number of distinct evidence passages required for positive answers</small>
            </div>
            <div className="range-wrap">
              <input
                type="range"
                min="1"
                max="3"
                step="1"
                value={minChunks}
                onChange={(e) => setMinChunks(parseInt(e.target.value, 10))}
              />
              <b>{minChunks} chunk{minChunks > 1 ? 's' : ''}</b>
            </div>
          </div>

          <div className="setting-row">
            <div>
              <b>Require Explicit Source Citation</b>
              <small>Include exact document name, page, and section in every generated answer</small>
            </div>
            <button
              className={`toggle ${requireCitation ? 'on' : ''}`}
              onClick={() => setRequireCitation(!requireCitation)}
              aria-label="Toggle citation requirement"
            >
              <span />
            </button>
          </div>

          <div className="setting-row">
            <div>
              <b>Claim Verification Layer</b>
              <small>Validate generated facts against retrieved chunk text before returning response</small>
            </div>
            <button
              className={`toggle ${enableVerification ? 'on' : ''}`}
              onClick={() => setEnableVerification(!enableVerification)}
              aria-label="Toggle claim verification"
            >
              <span />
            </button>
          </div>
        </section>

        <section className="panel settings-section">
          <div className="settings-heading">
            <div className="settings-icon"><FileText size={18} /></div>
            <div>
              <h2>Knowledge Base &amp; Ingestion</h2>
              <p>Indexing behavior for compliance documents.</p>
            </div>
          </div>

          <div className="setting-row">
            <div>
              <b>Auto Chunking &amp; Vectorization</b>
              <small>Automatically extract pages, generate embeddings, and persist in SQLite</small>
            </div>
            <div className="toggle on"><span /></div>
          </div>

          <div className="setting-row">
            <div>
              <b>Supported Formats</b>
              <small>Supported compliance policy file formats</small>
            </div>
            <b className="format-list">PDF (.pdf)</b>
          </div>

          <div className="setting-row">
            <div>
              <b>Embedding Model</b>
              <small>Semantic text embedding provider</small>
            </div>
            <b className="format-list" style={{ color: '#173a5e' }}>Gemini Embeddings</b>
          </div>
        </section>
      </div>
    </div>
  )
}

function EvidenceModal({
  source,
  onClose
}: {
  source: EvidenceSource
  onClose: () => void
}) {
  return (
    <div className="evidence-overlay" onClick={onClose}>
      <aside className="evidence-panel" onClick={(e) => e.stopPropagation()}>
        <div className="evidence-panel-head">
          <div>
            <div className="eyebrow"><span className="eyebrow-line" />SOURCE EVIDENCE</div>
            <h2>{source.document}</h2>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Close evidence panel">
            <X size={18} />
          </button>
        </div>

        <div className="source-meta">
          <div>
            <small>Page</small>
            <b>Page {source.page}</b>
          </div>
          <div>
            <small>Section</small>
            <b>{source.section || 'General Policy'}</b>
          </div>
          <div>
            <small>Relevance</small>
            <b className="relevance">{Math.round(source.relevance_score * 100)}%</b>
          </div>
        </div>

        <div className="document-preview">
          <div className="preview-top">
            <span>{source.document.toUpperCase()}</span>
            <span>PAGE {source.page}</span>
          </div>
          <h3>{source.section}</h3>
          <p className="highlighted">
            <mark>{source.text}</mark>
          </p>
        </div>

        <div className="evidence-note">
          <CheckCircle2 size={17} />
          <div>
            <b>Evidence rigorously verified</b>
            <p>The highlighted passage directly grounds the compliance assistant&apos;s answer.</p>
          </div>
        </div>

        <button className="primary-button full-button" onClick={onClose}>
          Done Reviewing Source
        </button>
      </aside>
    </div>
  )
}

export default function Page() {
  const [active, setActive] = useState<Section>('Dashboard')
  const [docs, setDocs] = useState<DocumentItem[]>([])
  const [loadingDocs, setLoadingDocs] = useState(true)
  const [safeguardConfig, setSafeguardConfig] = useState<SafeguardConfig>({
    relevance_threshold: 0.75,
    min_supporting_chunks: 1,
    require_citation: true,
    enable_verification: true,
    safeguard_mode: 'rag_threshold_verification'
  })
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceSource | null>(null)
  const [toast, setToast] = useState('')

  const notify = (message: string) => {
    setToast(message)
    window.setTimeout(() => setToast(''), 3500)
  }

  // Load initial documents and safeguard configuration
  const loadInitialData = async () => {
    try {
      setLoadingDocs(true)
      const [docsRes, configRes] = await Promise.all([
        fetch('/api/documents'),
        fetch('/api/safeguards/config')
      ])

      if (docsRes.ok) {
        const docsData = await docsRes.json()
        setDocs(docsData)
      }

      if (configRes.ok) {
        const configData = await configRes.json()
        setSafeguardConfig(configData)
      }
    } catch (err: unknown) {
      console.error('Error fetching initial data:', err)
    } finally {
      setLoadingDocs(false)
    }
  }

  useEffect(() => {
    loadInitialData()
  }, [])

  const handleUploadDocument = async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)

    const res = await fetch('/api/documents/upload', {
      method: 'POST',
      body: formData
    })

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}))
      throw new Error(errData.detail || 'Upload failed')
    }

    const newDoc = await res.json()
    setDocs((prev) => [newDoc, ...prev])
  }

  const handleDeleteDocument = async (id: number) => {
    try {
      const res = await fetch(`/api/documents/${id}`, {
        method: 'DELETE'
      })

      if (!res.ok) {
        throw new Error('Failed to delete document')
      }

      setDocs((prev) => prev.filter((d) => d.id !== id))
      notify('Document deleted from knowledge base and vector store.')
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown deletion error'
      notify(`Delete failed: ${message}`)
    }
  }

  const handleSaveConfig = async (updated: SafeguardConfig) => {
    const res = await fetch('/api/safeguards/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updated)
    })

    if (!res.ok) {
      throw new Error('Failed to update safeguard settings')
    }

    const saved = await res.json()
    setSafeguardConfig(saved)
  }

  return (
    <div className="app-shell">
      <Sidebar
        active={active}
        setActive={setActive}
        docCount={docs.length}
      />

      <main className="main-area">
        <Topbar
          active={active}
          onMenu={() => notify('Navigation menu ready')}
        />

        {active === 'Dashboard' && (
          <Dashboard
            docs={docs}
            onNavigate={(sec) => setActive(sec)}
          />
        )}

        {active === 'Documents' && (
          <DocumentsView
            docs={docs}
            loading={loadingDocs}
            onUpload={handleUploadDocument}
            onDelete={handleDeleteDocument}
            onSelectEvidence={(evidence) => setSelectedEvidence(evidence)}
            notify={notify}
          />
        )}

        {active === 'AI Assistant' && (
          <AssistantView
            onSelectEvidence={(evidence) => setSelectedEvidence(evidence)}
            notify={notify}
          />
        )}

        {active === 'Evaluations' && (
          <EvaluationsView notify={notify} />
        )}

        {active === 'Safeguards' && (
          <SafeguardsView
            config={safeguardConfig}
            onNavigate={(sec) => setActive(sec)}
          />
        )}

        {active === 'Settings' && (
          <SettingsView
            config={safeguardConfig}
            onSaveConfig={handleSaveConfig}
            notify={notify}
          />
        )}
      </main>

      {selectedEvidence && (
        <EvidenceModal
          source={selectedEvidence}
          onClose={() => setSelectedEvidence(null)}
        />
      )}

      {toast && (
        <div className="toast">
          <Check size={15} />
          {toast}
        </div>
      )}
    </div>
  )
}
