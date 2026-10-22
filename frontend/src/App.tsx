import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from './components/Layout/MainLayout';

const Dashboard = lazy(() => import('./pages/Dashboard').then((module) => ({ default: module.Dashboard })));
const IntentManagement = lazy(() => import('./pages/IntentManagement').then((module) => ({ default: module.IntentManagement })));
const Topology = lazy(() => import('./pages/Topology').then((module) => ({ default: module.Topology })));
const Configurations = lazy(() => import('./pages/Configurations').then((module) => ({ default: module.Configurations })));
const VerificationCenter = lazy(() => import('./pages/VerificationCenter').then((module) => ({ default: module.VerificationCenter })));
const Repairs = lazy(() => import('./pages/Repairs').then((module) => ({ default: module.Repairs })));
const Simulation = lazy(() => import('./pages/Simulation').then((module) => ({ default: module.Simulation })));
const Audit = lazy(() => import('./pages/Audit').then((module) => ({ default: module.Audit })));
const Settings = lazy(() => import('./pages/Settings').then((module) => ({ default: module.Settings })));

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className="p-8 text-sm text-slate-400">Loading page…</div>}>
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
      </Suspense>
    </BrowserRouter>
  );
}

export default App;

