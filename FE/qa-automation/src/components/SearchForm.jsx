import React, { useState } from 'react';
import axios from 'axios';
import AnswerList from './AnswerList';
import ConsultForm from './ConsultForm';

const SearchForm = () => {
    const [searchQuery, setSearchQuery] = useState('');
    const [results, setResults] = useState([]);
    const [showConsultButton, setShowConsultButton] = useState(false);
    const [error, setError] = useState('');

    const handleSearch = async (e) => {
        e.preventDefault();
        setError('');
        if (!searchQuery.trim()) {
            setError('Vui lòng nhập câu hỏi');
            return;
        }

        try {
            const response = await axios.post(
                '/api/qa/search',
                { question: searchQuery },
                { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
            );
            setResults(response.data);
            setShowConsultButton(true);
            // Gửi tín hiệu reset sau khi nhận kết quả mới
        } catch (err) {
            setError(err.response?.data?.message || 'Đã có lỗi xảy ra khi tìm kiếm');
        }
    };

    const handleConsulted = () => {
        setShowConsultButton(false);
    };

    return (
        <div className="max-w-2xl mx-auto mt-10 p-6 bg-white rounded-lg shadow-lg">
            <h2 className="text-2xl font-bold mb-4">Tìm kiếm câu hỏi</h2>
            <form onSubmit={handleSearch}>
                <div className="mb-4">
                    <label className="block text-gray-700">Câu hỏi</label>
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full p-2 border rounded"
                        placeholder="Nhập câu hỏi của bạn"
                    />
                </div>
                <button
                    type="submit"
                    className="w-full bg-blue-500 text-white p-2 rounded hover:bg-blue-600"
                >
                    Tìm kiếm
                </button>
            </form>
            {error && (
                <div className="mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
                    {error}
                </div>
            )}
            <div className="mt-6">
                <AnswerList results={results} searchQuery={searchQuery} onSearch={() => {}} /> {/* Thêm prop onSearch */}
                {searchQuery.trim() && showConsultButton && (
                    <ConsultForm question={searchQuery} onConsulted={handleConsulted} />
                )}
            </div>
        </div>
    );
};

export default SearchForm;