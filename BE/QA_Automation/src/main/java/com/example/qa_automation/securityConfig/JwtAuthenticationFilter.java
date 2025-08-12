package com.example.qa_automation.securityConfig;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

public class JwtAuthenticationFilter extends OncePerRequestFilter {
    private static final Logger logger = LoggerFactory.getLogger(JwtAuthenticationFilter.class);
    private final JwtUtil jwtTokenUtil;
    private final TokenBlacklist tokenBlacklist;

    public JwtAuthenticationFilter(JwtUtil jwtTokenUtil, TokenBlacklist tokenBlacklist) {
        this.jwtTokenUtil = jwtTokenUtil;
        this.tokenBlacklist = tokenBlacklist;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        logger.info("Processing request: {} {}", request.getMethod(), request.getRequestURI());

        String authHeader = request.getHeader("Authorization");

        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            String token = authHeader.substring(7).trim();
            logger.debug("Extracted token: {}", token);

            if (tokenBlacklist.isTokenBlacklisted(token)) {
                logger.warn("Token is blacklisted: {}", token);
                response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                response.setContentType("application/json");
                response.getWriter().write("{\"message\": \"Token đã bị vô hiệu hóa\"}");
                return;
            }

            try {
                if (jwtTokenUtil.validateToken(token)) {
                    String email = jwtTokenUtil.getEmailFromToken(token);
                    String role = jwtTokenUtil.getRoleFromToken(token);

                    if (role == null || role.isEmpty()) {
                        logger.warn("Token missing role: {}", token);
                        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                        response.setContentType("application/json");
                        response.getWriter().write("{\"message\": \"Token không chứa thông tin vai trò\"}");
                        return;
                    }

                    SimpleGrantedAuthority authority = new SimpleGrantedAuthority(role);
                    UsernamePasswordAuthenticationToken authentication =
                            new UsernamePasswordAuthenticationToken(email, null, List.of(authority));
                    SecurityContextHolder.getContext().setAuthentication(authentication);
                    logger.info("Authenticated user: {} with role: {}", email, role);
                } else {
                    logger.warn("Invalid token: {}", token);
                    response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                    response.setContentType("application/json");
                    response.getWriter().write("{\"message\": \"Token không hợp lệ hoặc đã hết hạn\"}");
                    return;
                }
            } catch (Exception e) {
                logger.error("Error validating token: {}", token, e);
                response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                response.setContentType("application/json");
                response.getWriter().write("{\"message\": \"Lỗi khi xác thực token: " + e.getMessage() + "\"}");
                return;
            }
        } else {
            logger.debug("No valid Authorization header found");
        }

        filterChain.doFilter(request, response);
    }
}