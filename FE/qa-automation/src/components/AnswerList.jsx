import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Swal from 'sweetalert2';
import 'react-toastify/dist/ReactToastify.css';

const AnswerList = ({ results, searchQuery, onSearch }) => {
    const [isLoading, setIsLoading] = useState({});
    const [likedAnswers, setLikedAnswers] = useState({});

    // Reset likedAnswers khi có tìm kiếm mới
    useEffect(() => {
        setLikedAnswers({});
    }, [onSearch, results]);

    const handleLike = async (answer, index) => {
        if (!searchQuery) {
            Swal.fire({ icon: 'error', title: 'Lỗi', text: 'Không tìm thấy câu hỏi tìm kiếm' });
            return;
        }
        setIsLoading((prev) => ({ ...prev, [answer]: true }));
        try {
            await axios.post(
                '/api/qa/like',
                { question: searchQuery, answer },
                { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
            );
            setLikedAnswers((prev) => ({ ...prev, [answer]: true }));
            Swal.fire({ icon: 'success', title: 'Thành công', text: 'Cảm ơn bạn đã đánh giá câu trả lời' });
        } catch (err) {
            Swal.fire({ icon: 'error', title: 'Lỗi', text: err.response?.data?.message || 'Lỗi khi đánh giá câu trả lời' });
        } finally {
            setIsLoading((prev) => ({ ...prev, [answer]: false }));
        }
    };

    return (
        <div>
            <h3 className="text-xl font-semibold mb-2">Kết quả:</h3>
            {results.length === 0 ? (
                <p className="text-gray-500">Không có kết quả nào.</p>
            ) : (
                results.map((result, index) => (
                    <div key={index} className="mb-4 p-4 border rounded">
                        <div className="flex justify-between items-start gap-4">
                            <div className="flex-1">
                                <p className="text-lg font-semibold text-black mt-2">
                                    <strong>Câu hỏi:</strong> {result.question}
                                </p>
                                <p className="mt-2"><strong>Câu trả lời:</strong> {result.answer}</p>
                            </div>

                            {!likedAnswers[result.answer] && (
                                <button
                                    onClick={() => handleLike(result.answer, index)}
                                    className={`h-fit px-4 py-2 border border-red-600 text-red-600 rounded hover:bg-red-600 hover:text-white transition-colors duration-200 ${isLoading[result.answer] ? 'opacity-50 cursor-not-allowed' : ''}`}
                                    disabled={isLoading[result.answer]}
                                >
                                    {isLoading[result.answer] ? 'like...' : 'Like'}
                                </button>
                            )}
                            {likedAnswers[result.answer] && (
                                <button
                                    className={`h-fit px-4 py-2 border text-white rounded bg-red-600 border-red-600 cursor-default`}>
                                    like
                                </button>
                            )}
                        </div>
                    </div>
                ))
            )}
        </div>
    );
};

export default AnswerList;