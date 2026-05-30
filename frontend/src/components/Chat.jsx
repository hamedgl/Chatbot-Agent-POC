import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, Terminal, ChevronDown, ChevronUp, 
  AlertTriangle, Check, X, Bot, User, Mic, MicOff, Volume2, VolumeX 
} from 'lucide-react';

export default function Chat({ 
  messages, 
  onSendMessage, 
  isStreaming, 
  streamingText, 
  streamingTraces, 
  pendingConfirmation 
}) {
  const [input, setInput] = useState('');
  const chatEndRef = useRef(null);
  
  // Voice state (Text-to-Speech)
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const prevStreamingRef = useRef(isStreaming);

  // Handle text-to-voice when streaming finishes
  useEffect(() => {
    if (prevStreamingRef.current && !isStreaming && voiceEnabled && messages.length > 0) {
      const lastMsg = messages[messages.length - 1];
      if (lastMsg.role === 'assistant' && lastMsg.content) {
        speakText(lastMsg.content);
      }
    }
    prevStreamingRef.current = isStreaming;
  }, [isStreaming, voiceEnabled, messages]);

  const speakText = (text) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    // Clean markdown characters so it reads naturally
    const cleanText = text.replace(/[*#_`~]/g, '');
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = 'en-US';
    window.speechSynthesis.speak(utterance);
  };

  const toggleVoice = () => {
    const nextState = !voiceEnabled;
    setVoiceEnabled(nextState);
    if (!nextState && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  };

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingText, streamingTraces, pendingConfirmation]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    onSendMessage(input.trim());
    setInput('');
  };

  return (
    <div className="chat-container">
      {/* Chat Header */}
      <div className="chat-header">
        <Bot size={22} className="brand-icon" />
        <div style={{ flex: 1 }}>
          <h2 style={{ fontSize: '16px', fontWeight: '700' }}>AI Assistant</h2>
          <span style={{ fontSize: '11px', color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--success)', display: 'inline-block' }}></span>
            Gemma 4 Connected
          </span>
        </div>
        
        {/* Voice Output Toggle */}
        <button 
          onClick={toggleVoice} 
          className="voice-toggle-btn"
          title={voiceEnabled ? "Mute agent voice" : "Enable agent voice"}
          style={{ 
            background: 'none', border: 'none', color: voiceEnabled ? 'var(--primary)' : 'var(--text-muted)', 
            cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '8px' 
          }}
        >
          {voiceEnabled ? <Volume2 size={20} /> : <VolumeX size={20} />}
        </button>
      </div>

      {/* Messages History */}
      <div className="chat-history">
        {messages.length === 0 ? (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', gap: '12px' }}>
            <Bot size={40} style={{ opacity: 0.4 }} />
            <p style={{ fontSize: '14px', textAlign: 'center', maxWidth: '300px' }}>
              Hello! I can view and update your profile, hobbies, calendar events, and preferences. Ask me anything!
            </p>
          </div>
        ) : (
          messages.map((msg, index) => (
            <div className={`message ${msg.role}`} key={index}>
              <div className="msg-avatar">
                {msg.role === 'user' ? <User size={18} /> : <Bot size={18} />}
              </div>
              
              <div className="msg-content-wrapper">
                {/* Visual Tool Traces Expander */}
                {msg.traces && msg.traces.length > 0 && (
                  <ToolTraces traces={msg.traces} />
                )}
                
                <div className="msg-bubble">
                  {msg.content}
                </div>
              </div>
            </div>
          ))
        )}

        {/* Streaming / Active Agent Turn Rendering */}
        {isStreaming && (
          <div className="message assistant">
            <div className="msg-avatar">
              <Bot size={18} />
            </div>
            <div className="msg-content-wrapper" style={{ width: '100%' }}>
              {streamingTraces && streamingTraces.length > 0 && (
                <ToolTraces traces={streamingTraces} defaultExpanded={true} />
              )}
              
              {(streamingText || pendingConfirmation) && (
                <div className="msg-bubble">
                  {streamingText}
                  {isStreaming && !pendingConfirmation && <span className="typewriter-cursor">▌</span>}
                  
                  {/* Visual Confirmation Panel */}
                  {pendingConfirmation && (
                    <div className="confirmation-panel">
                      <div className="confirmation-prompt">
                        <AlertTriangle size={16} style={{ color: 'var(--warning)' }} />
                        <span>Action requires explicit validation</span>
                      </div>
                      <div className="confirmation-buttons">
                        <button 
                          className="btn-confirm" 
                          onClick={() => onSendMessage('Yes')}
                        >
                          <Check size={14} style={{ display: 'inline-block', marginRight: '4px' }} />
                          Confirm Action
                        </button>
                        <button 
                          className="btn-cancel" 
                          onClick={() => onSendMessage('No')}
                        >
                          <X size={14} style={{ display: 'inline-block', marginRight: '4px' }} />
                          Cancel Action
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
        
        <div ref={chatEndRef} />
      </div>

      {/* Input Form */}
      <div className="chat-input-area">
        <form onSubmit={handleSubmit} className="chat-form">
          <input 
            type="text" 
            className="chat-input"
            placeholder={isStreaming ? "Thinking..." : "Ask to add hobbies, create events..."}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isStreaming}
          />
          <button 
            type="submit" 
            className="btn-send"
            disabled={isStreaming || !input.trim()}
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}

// Collapsible Tool Traces sub-component
function ToolTraces({ traces, defaultExpanded = false }) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div className="tool-traces-expander">
      <div className="tool-traces-header" onClick={() => setExpanded(!expanded)}>
        <Terminal size={14} />
        <span style={{ flex: 1 }}>🔧 Tool Execution Log ({traces.length})</span>
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </div>
      
      {expanded && (
        <div className="tool-traces-body">
          {traces.map((trace, i) => {
            const isSuccess = trace.includes('✅') || trace.includes('Executing');
            const isError = trace.includes('❌') || trace.includes('🚫');
            let traceClass = '';
            if (isSuccess) traceClass = 'success';
            if (isError) traceClass = 'error';
            
            return (
              <div className={`trace-line ${traceClass}`} key={i}>
                {trace}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
