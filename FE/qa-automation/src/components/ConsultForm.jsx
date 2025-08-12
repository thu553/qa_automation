import React, { useState } from 'react';
import axios from 'axios';
import Swal from 'sweetalert2';

const ConsultForm = ({ question, onConsulted }) => {
    const [isLoading, setIsLoading] = useState(false);

    const handleConsult = async () => {
        setIsLoading(true);
        try {
            await axios.post(
                '/api/qa/consult',
                { question, userEmail: localStorage.getItem('email') },
                { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
            );
            Swal.fire({
                icon: 'success',
                title: 'Thành công',
                text: 'Câu hỏi đã được gửi để tư vấn',
                confirmButtonText: 'OK',
            });
            if (onConsulted) {
                onConsulted();
            }
        } catch (err) {
            Swal.fire({
                icon: 'error',
                title: 'Lỗi',
                text: err.response?.data?.message || 'Đã có lỗi xảy ra',
                confirmButtonText: 'OK',
            });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <button
            onClick={handleConsult}
            disabled={isLoading}
            className={`mt-4 bg-yellow-500 text-white p-2 rounded hover:bg-yellow-600 ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
            {isLoading ? 'Đang gửi...' : 'Tư vấn trực tiếp'}
        </button>
    );
};

export default ConsultForm;