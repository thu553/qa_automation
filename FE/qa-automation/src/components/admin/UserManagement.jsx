// src/components/admin/UserManagement.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Swal from 'sweetalert2';
import UserForm from './UserForm';

const UserManagement = ({ setApiError }) => {
    const [users, setUsers] = useState([]);
    const [error, setError] = useState('');
    const [showForm, setShowForm] = useState(false);
    const [selectedUser, setSelectedUser] = useState(null);
    const [loading, setLoading] = useState(false);

    // Lấy danh sách user
    const fetchUsers = async () => {
        setLoading(true);
        try {
            const response = await axios.get('/api/admin/users', {
                headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
            });
            setUsers(response.data);
            setError('');
            setApiError('');
        } catch (err) {
            const errorMsg = err.response?.data?.error || 'Lỗi khi tải danh sách người dùng';
            setError(errorMsg);
            setApiError(errorMsg);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchUsers();
    }, [setApiError]);

    // Xóa user
    const handleDelete = async (id) => {
        Swal.fire({
            title: 'Xác nhận xóa',
            text: 'Bạn có chắc muốn xóa người dùng này?',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Xóa',
            cancelButtonText: 'Hủy',
        }).then(async (result) => {
            if (result.isConfirmed) {
                setLoading(true);
                try {
                    await axios.delete(`/api/admin/users/${id}`, {
                        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
                    });
                    Swal.fire({
                        icon: 'success',
                        title: 'Thành công',
                        text: 'Đã xóa người dùng',
                    });
                    fetchUsers();
                } catch (err) {
                    const errorMsg = err.response?.data?.error || 'Lỗi khi xóa người dùng';
                    Swal.fire({
                        icon: 'error',
                        title: 'Lỗi',
                        text: errorMsg,
                    });
                    setApiError(errorMsg);
                    if (err.response?.status === 401 && err.response?.data?.error === 'Token hết hạn') {
                        localStorage.removeItem('token');
                        localStorage.removeItem('role');
                        localStorage.removeItem('email');
                    }
                } finally {
                    setLoading(false);
                }
            }
        });
    };

    // Mở form sửa user
    const handleEdit = (user) => {
        setSelectedUser(user);
        setShowForm(true);
    };

    // Đóng form
    const handleCloseForm = () => {
        setShowForm(false);
        setSelectedUser(null);
        setError('');
        setApiError('');
        fetchUsers();
    };

    return (
        <div className="flex-1 p-6">
            <h2 className="text-2xl font-bold mb-6">Quản lý người dùng</h2>
            <button
                onClick={() => setShowForm(true)}
                className="mb-4 bg-blue-500 text-white p-2 rounded hover:bg-blue-600"
                disabled={loading}
            >
                Thêm người dùng
            </button>
            {error && (
                <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
                    {error}
                </div>
            )}
            {showForm && (
                <UserForm
                    user={selectedUser}
                    onClose={handleCloseForm}
                    setApiError={setApiError}
                />
            )}
            <div className="bg-white p-6 rounded-lg shadow-lg">
                {loading ? (
                    <p className="text-center text-gray-500">Đang tải...</p>
                ) : (
                    <table className="w-full border-collapse">
                        <thead>
                        <tr className="bg-gray-200">
                            <th className="p-2 border">ID</th>
                            <th className="p-2 border">Email</th>
                            <th className="p-2 border">Vai trò</th>
                            <th className="p-2 border">Hành động</th>
                        </tr>
                        </thead>
                        <tbody>
                        {users.length > 0 ? (
                            users.map((user) => (
                                <tr key={user.id} className="hover:bg-gray-100">
                                    <td className="p-2 border">{user.id}</td>
                                    <td className="p-2 border">{user.email}</td>
                                    <td className="p-2 border">{user.role}</td>
                                    <td className="p-2 border">
                                        <button
                                            onClick={() => handleEdit(user)}
                                            className="bg-yellow-500 text-white p-1 rounded mr-2 hover:bg-yellow-600"
                                            disabled={loading}
                                        >
                                            Sửa
                                        </button>
                                        <button
                                            onClick={() => handleDelete(user.id)}
                                            className="bg-red-500 text-white p-1 rounded hover:bg-red-600"
                                            disabled={loading}
                                        >
                                            Xóa
                                        </button>
                                    </td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan="4" className="p-2 text-center text-gray-500">
                                    Không có người dùng nào
                                </td>
                            </tr>
                        )}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
};

export default UserManagement;