import React from 'react';
import { NavLink } from 'react-router-dom';
import { MessageSquare, Settings } from 'lucide-react';

const Sidebar = () => {
  return (
    <div className="sidebar">
      <div className="brand">The Secretariat Chatbot</div>
      
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        <NavLink 
          to="/" 
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <MessageSquare size={20} />
          Chat
        </NavLink>
        
        <NavLink 
          to="/admin" 
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <Settings size={20} />
          Admin Panel
        </NavLink>
      </nav>
    </div>
  );
};

export default Sidebar;
