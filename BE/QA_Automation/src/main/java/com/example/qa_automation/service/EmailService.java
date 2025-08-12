package com.example.qa_automation.service;

import jakarta.mail.MessagingException;
import jakarta.mail.internet.MimeMessage;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.mail.MailException;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.stereotype.Service;

@Service
public class EmailService {
    @Autowired
    private JavaMailSender mailSender;

    public void sendConsultAnswer(String to, String question, String answer) {
        try {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true);
            helper.setTo(to);
            helper.setSubject("Câu hỏi tư vấn trư tiếp");

            // Nội dung email được cải tiến
            String emailContent = "<div style='font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;'>"
                    + "<p>Kính gửi bạn,</p>"
                    + "<p>Chúng tôi đã nhận được câu hỏi của bạn và xin gửi câu trả lời như sau:</p>"
                    + "<h3 style='color: #34495e; margin-top: 20px;'>Câu hỏi:</h3>"
                    + "<p style='background-color: #f9f9f9; padding: 10px; border-radius: 5px;'>" + question + "</p>"
                    + "<h3 style='color: #34495e; margin-top: 20px;'>Câu trả lời:</h3>"
                    + "<p style='background-color: #f9f9f9; padding: 10px; border-radius: 5px;'>" + answer + "</p>"
                    + "<p style='margin-top: 20px;'>Nếu bạn có thêm câu hỏi, gửi câu hỏi trên hệ thống QA của trường. Xin không reply lại mail này</p>"
                    + "<p>Thời gian gửi: " + new java.util.Date().toString() + "</p>"
                    + "<p style='margin-top: 20px; color: #7f8c8d;'>Trân trọng,<br/>Trường ĐH Nông Lâm</p>"
                    + "</div>";

            helper.setText(emailContent, true);
            mailSender.send(message);
        } catch (MessagingException | MailException e) {
            throw new RuntimeException("Lỗi khi gửi email: " + e.getMessage());
        }
    }
}