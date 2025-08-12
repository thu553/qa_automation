package com.example.qa_automation.controller;

import com.example.qa_automation.service.ConsultService;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

// lớp daành cho user thường dùng để hỏi hoặc hỏi trực tiêp
@RestController
@RequestMapping("/api/qa")
public class QAController {
    @Autowired
    private ConsultService consultService;

    // tìm kiếm câu trả lời
    @PostMapping("/search")
    public ResponseEntity<List<Map<String, Object>>> search(@RequestBody SearchRequest request) {
        List<Map<String, Object>> results = consultService.searchQuestion(request.getQuestion());
        return ResponseEntity.ok(results);
    }

    // nhâấn chấp nận câu trả lời
    @PostMapping("/like")
    public ResponseEntity<String> like(@RequestBody LikeRequest request) {
        consultService.likeQuestion(request.getQuestion(), request.getAnswer());
        return ResponseEntity.ok("Đã lưu câu hỏi và câu trả lời");
    }

    // gửi câu hỏi tư vấn
    @PostMapping("/consult")
    public ResponseEntity<String> sendConsult(@RequestBody ConsultRequest request) {
        consultService.sendConsult(request.getQuestion(), request.getUserEmail());
        return ResponseEntity.ok("Câu hỏi đã được gửi để tư vấn");
    }

    // các lớp request
    static class SearchRequest {
        @NotBlank
        private String question;

        public String getQuestion() { return question; }
        public void setQuestion(String question) { this.question = question; }
    }

    static class LikeRequest {
        @NotBlank
        private String question;
        @NotBlank
        private String answer;

        public String getQuestion() { return question; }
        public void setQuestion(String question) { this.question = question; }
        public String getAnswer() { return answer; }
        public void setAnswer(String answer) { this.answer = answer; }
    }

    static class ConsultRequest {
        @NotBlank
        private String question;
        @Email
        private String userEmail;

        public String getQuestion() { return question; }
        public void setQuestion(String question) { this.question = question; }
        public String getUserEmail() { return userEmail; }
        public void setUserEmail(String userEmail) { this.userEmail = userEmail; }
    }
}