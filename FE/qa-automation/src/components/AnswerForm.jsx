import React, { useState } from 'react';
import axios from 'axios';
import Swal from 'sweetalert2';

const AnswerForm = ({ consultId, userEmail, question, onAnswerSubmitted }) => {
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

        try {
            await axios.post(
                '/api/consult/answer',
                { consultId, answer, email: localStorage.getItem('email') },
                { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
            );
            setAnswer('');
            Swal.fire({
                icon: 'success',
                title: 'Thành công',
                text: 'Câu trả lời đã được gửi và email đã được gửi đến người hỏi',
                confirmButtonText: 'OK',
            });
            if (onAnswerSubmitted) {
                await onAnswerSubmitted(); // Làm mới danh sách ở UnansweredList
            }
        } catch (err) {
            setError(err.response?.data?.message || 'Đã có lỗi xảy ra khi gửi câu trả lời');
            Swal.fire({
                icon: 'error',
                title: 'Lỗi',
                text: err.response?.data?.message || 'Không thể gửi câu trả lời',
                confirmButtonText: 'OK',
            });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="mt-4">
            <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                className="w-full p-2 border rounded"
                placeholder="Nhập câu trả lời"
                rows="4"
                disabled={isLoading}
            />
            <button
                onClick={handleSubmit}
                className={`mt-2 bg-blue-500 text-white p-2 rounded hover:bg-blue-600 ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                disabled={isLoading}
            >
                {isLoading ? 'Đang gửi...' : 'Gửi'}
            </button>
            {error && (
                <p className="text-red-500 mt-2">{error}</p>
            )}
        </div>
    );
};

export default AnswerForm;