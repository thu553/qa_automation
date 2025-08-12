// src/components/admin/ConsultForm.jsx
import React, { useState } from 'react';
import axios from 'axios';
import Swal from 'sweetalert2';

const ConsultForm = ({ consult, onClose }) => {
    const [question, setQuestion] = useState(consult?.question || '');
    const [answer, setAnswer] = useState(consult?.answer || '');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            await axios.put(
                `/api/admin/consults/${consult.id}`,
                { question, answer },
                { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
            );
            Swal.fire({
                icon: 'success',
                title: 'Thành công',
                text: 'Đã cập nhật câu hỏi tư vấn',
            });
            onClose();
        } catch (err) {
            setError(err.response?.data?.message || 'Lỗi khi cập nhật câu hỏi');
            Swal.fire({
                icon: 'error',
                title: 'Lỗi',
                text: err.response?.data?.message || 'Lỗi khi cập nhật câu hỏi',
            });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
            <div className="bg-white p-6 rounded-lg shadow-lg max-w-md w-full">
                <h3 className="text-xl font-semibold mb-4">Sửa câu hỏi tư vấn</h3>
                <form onSubmit={handleSubmit}>
                    <div className="mb-4">
                        <label className="block text-gray-700">Câu hỏi</label>
                        <textarea
                            value={question}
                            onChange={(e) => setQuestion(e.target.value)}
                            className="w-full p-2 border rounded"
                            required
                            rows="4"
                        />
                    </div>
                    <div className="mb-4">
                        <label className="block text-gray-700">Câu trả lời</label>
                        <textarea
                            value={answer}
                            onChange={(e) => setAnswer(e.target.value)}
                            className="w-full p-2 border rounded"
                            rows="4"
                        />
                    </div>
                    {error && <p className="text-red-500 mb-4">{error}</p>}
                    <div className="flex justify-end">
                        <button
                            type="button"
                            onClick={onClose}
                            className="mr-2 bg-gray-500 text-white p-2 rounded hover:bg-gray-600"
                        >
                            Hủy
                        </button>
                        <button
                            type="submit"
                            disabled={isLoading}
                            className={`bg-blue-500 text-white p-2 rounded hover:bg-blue-600 ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                            {isLoading ? 'Đang lưu...' : 'Cập nhật'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default ConsultForm;