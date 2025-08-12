import React, { useState } from 'react';
import axios from 'axios';
import Swal from 'sweetalert2';

const UserForm = ({ user, onClose, setApiError }) => {
    const [formData, setFormData] = useState({
        email: user?.email || '',
        password: '',
        role: user?.role || 'USER'
    });
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);
        try {
            const payload = { ...formData };
            if (!user && !payload.password) {
                throw new Error('Mật khẩu bắt buộc');
            }
            if (!payload.password) delete payload.password;
            const url = user ? `/api/admin/users/${user.id}` : '/api/admin/users';
            const method = user ? axios.put : axios.post;
            await method(url, payload, {
                headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
            });
            Swal.fire('Thành công', user ? 'Đã cập nhật' : 'Đã tạo người dùng', 'success');
            setApiError('');
            onClose();
        } catch (err) {
            const errorMsg = err.response?.data?.error || 'Lỗi khi lưu';
            setError(errorMsg);
            Swal.fire('Lỗi', errorMsg, 'error');
            setApiError(errorMsg);
            if (err.response?.status === 401 && errorMsg === 'Token hết hạn') {
                localStorage.removeItem('token');
                localStorage.removeItem('role');
                localStorage.removeItem('email');
            }
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
            <div className="bg-white p-4 rounded max-w-sm w-full">
                <h2 className="text-lg font-bold mb-4">{user ? 'Sửa' : 'Thêm'} người dùng</h2>
                <form onSubmit={handleSubmit}>
                    <div className="mb-4">
                        <label className="block text-gray-600">Email</label>
                        <input
                            type="email"
                            value={formData.email}
                            onChange={e => setFormData({ ...formData, email: e.target.value })}
                            className="w-full p-2 border rounded"
                            required
                        />
                    </div>
                    <div className="mb-4">
                        <label className="block text-gray-600">Mật khẩu {user && '(để trống nếu không đổi)'}</label>
                        <input
                            type="password"
                            value={formData.password}
                            onChange={e => setFormData({ ...formData, password: e.target.value })}
                            className="w-full p-2 border rounded"
                            required={!user}
                            disabled={isLoading}
                        />
                    </div>
                    <div className="mb-4">
                        <label className="block text-gray-600">Vai trò</label>
                        <select
                            value={formData.role}
                            onChange={e => setFormData({ ...formData, role: e.target.value })}
                            className="w-full p-2 border rounded"
                            required
                        >
                            <option value="USER">USER</option>
                            <option value="CONSULTANT">CONSULTANT</option>
                            <option value="ADMIN">ADMIN</option>
                        </select>
                    </div>
                    {error && <p className="text-red-500 mb-4">{error}</p>}
                    <div className="flex justify-end">
                        <button
                            type="button"
                            onClick={onClose}
                            className="mr-2 bg-gray-500 text-white p-2 rounded hover:bg-gray-600"
                            disabled={isLoading}
                        >
                            Hủy
                        </button>
                        <button
                            type="submit"
                            className="bg-blue-500 text-white p-2 rounded hover:bg-blue-600"
                            disabled={isLoading}
                        >
                            {isLoading ? 'Đang lưu...' : user ? 'Cập nhật' : 'Thêm'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default UserForm;