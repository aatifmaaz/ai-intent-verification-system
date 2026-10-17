import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from './components/Layout/MainLayout';
import { Dashboard } from './pages/Dashboard';
import { IntentManagement } from './pages/IntentManagement';
import { Topology } from './pages/Topology';
import { Configurations } from './pages/Configurations';
import { VerificationCenter } from './pages/VerificationCenter';
import { Repairs } from './pages/Repairs';
import { Simulation } from './pages/Simulation';
import { Audit } from './pages/Audit';
import { Settings } from './pages/Settings';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="intents" element={<IntentManagement />} />
          <Route path="topology" element={<Topology />} />
          <Route path="configurations" element={<Configurations />} />
          <Route path="verification" element={<VerificationCenter />} />
          <Route path="repairs" element={<Repairs />} />
          <Route path="simulation" element={<Simulation />} />
          <Route path="audit" element={<Audit />} />
          <Route path="settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;

