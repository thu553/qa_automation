package com.example.qa_automation.service;

import com.example.qa_automation.entity.Consult;
import com.example.qa_automation.repository.ConsultRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Service
public class ConsultService {
    @Value("${fastapi.url}")
    private String fastApiUrl;

    private final RestTemplate restTemplate;
    private final ConsultRepository consultRepository;

    public ConsultService(RestTemplate restTemplate, ConsultRepository consultRepository) {
        this.restTemplate = restTemplate;
        this.consultRepository = consultRepository;
    }

    public List<Map<String, Object>> searchQuestion(@NotBlank String question) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<Map<String, String>> request = new HttpEntity<>(Map.of("question", question), headers);
//            String jsonResponse = restTemplate.postForObject(fastApiUrl + "/search", request, String.class);
//            System.out.println("debug đâyyyyyyyyyyyyyyyyyy "+jsonResponse);
            return restTemplate.postForObject(fastApiUrl + "/search", request, List.class);
        } catch (HttpClientErrorException e) {
            throw new RuntimeException("Lỗi khi gọi FastAPI: " + e.getMessage());
        }
    }

    public void likeQuestion(@NotBlank String question, @NotBlank String answer) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<Map<String, String>> request = new HttpEntity<>(Map.of("question", question, "answer", answer), headers);
            restTemplate.postForObject(fastApiUrl + "/update", request, String.class);
        } catch (HttpClientErrorException e) {
            throw new RuntimeException("Lỗi khi gọi FastAPI: " + e.getMessage());
        }
    }

    public void sendConsult(@NotBlank String question, @Email String userEmail) {
        Consult consult = new Consult();
        consult.setQuestion(question);
        consult.setUserEmail(userEmail);
        consult.setCreatedAt(LocalDateTime.now());
        consult.setAnswered(false);
        consultRepository.save(consult);
    }

    public List<Consult> getAllConsults() {
        return consultRepository.findAll();
    }

    public List<Consult> getUnansweredConsults() {
        return consultRepository.findByAnsweredFalseOrderByCreatedAtAsc();
    }

    public Consult answerConsult(Long consultId, @NotBlank String answer) {
        System.out.println("Consult ID: " + consultId + ", Answer: " + answer);
        Consult consult = consultRepository.findById(consultId)
                .orElseThrow(() -> new RuntimeException("Không tìm thấy câu hỏi"));
        consult.setAnswer(answer);
        consult.setAnswered(true);
        consultRepository.save(consult);

        // Gửi lên FastAPI để update hệ thống AI
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<Map<String, String>> request = new HttpEntity<>(
                    Map.of("question", consult.getQuestion(), "answer", answer), headers
            );
            restTemplate.postForObject(fastApiUrl + "/update", request, String.class);
        } catch (HttpClientErrorException e) {
            throw new RuntimeException("Lỗi khi gọi FastAPI (update): " + e.getMessage());
        }

        return consult;
    }

    public Consult updateConsult(Long id, String question) {
        Consult consult = consultRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Consult not found"));
        consult.setQuestion(question);
        return consultRepository.save(consult);
    }

    public void deleteConsult(Long id) {
        consultRepository.deleteById(id);
    }
}