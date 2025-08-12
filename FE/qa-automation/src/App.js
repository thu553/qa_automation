// src/App.jsx
import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate, Navigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import AuthForm from './components/AuthForm.jsx';
import SearchForm from './components/SearchForm.jsx';
import UnansweredList from './components/UnansweredList.jsx';
import AdminDashboard from './components/admin/AdminDashboard';
import UserManagement from './components/admin/UserManagement';
import ConsultManagement from './components/admin/ConsultManagement';
import SideNav from './components/admin/SideNav';

const App = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const token = localStorage.getItem('token');
    const role = localStorage.getItem('role');
    const [apiError, setApiError] = useState(''); // Lưu lỗi API tạm thời

    // Xử lý đăng xuất
    const handleLogout = async () => {
        try {
            await axios.post('/api/auth/logout', {}, {
                headers: { Authorization: `Bearer ${token}` },
            });
        } catch (err) {
            console.error('Lỗi khi đăng xuất:', err);
        } finally {
            localStorage.removeItem('token');
            localStorage.removeItem('role');
            localStorage.removeItem('email');
            navigate('/login');
        }
    };

    // Kiểm tra trạng thái đăng nhập
    useEffect(() => {
        if (!token && !apiError) {
            if (location.pathname !== '/login' && location.pathname !== '/register') {
                navigate('/login');
            }
        } else if (token && role === 'ADMIN' && !location.pathname.startsWith('/admin')) {
            navigate('/admin/dashboard');
        } else if (token && role === 'CONSULTANT' && location.pathname !== '/consult') {
            navigate('/consult');
        } else if (token && role === 'USER' && location.pathname !== '/search') {
            navigate('/search');
        }
    }, [token, role, navigate, location.pathname, apiError]);

    // Component bảo vệ route theo vai trò
    const AdminRoute = ({ children }) => {
        return token && role === 'ADMIN' ? (
            <div className="flex">
                <SideNav />
                <div className="flex-1">{children}</div>
            </div>
        ) : (
            <Navigate to="/login" />
        );
    };

    const ConsultantRoute = ({ children }) => {
        return token && role === 'CONSULTANT' ? children : <Navigate to="/login" />;
    };

    const UserRoute = ({ children }) => {
        return token && role === 'USER' ? children : <Navigate to="/login" />;
    };

    return (
        <div className="min-h-screen bg-gray-100">
            {token && (
                <nav className="bg-blue-600 p-4 text-white flex justify-between items-center">
                    <h1 className="text-xl font-bold">Hệ thống Hỏi Đáp</h1>
                    <button
                        onClick={handleLogout}
                        className="bg-red-500 p-2 rounded hover:bg-red-600"
                    >
                        Đăng xuất
                    </button>
                </nav>
            )}
            <Routes>
                <Route path="/login" element={<AuthForm isRegister={false} />} />
                <Route path="/register" element={<AuthForm isRegister={true} />} />
                <Route
                    path="/search"
                    element={
                        <UserRoute>
                            <SearchForm />
                        </UserRoute>
                    }
                />
                <Route
                    path="/consult"
                    element={
                        <ConsultantRoute>
                            <UnansweredList />
                        </ConsultantRoute>
                    }
                />
                <Route
                    path="/admin/dashboard"
                    element={
                        <AdminRoute>
                            <AdminDashboard />
                        </AdminRoute>
                    }
                />
                <Route
                    path="/admin/users"
                    element={
                        <AdminRoute>
                            <UserManagement setApiError={setApiError} />
                        </AdminRoute>
                    }
                />
                <Route
                    path="/admin/consults"
                    element={
                        <AdminRoute>
                            <ConsultManagement />
                        </AdminRoute>
                    }
                />
                <Route
                    path="/"
                    element={
                        <Navigate
                            to={
                                token
                                    ? role === 'ADMIN'
                                        ? '/admin/dashboard'
                                        : role === 'CONSULTANT'
                                            ? '/consult'
                                            : '/search'
                                    : '/login'
                            }
                        />
                    }
                />
            </Routes>
        </div>
    );
};

export default App;