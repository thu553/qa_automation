package com.example.qa_automation.request;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;

public class AnswerRequest {
    private Long consultId;
    @NotBlank
    private String answer;
    @Email
    private String email;

    public Long getConsultId() { return consultId; }
    public void setConsultId(Long consultId) { this.consultId = consultId; }
    public String getAnswer() { return answer; }
    public void setAnswer(String answer) { this.answer = answer; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
}
