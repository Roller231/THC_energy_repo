import React, { useState } from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import OverConsumersPage from './pages/OverConsumersPage';
import ClientsPage from './pages/ClientsPage';

function App() {
  const [tab, setTab] = useState<'violations' | 'clients'>('violations');
  return (
    <div>
      <nav className="p-4 bg-gray-100 space-x-4">
        <button onClick={() => setTab('violations')}>Нарушители</button>
        <button onClick={() => setTab('clients')}>Клиенты</button>
      </nav>
      {tab === 'violations' ? <OverConsumersPage /> : <ClientsPage />}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
