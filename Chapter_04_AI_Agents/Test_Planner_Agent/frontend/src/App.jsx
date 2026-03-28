import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [theme, setTheme] = useState('dark')
  const [step, setStep] = useState(1)
  
  // Form states
  const [llm, setLlm] = useState({ provider: 'Ollama', url: 'http://localhost:11434', key: '', model: 'llama3' })
  const [jira, setJira] = useState({ url: 'https://yourcompany.atlassian.net', email: '', token: '' })
  const [ticketId, setTicketId] = useState('')
  const [context, setContext] = useState('')
  
  // Processing states
  const [status, setStatus] = useState({ type: '', text: '' })
  const [generatedMarkdown, setGeneratedMarkdown] = useState('')

  // Handlers
  const testLlmAndNext = async () => {
    setStatus({ type: 'loading', text: 'Testing LLM Connection...' })
    try {
      const res = await fetch('http://localhost:8000/api/test-llm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(llm)
      });
      const data = await res.json();
      if(res.ok) {
        setStatus({ type: 'success', text: data.message })
        setTimeout(() => { setStatus({ type: '', text: ''}); setStep(2); }, 1000)
      } else {
        setStatus({ type: 'error', text: data.detail })
      }
    } catch(e) {
      setStatus({ type: 'error', text: 'Backend unavailable.' })
    }
  }

  const testJiraAndNext = async () => {
    setStatus({ type: 'loading', text: 'Testing Jira Connection...' })
    try {
      const res = await fetch('http://localhost:8000/api/test-jira', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(jira)
      });
      const data = await res.json();
      if(res.ok) {
        setStatus({ type: 'success', text: data.message })
        setTimeout(() => { setStatus({ type: '', text: ''}); setStep(3); }, 1000)
      } else {
        setStatus({ type: 'error', text: data.detail })
      }
    } catch(e) {
      setStatus({ type: 'error', text: 'Backend unavailable.' })
    }
  }

  const generatePlan = async () => {
    if (!ticketId || !jira.email || !jira.token) {
      setStatus({ type: 'error', text: 'Please fill Jira details and Ticket ID' })
      return;
    }
    setStatus({ type: 'loading', text: 'Agent is generating your test plan... (This may take a minute)' })
    setGeneratedMarkdown('')
    try {
      const res = await fetch('http://localhost:8000/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jira, llm, ticket_id: ticketId, context })
      });
      const data = await res.json();
      if(res.ok) {
        setStatus({ type: 'success', text: 'Plan generated successfully! ' + data.file_path })
        setGeneratedMarkdown(data.markdown)
        setStep(4)
      }
      else {
        setStatus({ type: 'error', text: data.detail })
      }
    } catch(e) {
      setStatus({ type: 'error', text: 'Backend unavailable or timed out.' })
    }
  }

  return (
    <div className={`app-container ${theme}`}>
      {/* Sidebar Panel */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo-icon">🚀</div>
          <h2>B.L.A.S.T</h2>
        </div>
        <nav className="sidebar-nav">
          <ul>
            <li className="active">📊 Dashboard</li>
            <li>⚙️ Settings</li>
            <li>🕒 History</li>
          </ul>
        </nav>
        <div className="sidebar-footer">
          <button className="theme-toggle" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
            {theme === 'dark' ? '☀️ Light Mode' : '🌙 Dark Mode'}
          </button>
        </div>
      </aside>

      {/* Main Dashboard Panel */}
      <main className="dashboard">
        <header className="dashboard-header">
          <h1>Test Planner Dashboard</h1>
          <p>Guided step-by-step workflow for generating test plans</p>
        </header>

        <div className="dashboard-content">
          {status.text && (
             <div className={`status-banner ${status.type}`}>
               {status.text}
             </div>
          )}

          <div className="stepper">
            {/* Step 1: LLM */}
            <div className={`step-card ${step === 1 ? 'active' : step > 1 ? 'completed' : 'disabled'}`}>
              <div className="step-header" onClick={() => step > 1 && setStep(1)}>
                <div className="step-number">1</div>
                <h2>LLM Connection</h2>
              </div>
              {step === 1 && (
                <div className="step-body">
                  <div className="form-group">
                    <label>Provider</label>
                    <select value={llm.provider} onChange={e => setLlm({...llm, provider: e.target.value})}>
                      <option>Ollama</option>
                      <option>Groq</option>
                      <option>Grok</option>
                    </select>
                  </div>
                  <div className="form-row">
                    <div className="form-group flex-2">
                      <label>Base URL / API Key</label>
                      {llm.provider === 'Ollama' ? 
                        <input type="text" value={llm.url} onChange={e => setLlm({...llm, url: e.target.value})} placeholder="http://localhost:11434" /> :
                        <input type="password" value={llm.key} onChange={e => setLlm({...llm, key: e.target.value})} placeholder="API Key" />
                      }
                    </div>
                    <div className="form-group flex-1">
                      <label>Model Name</label>
                      <input type="text" value={llm.model} onChange={e => setLlm({...llm, model: e.target.value})} />
                    </div>
                  </div>
                  <button className="btn primary" onClick={testLlmAndNext}>Test Connection & Continue ➔</button>
                </div>
              )}
            </div>

            {/* Step 2: Jira */}
            <div className={`step-card ${step === 2 ? 'active' : step > 2 ? 'completed' : 'disabled'}`}>
              <div className="step-header" onClick={() => step > 2 && setStep(2)}>
                <div className="step-number">2</div>
                <h2>Jira Connection</h2>
              </div>
              {step === 2 && (
                <div className="step-body">
                  <div className="form-group">
                    <label>Jira URL</label>
                    <input type="text" value={jira.url} onChange={e => setJira({...jira, url: e.target.value})} placeholder="https://yourcompany.atlassian.net" />
                  </div>
                  <div className="form-row">
                    <div className="form-group flex-1">
                      <label>Email</label>
                      <input type="email" value={jira.email} onChange={e => setJira({...jira, email: e.target.value})} />
                    </div>
                    <div className="form-group flex-1">
                      <label>API Token</label>
                      <input type="password" value={jira.token} onChange={e => setJira({...jira, token: e.target.value})} />
                    </div>
                  </div>
                  <div className="btn-group">
                    <button className="btn outline" onClick={() => setStep(1)}>Back</button>
                    <button className="btn primary" onClick={testJiraAndNext}>Test Connection & Continue ➔</button>
                  </div>
                </div>
              )}
            </div>

            {/* Step 3: Ticket Info */}
            <div className={`step-card ${step === 3 ? 'active' : step > 3 ? 'completed' : 'disabled'}`}>
              <div className="step-header" onClick={() => step > 3 && setStep(3)}>
                <div className="step-number">3</div>
                <h2>Ticket Information</h2>
              </div>
              {step === 3 && (
                <div className="step-body">
                  <div className="form-group">
                    <label>Jira Ticket ID (Required)</label>
                    <input type="text" value={ticketId} onChange={e => setTicketId(e.target.value)} placeholder="e.g. TEST-123" />
                  </div>
                  <div className="form-group">
                    <label>Additional Context / Instructions (Optional)</label>
                    <textarea value={context} onChange={e => setContext(e.target.value)} placeholder="E.g. Focus specifically on security boundary testing..."></textarea>
                  </div>
                  <div className="btn-group">
                    <button className="btn outline" onClick={() => setStep(2)}>Back</button>
                    <button className="btn primary highlight" onClick={generatePlan}>⚡ Generate Test Plan</button>
                  </div>
                </div>
              )}
            </div>

            {/* Step 4: Output Output */}
            <div className={`step-card ${step === 4 ? 'active' : 'disabled'}`}>
              <div className="step-header">
                <div className="step-number">4</div>
                <h2>Generated Result</h2>
              </div>
              {step === 4 && (
                <div className="step-body">
                  <div className="output-container">
                    <pre className="markdown-output">{generatedMarkdown}</pre>
                  </div>
                  <div className="btn-group" style={{marginTop: '1.5rem'}}>
                    <button className="btn outline" onClick={() => setStep(3)}>Start Over</button>
                    <button className="btn primary" onClick={() => {
                       const blob = new Blob([generatedMarkdown], { type: 'text/markdown' });
                       const url = URL.createObjectURL(blob);
                       const a = document.createElement('a');
                       a.href = url;
                       a.download = `${ticketId}_TestPlan.md`;
                       a.click();
                    }}>💾 Download as Markdown</button>
                  </div>
                </div>
              )}
            </div>
            
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
