import React, { useState, useRef, useEffect } from 'react';
import MessageBubble from '../components/MessageBubble';
import FollowUpChips from '../components/FollowUpChips';
import { Send } from 'lucide-react';

const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [followups, setFollowups] = useState([]);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, followups]);

  const handleSubmit = async (e, customValue = null) => {
    e?.preventDefault();
    const queryText = customValue || inputValue;
    if (!queryText.trim() || isLoading) return;

    const userMsg = { role: 'user', content: queryText };
    setMessages((prev) => [...prev, userMsg]);
    setInputValue('');
    setFollowups([]);
    setIsLoading(true);

    let botMsgId = Date.now();
    // Added 'isStreaming' tracking property to flag animation triggers
    setMessages((prev) => [...prev, { id: botMsgId, role: 'bot', content: '', sources: [], isStreaming: true }]);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userMsg.content }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            if (!dataStr) continue;
            
            try {
              const data = JSON.parse(dataStr);
              if (data.type === 'token') {
                setMessages((prev) =>
                  prev.map((m) => (m.id === botMsgId ? { ...m, content: m.content + data.content } : m))
                );
              } else if (data.type === 'sources') {
                setMessages((prev) =>
                  prev.map((m) => (m.id === botMsgId ? { ...m, sources: data.content } : m))
                );
              } else if (data.type === 'followups') {
                setFollowups(data.content);
              }
            } catch (err) {
              console.error("Parse err", err);
            }
          }
        }
      }
    } catch (error) {
      console.error(error);
    } finally {
      setIsLoading(false);
      // Turn off streaming animation flag
      setMessages((prev) =>
        prev.map((m) => (m.id === botMsgId ? { ...m, isStreaming: false } : m))
      );
    }
  };

  const handleSelectFollowup = (question) => {
    handleSubmit(null, question);
  };

  return (
    <div className="chat-container">
      <div className="messages-area">
        {messages.length === 0 ? (
          <div className="brand" style={{ textAlign: 'center', marginTop: 'auto', marginBottom: 'auto', fontSize: '3rem' }}>
            The Secretariat
          </div>
        ) : (
          messages.map((msg, idx) => (
            <MessageBubble 
              key={msg.id || idx} 
              message={msg} 
            />
          ))
        )}
        
        {followups.length > 0 && (
          <FollowUpChips questions={followups} onSelect={handleSelectFollowup} />
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        <form className="input-form" onSubmit={(e) => handleSubmit(e)}>
          <input
            type="text"
            className="chat-input"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask about a government Policies..."
          />
          <button type="submit" className="send-btn" disabled={isLoading}>
            <Send size={20} />
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatPage;
