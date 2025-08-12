import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { BrowserRouter } from 'react-router-dom';
import axios from 'axios';

// Thiết lập interceptor cho axios để xử lý lỗi 401
axios.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && error.response.status === 401 &&
            error.config.url !== '/api/auth/login') {
            localStorage.removeItem('token');
            localStorage.removeItem('role');
            localStorage.removeItem('email');
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
    <React.StrictMode>
        <BrowserRouter>
            <App />
        </BrowserRouter>
    </React.StrictMode>
);