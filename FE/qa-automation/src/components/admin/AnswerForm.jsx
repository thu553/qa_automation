import React, { useState } from 'react';
import axios from 'axios';
import Swal from 'sweetalert2';

const AnswerForm = ({ consultId, userEmail, question, onAnswerSubmitted, setApiError }) => {
    const [answer, setAnswer] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        if (!answer.trim()) {
            setError('Vui lòng nhập câu trả lời');
            setIsLoading(false);
            return;
        }

        const email = localStorage.getItem('email');
        if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            setError('Email không hợp lệ');
            setIsLoading(false);
            return;
        }

        try {
            await axios.post(
                '/api/admin/consult/answer',
                { consultId, answer, email },
                { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
            );
            Swal.fire('Thành công', 'Đã trả lời câu hỏi', 'success');
            setAnswer('');
            if (setApiError) setApiError('');
            onAnswerSubmitted();
        } catch (err) {
            console.log('API error:', err.response); // Debug
            const errorMsg = err.response?.data?.error || err.response?.data || 'Lỗi khi gửi câu trả lời';
            setError(errorMsg);
            Swal.fire('Lỗi', errorMsg, 'error');
            if (setApiError) setApiError(errorMsg);
            if (err.response?.status === 401) {
                localStorage.clear();
                window.location.href = '/login';
            }
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
            <div className="bg-white p-6 rounded-lg shadow-lg max-w-md w-full">
                <h3 className="text-xl font-semibold mb-4">Trả lời câu hỏi</h3>
                <form onSubmit={handleSubmit}>
                    <div className="mb-4">
                        <p className="text-sm text-gray-600 mb-2">Người hỏi: {userEmail}</p>
                        <p className="text-sm text-gray-600 mb-2">Câu hỏi: {question}</p>
                        <textarea
                            value={answer}
                            onChange={(e) => setAnswer(e.target.value)}
                            className="w-full p-2 border rounded"
                            placeholder="Nhập câu trả lời"
                            rows="4"
                            disabled={isLoading}
                            required
                        />
                    </div>
                    {error && <p className="text-red-500 mb-4">{error}</p>}
                    <div className="flex justify-end">
                        <button
                            type="button"
                            onClick={onAnswerSubmitted}
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
                            {isLoading ? 'Đang gửi...' : 'Gửi'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default AnswerForm;