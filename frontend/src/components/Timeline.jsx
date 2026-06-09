import React from 'react';

const Timeline = ({ events }) => {
  if (!events || events.length === 0) return null;
  
  return (
    <div className="timeline-container">
      {events.map((e, idx) => (
        <div key={idx} className="timeline-item glass">
          <div className="timeline-year">{e.year}</div>
          <div className="timeline-title">{e.title}</div>
          <div className="timeline-desc">{e.description}</div>
        </div>
      ))}
    </div>
  );
};

export default Timeline;
