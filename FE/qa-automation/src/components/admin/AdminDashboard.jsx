import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Swal from 'sweetalert2';

const AdminDashboard = () => {
    const [fineTuneStatus, setFineTuneStatus] = useState('Đang tải...');
    const [file, setFile] = useState(null);
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    // Lấy trạng thái auto fine-tune
    const fetchFineTuneStatus = async () => {
        try {
            const response = await axios.get('/api/admin/get-auto-fine-tune-status', {
                headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
            });
            setFineTuneStatus(response.data);
        } catch (err) {
            setError(err.response?.data?.message || 'Lỗi khi lấy trạng thái auto fine-tune');
        }
    };

    useEffect(() => {
        fetchFineTuneStatus();
    }, []);

    // Bật/tắt auto fine-tune
    const toggleFineTune = async () => {
        setIsLoading(true);
        try {
            const url = fineTuneStatus === 'enabled' ? '/api/admin/disable-auto-fine-tune' : '/api/admin/enable-auto-fine-tune';
            await axios.post(url, null, {
                headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
            });
            setFineTuneStatus(fineTuneStatus === 'enabled' ? 'disabled' : 'enabled');
            Swal.fire({
                icon: 'success',
                title: 'Thành công',
                text: `Auto fine-tune đã được ${fineTuneStatus === 'enabled' ? 'tắt' : 'bật'}`,
            });
        } catch (err) {
            Swal.fire({
                icon: 'error',
                title: 'Lỗi',
                text: err.response?.data?.message || 'Lỗi khi thay đổi trạng thái auto fine-tune',
            });
        } finally {
            setIsLoading(false);
        }
    };

    // Upload file Excel
    const handleFileUpload = async (e) => {
        e.preventDefault();
        if (!file) {
            setError('Vui lòng chọn file Excel');
            return;
        }
        setIsLoading(true);
        const formData = new FormData();
        formData.append('file', file);
        try {
            await axios.post('/api/admin/upload-excel', formData, {
                headers: {
                    Authorization: `Bearer ${localStorage.getItem('token')}`,
                    'Content-Type': 'multipart/form-data',
                },
            });
            Swal.fire({
                icon: 'success',
                title: 'Thành công',
                text: 'Đã tải file Excel lên thành công',
            });
            setFile(null);
            setError('');
        } catch (err) {
            setError(err.response?.data?.message || 'Lỗi khi upload file Excel');
            Swal.fire({
                icon: 'error',
                title: 'Lỗi',
                text: err.response?.data?.message || 'Lỗi khi upload file Excel',
            });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex-1 p-6">
            <h2 className="text-2xl font-bold mb-6">Admin Dashboard</h2>
            <div className="bg-white p-6 rounded-lg shadow-lg">
                <h3 className="text-xl font-semibold mb-4">Trạng thái Auto Fine-Tune</h3>
                <p className="mb-4">Trạng thái: <span className="font-bold">{fineTuneStatus === 'enabled' ? 'Bật' : 'Tắt'}</span></p>
                <button
                    onClick={toggleFineTune}
                    disabled={isLoading}
                    className={`bg-blue-500 text-white p-2 rounded hover:bg-blue-600 ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                    {isLoading ? 'Đang xử lý...' : fineTuneStatus === 'enabled' ? 'Tắt Auto Fine-Tune' : 'Bật Auto Fine-Tune'}
                </button>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-lg mt-6">
                <h3 className="text-xl font-semibold mb-4">Upload File Excel</h3>
                <form onSubmit={handleFileUpload}>
                    <input
                        type="file"
                        accept=".xlsx,.xls"
                        onChange={(e) => setFile(e.target.files[0])}
                        className="mb-4"
                    />
                    {error && <p className="text-red-500 mb-4">{error}</p>}
                    <button
                        type="submit"
                        disabled={isLoading}
                        className={`bg-blue-500 text-white p-2 rounded hover:bg-blue-600 ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                        {isLoading ? 'Đang upload...' : 'Upload Excel'}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default AdminDashboard;