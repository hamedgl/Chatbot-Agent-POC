import { useState, useEffect } from 'react';
import { Bot, RefreshCw, AlertCircle } from 'lucide-react';
import Chat from './components/Chat';
import Dashboard from './components/Dashboard';
import ChatHistory from './components/ChatHistory';

// ?? not || so that VITE_API_URL="" (empty string for AWS) is respected,
// while undefined (not set at all, e.g. local dev) falls back to localhost
const FASTAPI_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

function generateSessionId() {
  return Math.random().toString(36).substring(2, 15);
}

function getStoredSessionId() {
  let sid = localStorage.getItem('chat_session_id');
  if (!sid) {
    sid = generateSessionId();
    localStorage.setItem('chat_session_id', sid);
  }
  return sid;
}

export default function App() {
  const [sessionId, setSessionId] = useState(getStoredSessionId);
  const [messages, setMessages] = useState([]);

  // Dashboard states
  const [profile, setProfile] = useState(null);
  const [hobbies, setHobbies] = useState(null);
  const [events, setEvents] = useState(null);
  const [settings, setSettings] = useState(null);
  const [backendConnected, setBackendConnected] = useState(true);

  // Streaming states
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [streamingTraces, setStreamingTraces] = useState([]);
  const [pendingConfirmation, setPendingConfirmation] = useState(false);

  // History panel refresh trigger
  const [sessionsVersion, setSessionsVersion] = useState(0);

  // ── Fetch helpers ─────────────────────────────────────────────────────────

  const fetchDashboardData = async () => {
    try {
      const endpoints = ['/api/profile', '/api/hobbies', '/api/events', '/api/settings'];
      const [profRes, hobRes, eveRes, setRes] = await Promise.all(
        endpoints.map(ep =>
          fetch(`${FASTAPI_URL}${ep}`).then(r => {
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            return r.json();
          })
        )
      );
      setProfile(profRes.data);
      setHobbies(hobRes.data);
      setEvents(eveRes.data);
      setSettings(setRes.data);
      setBackendConnected(true);
    } catch (err) {
      console.error('Failed to connect to backend:', err);
      setBackendConnected(false);
    }
  };

  const fetchSessionHistory = async (sid) => {
    try {
      const res = await fetch(`${FASTAPI_URL}/api/history/${sid}`);
      const data = await res.json();
      return (data.data || []).map(m => ({ role: m.role, content: m.content }));
    } catch {
      return [];
    }
  };

  // ── Startup ───────────────────────────────────────────────────────────────

  useEffect(() => {
    fetchDashboardData();
    fetchSessionHistory(sessionId).then(history => {
      if (history.length > 0) setMessages(history);
    });
  }, []);

  // ── Session switching ─────────────────────────────────────────────────────

  const handleSessionSelect = async (newSid) => {
    if (newSid === sessionId) return;
    localStorage.setItem('chat_session_id', newSid);
    setSessionId(newSid);
    setIsStreaming(false);
    setStreamingText('');
    setStreamingTraces([]);
    setPendingConfirmation(false);
    const history = await fetchSessionHistory(newSid);
    setMessages(history);
  };

  const handleNewSession = () => {
    const newSid = generateSessionId();
    localStorage.setItem('chat_session_id', newSid);
    setSessionId(newSid);
    setMessages([]);
    setIsStreaming(false);
    setStreamingText('');
    setStreamingTraces([]);
    setPendingConfirmation(false);
    setSessionsVersion(v => v + 1);
  };

  // ── Chat ──────────────────────────────────────────────────────────────────

  const handleSendMessage = async (text) => {
    if (isStreaming && !pendingConfirmation) return;

    const newUserMessage = { role: 'user', content: text };
    setMessages(prev => [...prev, newUserMessage]);

    setIsStreaming(true);
    setStreamingText('');
    setStreamingTraces([]);
    setPendingConfirmation(false);

    try {
      const response = await fetch(`${FASTAPI_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: sessionId })
      });

      if (!response.ok) throw new Error(`Server error: ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let textAccumulator = '';
      let tracesList = [];
      let isConfPending = false;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          try {
            const event = JSON.parse(trimmed);
            if (event.type === 'trace') {
              tracesList = [...tracesList, event.message];
              setStreamingTraces(tracesList);
            } else if (event.type === 'confirmation') {
              isConfPending = true;
              setPendingConfirmation(true);
              textAccumulator = event.message;
              setStreamingText(textAccumulator);
            } else if (event.type === 'content') {
              textAccumulator += event.delta;
              setStreamingText(textAccumulator);
            } else if (event.type === 'error') {
              textAccumulator = `Error: ${event.message}`;
              setStreamingText(textAccumulator);
            }
          } catch (e) {
            console.warn('Failed to parse SSE JSON line:', trimmed, e);
          }
        }
      }

      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: textAccumulator,
          traces: tracesList.length > 0 ? tracesList : null
        }
      ]);

      if (!isConfPending) {
        setIsStreaming(false);
        setStreamingText('');
        setStreamingTraces([]);
        setPendingConfirmation(false);
        setSessionsVersion(v => v + 1); // refresh history panel after each completed turn
      }

      fetchDashboardData();

    } catch (error) {
      console.error('Chat streaming failed:', error);
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: `Unable to stream response from backend. Error: ${error.message}` }
      ]);
      setIsStreaming(false);
    }
  };

  // ── Reset ─────────────────────────────────────────────────────────────────

  const handleResetDatabase = async () => {
    try {
      const response = await fetch(`${FASTAPI_URL}/api/reset`, { method: 'POST' });
      if (response.ok) {
        setMessages([]);
        setStreamingText('');
        setStreamingTraces([]);
        setPendingConfirmation(false);
        setIsStreaming(false);
        setSessionsVersion(v => v + 1);
        await fetchDashboardData();
      }
    } catch (e) {
      console.error('Failed to reset database:', e);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="app-container">
      {/* LEFT SIDEBAR */}
      <aside className="sidebar">
        <div className="sidebar-top">
          <div className="brand">
            <Bot className="brand-icon" size={28} />
            <h1 className="brand-name">Chatbot Agent POC</h1>
          </div>

          <p className="poc-description">
            This proof-of-concept showcases natural-language database tool-calling with an SQLite DB,
            FastAPI server, and a fully interactive React UI.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)' }}>System Info</span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                LLM: <code>{FASTAPI_URL ? 'Amazon Bedrock' : 'LM Studio (local)'}</code>
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                API: <code>{FASTAPI_URL || 'localhost:8000'}</code>
              </div>
            </div>
          </div>
        </div>

        {/* CHAT HISTORY PANEL */}
        <ChatHistory
          apiUrl={FASTAPI_URL}
          currentSessionId={sessionId}
          refreshVersion={sessionsVersion}
          onSessionSelect={handleSessionSelect}
          onNewSession={handleNewSession}
        />

        {/* BOTTOM CONTROLS */}
        <div className="sidebar-bottom">
          <button className="btn-reset" onClick={handleResetDatabase}>
            <RefreshCw size={16} />
            Reset Demo Data
          </button>
          <div className="sidebar-meta">
            Session: {sessionId.substring(0, 8)}…
          </div>
        </div>
      </aside>

      {/* WORKSPACE */}
      <main className="workspace">
        {backendConnected ? (
          <>
            <Chat
              messages={messages}
              onSendMessage={handleSendMessage}
              isStreaming={isStreaming}
              streamingText={streamingText}
              streamingTraces={streamingTraces}
              pendingConfirmation={pendingConfirmation}
            />
            <Dashboard
              profile={profile}
              hobbies={hobbies}
              events={events}
              settings={settings}
              loading={isStreaming}
            />
          </>
        ) : (
          <div className="offline-banner">
            <AlertCircle size={40} />
            <h3>🔌 Backend Connection Lost</h3>
            <p>
              We are unable to reach the FastAPI server. Please check that your terminal backend is
              running on <code>port 8000</code> and restart uvicorn.
            </p>
            <button
              className="btn-cancel"
              style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '8px', margin: '12px auto' }}
              onClick={fetchDashboardData}
            >
              <RefreshCw size={14} /> Retry Connection
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
