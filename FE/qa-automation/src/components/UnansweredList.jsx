import React, { useState, useEffect } from 'react';
import axios from 'axios';
import AnswerForm from './AnswerForm';

const UnansweredList = () => {
    const [consults, setConsults] = useState([]);
    const [error, setError] = useState('');

    // Lấy danh sách câu hỏi chưa trả lời
    const fetchConsults = async () => {
        try {
            const response = await axios.get('/api/consult/unanswered', {
                headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
            });
            console.log('Fetched consults:', response.data); // Debug
            setConsults(response.data);
            setError('');
        } catch (err) {
            setError(err.response?.data?.message || 'Đã có lỗi xảy ra khi tải câu hỏi');
        }
    };

    useEffect(() => {
        fetchConsults();
    }, []);

    return (
        <div className="max-w-2xl mx-auto mt-10 p-6 bg-white rounded-lg shadow-lg">
            <h2 className="text-2xl font-bold mb-4">Câu hỏi chưa trả lời</h2>
            {error && (
                <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
                    {error}
                </div>
            )}
            {consults.length > 0 ? (
                consults.map((consult) => (
                    <div key={consult.id} className="mb-4 p-4 border rounded">
                        <p><strong>Câu hỏi:</strong> {consult.question}</p>
                        <p><strong>Email:</strong> {consult.userEmail}</p>
                        <AnswerForm
                            consultId={consult.id}
                            userEmail={consult.userEmail}
                            question={consult.question}
                            onAnswerSubmitted={fetchConsults} // Truyền callback
                        />
                    </div>
                ))
            ) : (
                <p className="text-gray-500">Không có câu hỏi nào chưa trả lời.</p>
            )}
        </div>
    );
};

export default UnansweredList;