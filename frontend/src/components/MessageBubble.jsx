import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const MessageBubble = ({ message }) => {
  const isBot = message.role === 'bot';
  
  return (
    <div className={`message-bubble ${isBot ? 'message-bot glass' : 'message-user'}`}>
      <div className="markdown-content">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {message.content || (isBot ? "Generating..." : "")}
        </ReactMarkdown>
      </div>

      {/* Live AI Status Animation */}
      {isBot && message.isStreaming && (
        <div className="streaming-indicator">
          <span className="streaming-dot"></span>
          <span className="streaming-dot"></span>
          <span className="streaming-dot"></span>
          <span style={{ marginLeft: '4px', fontWeight: '600' }}>AI Live Response</span>
        </div>
      )}

      {isBot && message.sources && message.sources.length > 0 && (
        <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border)', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          <strong>Sources:</strong> {message.sources.map(s => `[Doc ${s.doc_id}]`).join(', ')}
        </div>
      )}
    </div>
  );
};

export default MessageBubble;