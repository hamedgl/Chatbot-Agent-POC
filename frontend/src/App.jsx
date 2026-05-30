import React, { useState, useEffect } from 'react';
import { Bot, RefreshCw, AlertCircle, Database, HelpCircle } from 'lucide-react';
import Chat from './components/Chat';
import Dashboard from './components/Dashboard';

const FASTAPI_URL = 'http://localhost:8000';

// Generate a random session ID on startup
const getSessionId = () => {
  let sid = localStorage.getItem('chat_session_id');
  if (!sid) {
    sid = Math.random().toString(36).substring(2, 15);
    localStorage.setItem('chat_session_id', sid);
  }
  return sid;
};

export default function App() {
  const [sessionId] = useState(getSessionId);
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

  // Fetch dashboard data
  const fetchDashboardData = async () => {
    try {
      const endpoints = ['/api/profile', '/api/hobbies', '/api/events', '/api/settings'];
      const [profRes, hobRes, eveRes, setRes] = await Promise.all(
        endpoints.map(endpoint => 
          fetch(`${FASTAPI_URL}${endpoint}`).then(res => {
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return res.json();
          })
        )
      );

      setProfile(profRes.data);
      setHobbies(hobRes.data);
      setEvents(eveRes.data);
      setSettings(setRes.data);
      setBackendConnected(true);
    } catch (err) {
      console.error("Failed to connect to backend:", err);
      setBackendConnected(false);
    }
  };

  // Run on startup
  useEffect(() => {
    fetchDashboardData();
  }, []);

  // Send a message and handle Server-Sent Events (SSE) stream
  const handleSendMessage = async (text) => {
    if (isStreaming && !pendingConfirmation) return;

    // 1. Append user message to UI chat log
    const newUserMessage = { role: 'user', content: text };
    const updatedMessages = [...messages, newUserMessage];
    setMessages(updatedMessages);

    // 2. Prepare streaming state
    setIsStreaming(true);
    setStreamingText('');
    setStreamingTraces([]);
    setPendingConfirmation(false);

    try {
      // 3. Initiate post request to FastAPI chat
      const response = await fetch(`${FASTAPI_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: sessionId })
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      // 4. Initialize stream reader
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
        
        // Save the last partial line back to buffer
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
            } else if (event.type === 'done') {
              // End of this turn's response
            }
          } catch (e) {
            console.warn("Failed to parse SSE JSON line:", trimmed, e);
          }
        }
      }

      // 5. Finalize turn and save assistant message to history
      setMessages(prev => [
        ...prev, 
        { 
          role: 'assistant', 
          content: textAccumulator, 
          traces: tracesList.length > 0 ? tracesList : null 
        }
      ]);

      // If a confirmation is pending, we keep isStreaming true so the buttons stay clickable
      if (!isConfPending) {
        setIsStreaming(false);
        setStreamingText('');
        setStreamingTraces([]);
        setPendingConfirmation(false);
      }

      // 6. Refresh the data panel to show changes in real-time
      fetchDashboardData();

    } catch (error) {
      console.error("Chat streaming failed:", error);
      setMessages(prev => [
        ...prev, 
        { 
          role: 'assistant', 
          content: `Unable to stream response from backend. Error: ${error.message}` 
        }
      ]);
      setIsStreaming(false);
    }
  };

  // Reset database handler
  const handleResetDatabase = async () => {
    try {
      const response = await fetch(`${FASTAPI_URL}/api/reset`, { method: 'POST' });
      if (response.ok) {
        setMessages([]); // Clear chat logs
        setStreamingText('');
        setStreamingTraces([]);
        setPendingConfirmation(false);
        setIsStreaming(false);
        await fetchDashboardData(); // Load clean database seed
      }
    } catch (e) {
      console.error("Failed to reset database:", e);
    }
  };

  return (
    <div className="app-container">
      {/* LEFT SIDEBAR CONTROLS */}
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
                LLM Mode: <code>gemma-4</code>
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Server: <code>localhost:1235</code>
              </div>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <button className="btn-reset" onClick={handleResetDatabase}>
            <RefreshCw size={16} />
            Reset Demo Data
          </button>
          
          <div className="sidebar-meta">
            Session: {sessionId.substring(0, 8)}...
          </div>
        </div>
      </aside>

      {/* WORKSPACE AREA */}
      <main className="workspace">
        {backendConnected ? (
          <>
            {/* Chat Panel */}
            <Chat 
              messages={messages} 
              onSendMessage={handleSendMessage}
              isStreaming={isStreaming}
              streamingText={streamingText}
              streamingTraces={streamingTraces}
              pendingConfirmation={pendingConfirmation}
            />
            
            {/* Dashboard Panel */}
            <Dashboard 
              profile={profile} 
              hobbies={hobbies}
              events={events}
              settings={settings}
              loading={isStreaming}
            />
          </>
        ) : (
          /* Offline Connection Banner */
          <div className="offline-banner">
            <AlertCircle size={40} />
            <h3>🔌 Backend Connection Lost</h3>
            <p>
              We are unable to reach the FastAPI server. Please check that your terminal backend is running on <code>port 8000</code> and restart uvicorn.
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
