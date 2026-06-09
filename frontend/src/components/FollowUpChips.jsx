import React from 'react';
import { MessageCircle } from 'lucide-react';

const FollowUpChips = ({ questions, onSelect }) => {
  return (
    <div className="followups">
      {questions.map((q, idx) => (
        <div key={idx} className="chip glass" onClick={() => onSelect(q)}>
          <MessageCircle size={14} style={{ display: 'inline', marginRight: '5px', verticalAlign: 'middle' }} />
          {q}
        </div>
      ))}
    </div>
  );
};

export default FollowUpChips;
