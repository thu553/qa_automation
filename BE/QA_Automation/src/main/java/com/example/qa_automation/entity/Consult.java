package com.example.qa_automation.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.time.LocalDateTime;

@Entity
@Table(name = "consults")
@Data
public class Consult {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NotBlank
    @Column(nullable = false)
    private String question;

    @Column
    private String answer;

    @Email
    @NotBlank
    @Column(nullable = false)
    private String userEmail;

    @Column
    private LocalDateTime createdAt;

    @Column
    private boolean answered;
}