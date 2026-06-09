import React, { useState, useEffect } from 'react';

const AdminPage = () => {
  // Config states
  const [primaryLlm, setPrimaryLlm] = useState('gpt-4o');
  const [fallbackLlm, setFallbackLlm] = useState('gpt-3.5-turbo');
  const [apiKey, setApiKey] = useState('');
  
  // Keyword management states
  const [keywords, setKeywords] = useState(['restricted_policy_alpha', 'confidential_internal']);
  const [newKeyword, setNewKeyword] = useState('');
  
  // Status message trackers
  const [status, setStatus] = useState({ message: '', type: '' });

  // Fetch initial config values from FastAPI on page mount
  useEffect(() => {
    fetch('http://localhost:8000/api/admin/config')
      .then(res => res.json())
      .then(data => {
        if (data) {
          setPrimaryLlm(data.primary_llm || 'gpt-4o');
          setFallbackLlm(data.fallback_llm || 'gpt-3.5-turbo');
          setApiKey(data.api_key || '');
          setKeywords(data.restricted_keywords || []);
        }
      })
      .catch(err => console.error("Error loading admin configurations:", err));
  }, []);

  const showStatus = (message, type) => {
    setStatus({ message, type });
    setTimeout(() => setStatus({ message: '', type: '' }), 4000);
  };

  // Submit configuration changes to Backend
  const handleSaveConfig = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('http://localhost:8000/api/admin/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ primary_llm: primaryLlm, fallback_llm: fallbackLlm, api_key: apiKey })
      });
      if (response.ok) showStatus('LLM Configurations updated successfully!', 'success');
      else showStatus('Failed to update system configurations.', 'error');
    } catch (err) {
      showStatus('Network connection failure.', 'error');
    }
  };

  // Add new restricted validation keyword
  const handleAddKeyword = (e) => {
    e.preventDefault();
    if (!newKeyword.trim()) return;
    if (keywords.includes(newKeyword.trim())) {
      showStatus('Keyword already exists.', 'error');
      return;
    }
    const updatedKeywords = [...keywords, newKeyword.trim()];
    setKeywords(updatedKeywords);
    setNewKeyword('');
    saveKeywordsToBackend(updatedKeywords);
  };

  // Remove restricted validation keyword
  const handleDeleteKeyword = (keywordToDelete) => {
    const updatedKeywords = keywords.filter(k => k !== keywordToDelete);
    setKeywords(updatedKeywords);
    saveKeywordsToBackend(updatedKeywords);
  };

  const saveKeywordsToBackend = async (keywordList) => {
    try {
      await fetch('http://localhost:8000/api/admin/keywords', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keywords: keywordList })
      });
      showStatus('Security keywords updated.', 'success');
    } catch (err) {
      console.error('Failed to sync security keywords:', err);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '900px', margin: '0 auto', color: '#fff' }}>
      <h1 className="brand" style={{ fontSize: '2.5rem', marginBottom: '2rem' }}>Admin Dashboard</h1>
      
      {/* Global Status Banner Alert */}
      {status.message && (
        <div style={{
          padding: '1rem', 
          marginBottom: '1.5rem', 
          borderRadius: '8px',
          backgroundColor: status.type === 'success' ? '#1b4332' : '#641212',
          border: `1px solid ${status.type === 'success' ? '#2d6a4f' : '#a41616'}`
        }}>
          {status.message}
        </div>
      )}

      {/* SECTION 1: LLM Parameters configuration profile */}
      <div className="glass" style={{ padding: '2rem', marginBottom: '2rem', borderRadius: '12px' }}>
        <h2 style={{ borderBottom: '1px solid #333', paddingBottom: '0.5rem', marginBottom: '1.5rem' }}>LLM Configuration</h2>
        <form onSubmit={handleSaveConfig} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          <div style={{ display: 'flex', gap: '2rem' }}>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.9rem', fontWeight: 'bold' }}>Primary LLM Model Engine</label>
              <select 
                value={primaryLlm} 
                onChange={(e) => setPrimaryLlm(e.target.value)}
                style={{ padding: '0.7rem', borderRadius: '6px', background: '#222', color: '#fff', border: '1px solid #44' }}
              >
                <option value="gpt-4o">OpenAI GPT-4o (Recommended)</option>
                <option value="gpt-4-turbo">OpenAI GPT-4 Turbo</option>
                <option value="claude-3-5-sonnet">Anthropic Claude 3.5 Sonnet</option>
                <option value="llama-3-70b">Meta Llama 3 70B (Local)</option>
              </select>
            </div>

            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.9rem', fontWeight: 'bold' }}>Fallback Failure Chain Model</label>
              <select 
                value={fallbackLlm} 
                onChange={(e) => setFallbackLlm(e.target.value)}
                style={{ padding: '0.7rem', borderRadius: '6px', background: '#222', color: '#fff', border: '1px solid #444' }}
              >
                <option value="gpt-3.5-turbo">OpenAI GPT-3.5 Turbo</option>
                <option value="llama-3-8b">Meta Llama 3 8B (Local)</option>
                <option value="mistral-7b">Mistral 7B (Fallback)</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <label style={{ fontSize: '0.9rem', fontWeight: 'bold' }}>Provider Secure Security Access Key (API Key)</label>
            <input 
              type="password" 
              value={apiKey} 
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-........................................"
              style={{ padding: '0.7rem', borderRadius: '6px', background: '#222', color: '#fff', border: '1px solid #444', fontFamily: 'monospace' }}
            />
          </div>

          <button type="submit" style={{ alignSelf: 'flex-start', padding: '0.7rem 2rem', cursor: 'pointer', fontWeight: 'bold' }}>
            Save Model Configuration
          </button>
        </form>
      </div>

      {/* SECTION 2: Guardrail Redaction Security Keyword Matrix */}
      <div className="glass" style={{ padding: '2rem', borderRadius: '12px' }}>
        <h2 style={{ borderBottom: '1px solid #333', paddingBottom: '0.5rem', marginBottom: '1.5rem' }}>Security Guardrail Keywords</h2>
        <p style={{ fontSize: '0.9rem', color: '#aaa', marginBottom: '1.5rem' }}>
          Manage phrase blocks. Queries containing these tokens will be stopped before running embeddings.
        </p>

        {/* Input Addition Grouping */}
        <form onSubmit={handleAddKeyword} style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
          <input 
            type="text" 
            value={newKeyword}
            onChange={(e) => setNewKeyword(e.target.value)}
            placeholder="Enter protected keyword or code signifier..."
            style={{ flexGrow: 1, padding: '0.7rem', borderRadius: '6px', background: '#222', color: '#fff', border: '1px solid #444' }}
          />
          <button type="submit" style={{ padding: '0.7rem 1.5rem', cursor: 'pointer' }}>Add Rule</button>
        </form>

        {/* Active Tag Chip Rendering Panel */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.7rem' }}>
          {keywords.length === 0 ? (
            <p style={{ fontStyle: 'italic', color: '#666' }}>No active keyword compliance rules established.</p>
          ) : (
            keywords.map((kw, index) => (
              <div 
                key={index} 
                style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '0.5rem', 
                  padding: '0.4rem 0.8rem', 
                  background: '#a41616', 
                  borderRadius: '20px',
                  fontSize: '0.85rem',
                  fontWeight: 'bold'
                }}
              >
                <span>{kw}</span>
                <button 
                  onClick={() => handleDeleteKeyword(kw)}
                  style={{ 
                    background: 'transparent', 
                    border: 'none', 
                    color: '#fff', 
                    cursor: 'pointer', 
                    fontSize: '1rem',
                    lineHeight: 1,
                    padding: 0
                  }}
                  title="Remove restriction rule"
                >
                  &times;
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminPage;