import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import './index.css'

const STORAGE_KEYS = {
  agentArn: 'chat_agent_arn',
  apiUrl: 'chat_api_url',
  idToken: 'cognito_id_token',
  cognitoLoginUrl: 'chat_cognito_login_url',
  user: 'cognito_user',
}

function App() {
  const [agentArn, setAgentArn] = useState('')
  const [apiUrl, setApiUrl] = useState('')
  const [messages, setMessages] = useState([])
  const [inputText, setInputText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [humanInLoop, setHumanInLoop] = useState(false)
  const [sessionId] = useState(() => `chat-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`)
  const [showSettings, setShowSettings] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [authToken, setAuthToken] = useState('')
  const [cognitoLoginUrl, setCognitoLoginUrl] = useState('')
  const messagesEndRef = useRef(null)

  useEffect(() => {
    setAgentArn(localStorage.getItem(STORAGE_KEYS.agentArn) || '')
    setApiUrl(localStorage.getItem(STORAGE_KEYS.apiUrl) || import.meta.env.VITE_API_URL || '')
    setCognitoLoginUrl(localStorage.getItem(STORAGE_KEYS.cognitoLoginUrl) || '')
    const token = localStorage.getItem(STORAGE_KEYS.idToken)
    if (token) {
      setAuthToken(token)
      setIsAuthenticated(true)
    }
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const saveSettings = () => {
    localStorage.setItem(STORAGE_KEYS.agentArn, agentArn)
    localStorage.setItem(STORAGE_KEYS.apiUrl, apiUrl)
    setShowSettings(false)
  }

  const getApiBase = () => {
    if (apiUrl) return apiUrl.replace(/\/$/, '')
    return ''
  }

  const api = axios.create({
    baseURL: getApiBase() || undefined,
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  })

  const handleSend = async () => {
    const text = inputText.trim()
    if (!text) return
    if (!agentArn && !getApiBase()) {
      setError('Configure Agent ARN or API URL in Settings')
      return
    }

    setInputText('')
    setError(null)
    const userMsg = { id: `u-${Date.now()}`, role: 'user', content: text, timestamp: new Date().toISOString() }
    setMessages((prev) => [...prev, userMsg])
    setLoading(true)

    const assistantId = `a-${Date.now()}`
    const assistantMsg = { id: assistantId, role: 'assistant', content: '', loading: true }
    setMessages((prev) => [...prev, assistantMsg])

    try {
      const endpoint = getApiBase() ? `${getApiBase()}/invoke` : '/api/invoke'
      const payload = {
        agentArn: agentArn || undefined,
        prompt: text,
        sessionId,
        humanInLoop: humanInLoop,
      }
      if (!payload.agentArn) delete payload.agentArn

      const res = await api.post(endpoint, payload)
      const data = res.data

      if (data.status === 'awaiting_human_review' || data.interrupt) {
        const interruptPayload = Array.isArray(data.interrupt) ? data.interrupt[0] : data.interrupt
        updateMessage(assistantId, {
          content: data.output || data.message || interruptPayload?.message || 'Evaluation requires human review.',
          loading: false,
          awaitingReview: {
            sessionId: data.session_id,
            interrupt: interruptPayload || data.interrupt,
            resumeInstruction: data.resume_instruction,
          },
        })
        setLoading(false)
        return
      }

      updateMessage(assistantId, {
        content: formatResponse(data),
        loading: false,
      })
    } catch (err) {
      const errMsg = err.response?.data?.error || err.response?.data?.message || err.message || 'Request failed'
      updateMessage(assistantId, { content: `Error: ${errMsg}`, loading: false, error: true })
      setError(errMsg)
    } finally {
      setLoading(false)
    }
  }

  const updateMessage = (id, updates) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, ...updates } : m))
    )
  }

  const handleResume = async (msg, action, overrideScore) => {
    if (!msg.awaitingReview) return
    const { sessionId: revSessionId } = msg.awaitingReview
    const humanDecision = action === 'override' && overrideScore != null
      ? { action: 'override', score: parseFloat(overrideScore) }
      : { action }

    const assistantId = msg.id
    updateMessage(assistantId, { loading: true, awaitingReview: null })

    try {
      const endpoint = getApiBase() ? `${getApiBase()}/invoke` : '/api/invoke'
      const res = await api.post(endpoint, {
        agentArn: agentArn || undefined,
        resume: humanDecision,
        sessionId: revSessionId,
      })
      const data = res.data
      if (data.status === 'awaiting_human_review' || data.interrupt) {
        const interruptPayload = Array.isArray(data.interrupt) ? data.interrupt[0] : data.interrupt
        updateMessage(assistantId, {
          content: data.output || interruptPayload?.message || 'Review required',
          loading: false,
          awaitingReview: {
            sessionId: data.session_id,
            interrupt: interruptPayload || data.interrupt,
          },
        })
      } else {
        updateMessage(assistantId, {
          content: formatResponse(data),
          loading: false,
        })
      }
    } catch (err) {
      const errMsg = err.response?.data?.error || err.message || 'Resume failed'
      updateMessage(assistantId, { content: `Error: ${errMsg}`, loading: false, error: true })
    }
  }

  const formatResponse = (data) => {
    if (!data) return 'No response'
    if (data.output && typeof data.output === 'string') return data.output
    if (data.evaluation_results && Array.isArray(data.evaluation_results)) {
      return data.evaluation_results.map((r) => JSON.stringify(r, null, 2)).join('\n\n')
    }
    if (data.summary) return JSON.stringify(data.summary, null, 2)
    return JSON.stringify(data, null, 2)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="chat-container">
      <header className="chat-header">
        <h1>RAG Evaluation Chat</h1>
        <div className="header-actions">
          <label className="hitl-toggle">
            <input
              type="checkbox"
              checked={humanInLoop}
              onChange={(e) => setHumanInLoop(e.target.checked)}
            />
            Human-in-the-loop
          </label>
          <button className="btn-icon" onClick={() => setShowSettings(true)} title="Settings">
            ⚙️
          </button>
        </div>
      </header>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="welcome">
            <p>Send a query to run RAG evaluation.</p>
            <p className="hint">Toggle &quot;Human-in-the-loop&quot; to pause for review when scores are below threshold.</p>
          </div>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={`message message-${msg.role}`}>
            <div className="message-avatar">{msg.role === 'user' ? '👤' : '🤖'}</div>
            <div className="message-content">
              {msg.loading ? (
                <span className="loading-text">Evaluating...</span>
              ) : (
                <>
                  <pre className="message-text">{msg.content}</pre>
                  {msg.awaitingReview && (
                    <div className="review-actions">
                      <p className="review-message">{msg.awaitingReview.interrupt?.message}</p>
                      <div className="review-buttons">
                        <button className="btn btn-approve" onClick={() => handleResume(msg, 'approve')}>
                          Approve
                        </button>
                        <button className="btn btn-reject" onClick={() => handleResume(msg, 'reject')}>
                          Reject
                        </button>
                        <button
                          className="btn btn-override"
                          onClick={() => {
                            const score = prompt('Override score (0-1):', '0.85')
                            if (score != null) handleResume(msg, 'override', score)
                          }}
                        >
                          Override Score
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      <div className="chat-input-area">
        <textarea
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter evaluation query (e.g., What is RAG?)"
          disabled={loading}
          rows={2}
        />
        <button
          className="btn-send"
          onClick={handleSend}
          disabled={loading || !inputText.trim()}
        >
          {loading ? '...' : 'Send'}
        </button>
      </div>

      {showSettings && (
        <div className="modal-overlay" onClick={() => setShowSettings(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Settings</h2>
            <div className="form-group">
              <label>API URL (API Gateway or backend)</label>
              <input
                type="text"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                placeholder="https://xxx.execute-api.us-east-1.amazonaws.com/prod"
              />
              <small>Leave empty to use current origin (local dev)</small>
            </div>
            <div className="form-group">
              <label>Agent ARN (optional if API uses fixed agent)</label>
              <input
                type="text"
                value={agentArn}
                onChange={(e) => setAgentArn(e.target.value)}
                placeholder="arn:aws:bedrock-agentcore:us-east-1:..."
              />
            </div>
            <div className="form-group">
              <label>Cognito Hosted UI URL (optional)</label>
              <input
                type="text"
                value={cognitoLoginUrl}
                onChange={(e) => {
                  const v = e.target.value
                  setCognitoLoginUrl(v)
                  localStorage.setItem(STORAGE_KEYS.cognitoLoginUrl, v)
                }}
                placeholder="https://your-pool.auth.region.amazoncognito.com/login?..."
              />
              <small>Open this URL to log in, then copy id_token from callback URL</small>
            </div>
            <div className="form-group">
              <label>Cognito Token (for API Gateway auth)</label>
              <input
                type="password"
                value={authToken ? '••••••••' : ''}
                onChange={(e) => {
                  const v = e.target.value
                  if (v !== '••••••••') {
                    setAuthToken(v)
                    localStorage.setItem(STORAGE_KEYS.idToken, v)
                    setIsAuthenticated(!!v)
                  }
                }}
                placeholder="Paste id_token from Cognito"
              />
              <small>Get token from Cognito Hosted UI after login</small>
              {cognitoLoginUrl && (
                <a href={cognitoLoginUrl} target="_blank" rel="noopener noreferrer" className="login-link">
                  Open Cognito Login
                </a>
              )}
            </div>
            <div className="modal-actions">
              <button className="btn btn-primary" onClick={saveSettings}>
                Save
              </button>
              <button className="btn btn-secondary" onClick={() => setShowSettings(false)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
