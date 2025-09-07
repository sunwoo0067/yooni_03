import React from 'react';
import ReactDOM from 'react-dom/client';
import PersonalApp from './PersonalApp';
import './index.css';

// React 18의 새로운 createRoot API 사용
const root = ReactDOM.createRoot(document.getElementById('root'));

root.render(
  <React.StrictMode>
    <PersonalApp />
  </React.StrictMode>
);