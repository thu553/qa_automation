package com.example.qa_automation.securityConfig;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class TokenBlacklist {
    private static final Logger logger = LoggerFactory.getLogger(TokenBlacklist.class);
    private final Map<String, Long> blacklist = new ConcurrentHashMap<>();

    public void blacklistToken(String token, long expirationTime) {
        blacklist.put(token, expirationTime);
        logger.info("Added token to blacklist: {} with expiration: {}", token, expirationTime);
    }

    public boolean isTokenBlacklisted(String token) {
        Long expiration = blacklist.get(token);
        if (expiration == null) {
            logger.debug("Token not found in blacklist: {}", token);
            return false;
        }
        if (System.currentTimeMillis() > expiration) {
            blacklist.remove(token);
            logger.debug("Removed expired token from blacklist: {}", token);
            return false;
        }
        logger.info("Token is blacklisted: {}", token);
        return true;
    }

    public Map<String, Long> getAll() {
        return blacklist;
    }
}