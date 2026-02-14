import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { Layout } from './components/Layout';
import { RoleGuard } from './components/RoleGuard';
import { AdminDashboard } from './pages/AdminDashboard';
import { EmployerDashboard } from './pages/EmployerDashboard';
import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { WorkerDashboard } from './pages/WorkerDashboard';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            <Route element={<RoleGuard allow={['worker']} />}>
              <Route path="/worker" element={<WorkerDashboard />} />
            </Route>
            <Route element={<RoleGuard allow={['employer']} />}>
              <Route path="/employer" element={<EmployerDashboard />} />
            </Route>
            <Route element={<RoleGuard allow={['admin']} />}>
              <Route path="/admin" element={<AdminDashboard />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </React.StrictMode>
);
