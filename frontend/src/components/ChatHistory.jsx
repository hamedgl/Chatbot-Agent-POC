import React, { useState, useEffect } from 'react';
import { MessageSquare, Plus } from 'lucide-react';

function formatRelativeDate(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export default function ChatHistory({ apiUrl, currentSessionId, refreshVersion, onSessionSelect, onNewSession }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSessions();
  }, [refreshVersion, currentSessionId]);

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${apiUrl}/api/sessions`);
      const data = await res.json();
      setSessions(data.data || []);
    } catch {
      // silently fail — sidebar history is non-critical
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="history-panel">
      <div className="history-header">
        <span>Chat History</span>
        <button className="history-new-btn" onClick={onNewSession} title="Start a new chat">
          <Plus size={12} style={{ marginRight: '3px' }} />
          New
        </button>
      </div>

      <div className="history-list">
        {loading ? (
          <div className="history-empty">Loading…</div>
        ) : sessions.length === 0 ? (
          <div className="history-empty">No conversations yet</div>
        ) : (
          sessions.map(s => (
            <button
              key={s.session_id}
              className={`history-item ${s.session_id === currentSessionId ? 'active' : ''}`}
              onClick={() => onSessionSelect(s.session_id)}
              title={s.preview}
            >
              <MessageSquare size={11} className="history-item-icon" />
              <div className="history-item-body">
                <span className="history-item-preview">{s.preview}</span>
                <span className="history-item-meta">
                  {formatRelativeDate(s.last_at)} · {s.message_count} msgs
                </span>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
