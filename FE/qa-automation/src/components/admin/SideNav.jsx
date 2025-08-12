// src/components/admin/SideNav.jsx
import React from 'react';
import { NavLink } from 'react-router-dom';

const SideNav = () => {
    return (
        <div className="w-64 bg-gray-800 text-white h-screen p-4">
            <h2 className="text-2xl font-bold mb-6">Admin Panel</h2>
            <nav>
                <ul>
                    <li className="mb-4">
                        <NavLink
                            to="/admin/dashboard"
                            className={({ isActive }) =>
                                isActive ? 'text-blue-400 font-semibold' : 'text-white hover:text-blue-400'
                            }
                        >
                            Dashboard
                        </NavLink>
                    </li>
                    <li className="mb-4">
                        <NavLink
                            to="/admin/users"
                            className={({ isActive }) =>
                                isActive ? 'text-blue-400 font-semibold' : 'text-white hover:text-blue-400'
                            }
                        >
                            Quản lý người dùng
                        </NavLink>
                    </li>
                    <li className="mb-4">
                        <NavLink
                            to="/admin/consults"
                            className={({ isActive }) =>
                                isActive ? 'text-blue-400 font-semibold' : 'text-white hover:text-blue-400'
                            }
                        >
                            Quản lý câu hỏi tư vấn
                        </NavLink>
                    </li>
                </ul>
            </nav>
        </div>
    );
};

export default SideNav;