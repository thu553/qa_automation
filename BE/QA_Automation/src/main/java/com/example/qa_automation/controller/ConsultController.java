package com.example.qa_automation.controller;

import com.example.qa_automation.entity.Consult;
import com.example.qa_automation.repository.ConsultRepository;
import com.example.qa_automation.request.AnswerRequest;
import com.example.qa_automation.service.EmailService;
import com.example.qa_automation.service.ConsultService;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

// lớp dành cho người trả lời các câu hỏi
@RestController
@RequestMapping("/api/consult")
public class ConsultController {
    @Autowired
    private ConsultService consultService;

    @Autowired
    private EmailService emailService;

    // lấy ra list cac cau hoi chua tra loi
    @GetMapping("/unanswered")
    public ResponseEntity<List<Consult>> getUnansweredConsults() {
        return ResponseEntity.ok(consultService.getUnansweredConsults());
    }

    // tra loi cau hoi chua tra loi
    @PostMapping("/answer")
    public ResponseEntity<String> answerConsult(@RequestBody AnswerRequest request) {
        Consult consult = consultService.answerConsult(request.getConsultId(), request.getAnswer());
        emailService.sendConsultAnswer(consult.getUserEmail(), consult.getQuestion(), request.getAnswer());
        return ResponseEntity.ok("Đã gửi câu trả lời");
    }
}