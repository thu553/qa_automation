package com.example.qa_automation.controller;

import com.example.qa_automation.request.AnswerRequest;
import com.example.qa_automation.request.UserRequest;
import com.example.qa_automation.entity.Consult;
import com.example.qa_automation.entity.User;
import com.example.qa_automation.service.AdminService;
import com.example.qa_automation.service.ConsultService;
import com.example.qa_automation.service.EmailService;
import com.example.qa_automation.service.UserService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/admin")
public class AdminController {
    @Autowired
    private ConsultService consultService;

    @Autowired
    private AdminService adminService;

    @Autowired
    private UserService userService;

    @Autowired
    private EmailService emailService;

    @GetMapping("/consults")
    public ResponseEntity<List<Consult>> getAllConsults() {
        return ResponseEntity.ok(consultService.getAllConsults());
    }

    // 1. Lấy danh sách câu hỏi chưa được trả lời
    @GetMapping("/unanswered")
    public ResponseEntity<List<Consult>> getUnansweredConsults() {
        return ResponseEntity.ok(consultService.getUnansweredConsults());
    }

    // 2. Trả lời câu hỏi tư vấn
    @PostMapping("/consult/answer")
    public ResponseEntity<?> answerConsult(@Valid @RequestBody AnswerRequest request) {
        try {
            Consult consult = consultService.answerConsult(request.getConsultId(), request.getAnswer());
            emailService.sendConsultAnswer(consult.getUserEmail(), consult.getQuestion(), request.getAnswer());
            return ResponseEntity.ok(Map.of("message", "Đã gửi câu trả lời"));
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        } catch (Exception e) {
            return ResponseEntity.status(500).body(Map.of("error", "Lỗi server: " + e.getMessage()));
        }
    }

    // 3. Upload file Excel để thêm dữ liệu huấn luyện
    @PostMapping("/upload-excel")
    public ResponseEntity<Map<String, String>> uploadExcel(@RequestParam("file") MultipartFile file) {
        String result = adminService.uploadExcel(file);
        Map<String, String> response = Map.of("message", result);
        if (result.contains("Only Excel files") || result.contains("Excel must have") || result.contains("Questions and answers cannot be empty") || result.contains("Exceed 10,000 records") || result.contains("Invalid Excel file")) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(response);
        } else if (result.contains("No valid records to save")) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(response);
        } else if (result.contains("Unexpected error")) {
            return ResponseEntity.status(HttpStatus.PAYMENT_REQUIRED).body(response);
        } else if (result.contains("Upload thất bại")) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
        }
        return ResponseEntity.ok(response);
    }

    // 4. Bật tự động fine-tune
    @PostMapping("/enable-auto-fine-tune")
    public ResponseEntity<Map<String, Object>> enableAutoFineTune() {
        Map<String, Object> response = adminService.enableAutoFineTune();
        return ResponseEntity.ok(response);
    }

    // 5. Tắt tự động fine-tune
    @PostMapping("/disable-auto-fine-tune")
    public ResponseEntity<Map<String, Object>> disableAutoFineTune() {
        Map<String, Object> response = adminService.disableAutoFineTune();
        return ResponseEntity.ok(response);
    }

    // 6. Tranạng thái fine-tune
    @GetMapping("/get-auto-fine-tune-status")
    public ResponseEntity<String> getAutoFineTune() {
        boolean status = adminService.getAutoFineTune();
        return ResponseEntity.ok(status ? "enabled" : "disabled");
    }

    // 7. Get list of users
    @GetMapping("/users")
    public ResponseEntity<List<User>> getAllUsers() {
        return ResponseEntity.ok(userService.getAllUsers());
    }

    // 8. Create a new user
    @PostMapping("/users")
    public ResponseEntity<?> createUser(@RequestBody UserRequest userRequest) {
        try {
            if (userRequest.getEmail() == null || userRequest.getPassword() == null || userRequest.getRole() == null) {
                return ResponseEntity.badRequest().body(Map.of("error", "Thiếu thông tin"));
            }
            User user = userService.createUser(userRequest.getEmail(), userRequest.getPassword(), userRequest.getRole());
            return ResponseEntity.ok(Map.of("id", user.getId(), "email", user.getEmail(), "role", user.getRole().toString()));
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    // 9. Update a user
    @PutMapping("/users/{id}")
    public ResponseEntity<?> updateUser(@PathVariable Long id, @RequestBody UserRequest userRequest) {
        try {
            if (userRequest.getEmail() == null || userRequest.getRole() == null) {
                return ResponseEntity.badRequest().body(Map.of("error", "Thiếu thông tin"));
            }
            User user = userService.updateUser(id, userRequest.getEmail(), userRequest.getPassword(), userRequest.getRole());
            return ResponseEntity.ok(Map.of("id", user.getId(), "email", user.getEmail(), "role", user.getRole().toString()));
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    // 10. Delete a user
    @DeleteMapping("/users/{id}")
    public ResponseEntity<?> deleteUser(@PathVariable Long id) {
        try {
            userService.deleteUser(id);
            return ResponseEntity.ok(Map.of("message", "Xóa thành công"));
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    // 11. Update a consult
    @PutMapping("/consults/{id}")
    public ResponseEntity<?> updateConsult(
            @PathVariable Long id,
            @Valid @RequestBody ConsultRequest consultRequest
    ) {
        if (!consultRequest.getAnswer().isEmpty()) {
            try {
                Consult consult = consultService.answerConsult(id, consultRequest.getAnswer());
                emailService.sendConsultAnswer(consult.getUserEmail(), consult.getQuestion(), consultRequest.getAnswer());
                return ResponseEntity.ok(Map.of("message", "Đã gửi câu trả lời"));
            } catch (RuntimeException e) {
                return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
            } catch (Exception e) {
                return ResponseEntity.status(500).body(Map.of("error", "Lỗi server: " + e.getMessage()));
            }
        }
        Consult consult = consultService.updateConsult(id, consultRequest.getQuestion());
        return ResponseEntity.ok(consult);
    }

    // 12. Delete a consult
    @DeleteMapping("/consults/{id}")
    public ResponseEntity<String> deleteConsult(@PathVariable Long id) {
        consultService.deleteConsult(id);
        return ResponseEntity.ok("Đã xóa câu hỏi tư vấn");
    }

    // Request cho updating consult
    static class ConsultRequest {
        @NotBlank
        private String question;
        private String answer;

        public String getQuestion() { return question; }
        public void setQuestion(String question) { this.question = question; }
        public String getAnswer() { return answer; }
        public void setAnswer(String answer) { this.answer = answer; }
    }
}
