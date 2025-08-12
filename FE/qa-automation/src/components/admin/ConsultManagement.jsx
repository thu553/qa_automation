import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Swal from 'sweetalert2';
import AnswerForm from './AnswerForm';
import ConsultForm from './ConsultForm';
import { FiEye, FiEdit, FiTrash2, FiMessageSquare } from 'react-icons/fi';

const ConsultManagement = () => {
    const [consults, setConsults] = useState([]);
    const [filteredConsults, setFilteredConsults] = useState([]);
    const [error, setError] = useState('');
    const [filterUnanswered, setFilterUnanswered] = useState(true);
    const [showConsultForm, setShowConsultForm] = useState(false);
    const [showAnswerForm, setShowAnswerForm] = useState(false);
    const [showAnswerDialog, setShowAnswerDialog] = useState(null);
    const [selectedConsult, setSelectedConsult] = useState(null);
    const [apiError, setApiError] = useState('');

    const fetchConsults = async () => {
        try {
            const response = await axios.get('/api/admin/consults', {
                headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
            });
            setConsults(response.data);
            setFilteredConsults(response.data);
            setApiError('');
        } catch (e) {
            const errorMsg = e.response?.data?.error || 'Lỗi khi tải danh sách câu hỏi';
            setError(errorMsg);
            setApiError(errorMsg);
        }
    };

    useEffect(() => {
        fetchConsults();
    }, []);

    useEffect(() => {
        setFilteredConsults(
            filterUnanswered ? consults.filter((c) => !c.answer) : consults
        );
    }, [filterUnanswered, consults]);

    const handleDelete = async (id) => {
        try {
            const result = await Swal.fire({
                title: 'Xác nhận xóa',
                text: 'Bạn muốn xóa câu hỏi này?',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonText: 'Xóa',
                cancelButtonText: 'Hủy',
            });
            if (result.isConfirmed) {
                await axios.delete(`/api/admin/consults/${id}`, {
                    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
                });
                Swal.fire('Thành công', 'Đã xóa câu hỏi', 'success');
                fetchConsults();
            }
        } catch (e) {
            Swal.fire('Lỗi', e.response?.data?.error || 'Lỗi khi xóa', 'error');
        }
    };

    const handleEdit = (consult) => {
        setSelectedConsult(consult);
        setShowConsultForm(true);
    };

    const handleAnswer = (consult) => {
        setSelectedConsult(consult);
        setShowAnswerForm(true);
    };

    const handleShowAnswer = (consult) => {
        setShowAnswerDialog(consult);
    };

    const handleClose = () => {
        setShowConsultForm(false);
        setShowAnswerForm(false);
        setShowAnswerDialog(null);
        setSelectedConsult(null);
        fetchConsults();
    };

    return (
        <div className="flex-1 p-6">
            <h2 className="text-2xl font-bold mb-6">Quản lý câu hỏi tư vấn</h2>
            <div className="mb-4">
                <label className="inline-flex items-center">
                    <input
                        type="checkbox"
                        checked={filterUnanswered}
                        onChange={(e) => setFilterUnanswered(e.target.checked)}
                        className="mr-2"
                    />
                    Chỉ hiển thị câu hỏi chưa trả lời
                </label>
            </div>
            {error && (
                <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
                    {error}
                </div>
            )}
            {showConsultForm && (
                <ConsultForm consult={selectedConsult} onClose={handleClose} />
            )}
            {showAnswerForm && (
                <AnswerForm
                    consultId={selectedConsult.id}
                    userEmail={selectedConsult.userEmail}
                    question={selectedConsult.question}
                    onAnswerSubmitted={handleClose}
                    setApiError={setApiError}
                />
            )}
            {showAnswerDialog && (
                <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center">
                    <div className="bg-white p-4 rounded-xl shadow-lg max-w-sm w-full">
                        <h3 className="text-lg font-semibold mb-3">Câu trả lời</h3>
                        <p className="text-sm text-gray-600 mb-2">Câu hỏi: {showAnswerDialog.question}</p>
                        <p className="text-sm text-gray-600 mb-4">
                            Trả lời: {showAnswerDialog.answer || 'Chưa trả lời'}
                        </p>
                        <div className="flex justify-end">
                            <button
                                onClick={() => setShowAnswerDialog(null)}
                                className="bg-gray-300 text-gray-700 px-3 py-1 rounded-lg hover:bg-gray-400 transition-colors duration-200 text-sm"
                            >
                                Đóng
                            </button>
                        </div>
                    </div>
                </div>
            )}
            <div className="bg-white p-6 rounded-lg shadow-lg">
                <table className="w-full border-collapse">
                    <thead>
                    <tr className="bg-gray-200">
                        <th className="p-2 border">ID</th>
                        <th className="p-2 border">Câu hỏi</th>
                        <th className="p-2 border">Câu trả lời</th>
                        <th className="p-2 border">Email người hỏi</th>
                        <th className="p-2 border">Hành động</th>
                    </tr>
                    </thead>
                    <tbody>
                    {filteredConsults.length > 0 ? (
                        filteredConsults.map((consult) => (
                            <tr key={consult.id} className="hover:bg-gray-100">
                                <td className="p-2 border">{consult.id}</td>
                                <td className="p-2 border">{consult.question}</td>
                                <td className="p-2 border">
                                    {consult.answer ? (
                                        <button
                                            onClick={() => handleShowAnswer(consult)}
                                            className="bg-teal-100 text-teal-700 px-3 py-1 rounded-full hover:bg-teal-200 transition-colors duration-200 text-sm font-medium flex items-center gap-1"
                                        >
                                            <FiEye className="w-4 h-4" />
                                            Xem
                                        </button>
                                    ) : (
                                        'Chưa trả lời'
                                    )}
                                </td>
                                <td className="p-2 border">{consult.userEmail}</td>
                                <td className="p-2 border flex gap-2">
                                    <button
                                        onClick={() => handleEdit(consult)}
                                        className="bg-yellow-100 text-yellow-700 px-3 py-1 rounded-full hover:bg-yellow-200 transition-colors duration-200 text-sm font-medium flex items-center gap-1"
                                    >
                                        <FiEdit className="w-4 h-4" />
                                        Sửa
                                    </button>
                                    <button
                                        onClick={() => handleDelete(consult.id)}
                                        className="bg-red-100 text-red-700 px-3 py-1 rounded-full hover:bg-red-200 transition-colors duration-200 text-sm font-medium flex items-center gap-1"
                                    >
                                        <FiTrash2 className="w-4 h-4" />
                                        Xóa
                                    </button>
                                    {!consult.answer && (
                                        <button
                                            onClick={() => handleAnswer(consult)}
                                            className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full hover:bg-blue-200 transition-colors duration-200 text-sm font-medium flex items-center gap-1"
                                        >
                                            <FiMessageSquare className="w-4 h-4" />
                                            Trả lời
                                        </button>
                                    )}
                                </td>
                            </tr>
                        ))
                    ) : (
                        <tr>
                            <td colSpan="5" className="p-2 text-center text-gray-500">
                                Không có câu hỏi nào
                            </td>
                        </tr>
                    )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default ConsultManagement;