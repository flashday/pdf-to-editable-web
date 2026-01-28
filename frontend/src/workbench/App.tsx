import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import WorkbenchPage from './pages/WorkbenchPage';

const App: React.FC = () => {
  return (
    <BrowserRouter basename="/workbench">
      <Routes>
        <Route path="/" element={<WorkbenchPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
