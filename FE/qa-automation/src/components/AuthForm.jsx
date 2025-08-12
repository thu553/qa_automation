import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate, Link } from 'react-router-dom';

const AuthForm = ({ isRegister }) => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(''); // Xóa lỗi cũ trước khi gửi yêu cầu
        try {
            const url = isRegister ? '/api/auth/register' : '/api/auth/login';
            const response = await axios.post(url, { email, password });
            if (!isRegister) {
                localStorage.setItem('token', response.data.token);
                localStorage.setItem('role', response.data.role);
                localStorage.setItem('email', response.data.email || email);
                if (response.data.role === 'ADMIN') {
                    navigate('/admin/dashboard');
                } else if (response.data.role === 'CONSULTANT') {
                    navigate('/consult');
                } else {
                    navigate('/search');
                }
            } else {
                navigate('/login');
            }
        } catch (err) {
            // Xử lý lỗi từ backend
            if (err.response) {
                // Backend trả về phản hồi với mã trạng thái (400, 401, 500, v.v.)
                const status = err.response.status;
                const data = err.response.data;

                if (status === 400 || status === 401) {
                    // Lỗi đăng nhập không hợp lệ
                    setError(data.message || 'Thông tin đăng nhập không hợp lệ');
                } else if (status === 500) {
                    setError('Lỗi server, vui lòng thử lại sau');
                } else {
                    setError(data.message || 'Đã có lỗi xảy ra');
                }
            } else if (err.request) {
                // Không nhận được phản hồi từ backend (mất kết nối)
                setError('Không thể kết nối đến server, vui lòng kiểm tra kết nối mạng');
            } else {
                // Lỗi khác (cấu hình axios, v.v.)
                setError('Đã có lỗi xảy ra: ' + err.message);
            }
        }
    };

    return (
        <div className="max-w-md mx-auto mt-10 p-6 bg-white rounded-lg shadow-lg">
            <h2 className="text-2xl font-bold mb-4">{isRegister ? 'Đăng ký' : 'Đăng nhập'}</h2>
            {error && (
                <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
                    {error}
                </div>
            )}
            <form onSubmit={handleSubmit}>
                <div className="mb-4">
                    <label className="block text-gray-700">Email</label>
                    <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full p-2 border rounded"
                        required
                    />
                </div>
                <div className="mb-4">
                    <label className="block text-gray-700">Mật khẩu</label>
                    <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full p-2 border rounded"
                        required
                    />
                </div>
                <button
                    type="submit"
                    className="w-full bg-blue-500 text-white p-2 rounded hover:bg-blue-600"
                >
                    {isRegister ? 'Đăng ký' : 'Đăng nhập'}
                </button>
            </form>
            <div className="mt-4 text-center text-sm text-gray-600">
                {isRegister ? (
                    <>
                        Đã có tài khoản?{' '}
                        <Link to="/login" className="text-blue-500 hover:underline">
                            Đăng nhập
                        </Link>
                    </>
                ) : (
                    <>
                        Chưa có tài khoản?{' '}
                        <Link to="/register" className="text-blue-500 hover:underline">
                            Đăng ký
                        </Link>
                    </>
                )}
            </div>
        </div>
    );
};

export default AuthForm;