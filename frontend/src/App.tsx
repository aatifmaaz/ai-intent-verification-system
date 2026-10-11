import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from './components/Layout/MainLayout';
import { Dashboard } from './pages/Dashboard';
import { IntentManagement } from './pages/IntentManagement';
import { Topology } from './pages/Topology';
import { VerificationCenter } from './pages/VerificationCenter';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="intents" element={<IntentManagement />} />
          <Route path="topology" element={<Topology />} />
          <Route path="verification" element={<VerificationCenter />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
