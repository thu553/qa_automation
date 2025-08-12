package com.example.qa_automation.service;

import com.example.qa_automation.entity.Role;
import com.example.qa_automation.entity.User;
import com.example.qa_automation.repository.UserRepository;
import com.example.qa_automation.securityConfig.JwtUtil;
import com.example.qa_automation.securityConfig.TokenBlacklist;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class AuthService {
    @Autowired
    private UserRepository userRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Autowired
    private JwtUtil jwtUtil;

    @Autowired
    private TokenBlacklist tokenBlacklist;

    public User register(String email, String password) {
        if (!email.matches("^[A-Za-z0-9+_.-]+@(.+)$")) {
            throw new RuntimeException("Email không hợp lệ");
        }

        if (userRepository.findByEmail(email) != null) {
            throw new RuntimeException("Email đã tồn tại");
        }
        User user = new User();
        user.setEmail(email);
        user.setPassword(passwordEncoder.encode(password));
        user.setRole(Role.USER);
        return userRepository.save(user);
    }

    public LoginResponse login(String email, String password) {
        User user = userRepository.findByEmail(email);
        if (user == null || !passwordEncoder.matches(password, user.getPassword())) {
            throw new RuntimeException("Thông tin đăng nhập không hợp lệ");
        }
        String token = jwtUtil.generateToken(user.getEmail(), user.getRole().toString());
        return new LoginResponse(user.getEmail(), user.getRole().toString(), token);
    }

    public void logout(String token) {
        if (jwtUtil.validateToken(token)) {
            long expirationTime = jwtUtil.getExpirationDateFromToken(token).getTime();
            tokenBlacklist.blacklistToken(token, expirationTime);
        } else {
            throw new RuntimeException("Token không hợp lệ hoặc đã hết hạn");
        }
    }

    public static class LoginResponse {
        private String email;
        private String role;
        private String token;

        public LoginResponse(String email, String role, String token) {
            this.email = email;
            this.role = role;
            this.token = token;
        }

        public String getEmail() { return email; }
        public void setEmail(String email) { this.email = email; }
        public String getRole() { return role; }
        public void setRole(String role) { this.role = role; }
        public String getToken() { return token; }
        public void setToken(String token) { this.token = token; }
    }
}