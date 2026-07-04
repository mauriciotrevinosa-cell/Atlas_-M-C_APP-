import { useState } from 'react';
import { Dashboard } from './components/Dashboard.jsx';
import { Login } from './components/Login.jsx';

export const App = () => {
  const [authenticated, setAuthenticated] = useState(true);

  if (!authenticated) {
    return <Login onLogin={() => setAuthenticated(true)} />;
  }

  return <Dashboard onLogout={() => setAuthenticated(false)} />;
};
