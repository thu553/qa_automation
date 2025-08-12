package com.example.qa_automation.service;

import com.example.qa_automation.entity.Consult;
import com.example.qa_automation.repository.ConsultRepository;
import com.example.qa_automation.utils.MultipartInputStreamFileResource;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Service
public class AdminService {

    @Value("${fastapi.url}")
    private String fastApiUrl;
    private final ObjectMapper objectMapper;

    private final RestTemplate restTemplate;

    public AdminService(ObjectMapper objectMapper, RestTemplate restTemplate) {
        this.objectMapper = objectMapper;
        this.restTemplate = restTemplate;
    }

    public String uploadExcel(MultipartFile file) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.MULTIPART_FORM_DATA);
            MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
            body.add("file", new MultipartInputStreamFileResource(file.getInputStream(), file.getOriginalFilename()));
            HttpEntity<MultiValueMap<String, Object>> request = new HttpEntity<>(body, headers);

            ResponseEntity<Map> response = restTemplate.postForEntity(fastApiUrl + "/upload-excel", request, Map.class);
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null && response.getBody().containsKey("message")) {
                return (String) response.getBody().get("message");
            } else if (response.getStatusCode() == HttpStatus.BAD_REQUEST && response.getBody() != null && response.getBody().containsKey("detail")) {
                return (String) response.getBody().get("detail");
            } else if (response.getStatusCode() == HttpStatus.UNAUTHORIZED && response.getBody() != null && response.getBody().containsKey("detail")) {
                return (String) response.getBody().get("detail");
            } else if (response.getStatusCode() == HttpStatus.PAYMENT_REQUIRED && response.getBody() != null && response.getBody().containsKey("detail")) {
                return (String) response.getBody().get("detail");
            } else if (response.getStatusCode().is5xxServerError() && response.getBody() != null && response.getBody().containsKey("detail")) {
                return (String) response.getBody().get("detail");
            }
            return "Upload thất bại: Không nhận được phản hồi hợp lệ từ server";
        } catch (HttpClientErrorException e) {
            String errorMessage = e.getResponseBodyAsString();
            try {
                Map<String, Object> errorResponse = objectMapper.readValue(errorMessage, Map.class);
                if (errorResponse.containsKey("detail")) {
                    return (String) errorResponse.get("detail"); // Trả về raw detail mà không thêm "Lỗi: " để controller xử lý
                }
                return "Lỗi không xác định: " + errorMessage;
            } catch (Exception ex) {
                return "Lỗi upload file: " + (errorMessage.isEmpty() ? "Không xác định" : errorMessage);
            }
        } catch (Exception e) {
            return "Lỗi upload file: " + e.getMessage();
        }
    }

    public Map<String, Object> enableAutoFineTune() {
        try {
            return restTemplate.postForObject(fastApiUrl + "/enable-auto-fine-tune", null, Map.class);
        } catch (Exception e) {
            throw new RuntimeException("Failed to enable auto fine-tune: " + e.getMessage(), e);
        }
    }

    public Map<String, Object> disableAutoFineTune() {
        try {
            return restTemplate.postForObject(fastApiUrl + "/disable-auto-fine-tune", null, Map.class);
        } catch (Exception e) {
            throw new RuntimeException("Failed to disable auto fine-tune: " + e.getMessage(), e);
        }
    }

    public boolean getAutoFineTune() {
        try {
            Map<String, Object> response = restTemplate.getForObject(fastApiUrl + "/get-auto-fine-tune-status", Map.class);
            if (response != null && response.containsKey("status")) {
                return (boolean) response.get("status");
            }
            throw new RuntimeException("Invalid response from FastAPI");
        } catch (Exception e) {
            throw new RuntimeException("Failed to get auto fine-tune status: " + e.getMessage(), e);
        }
    }
}
