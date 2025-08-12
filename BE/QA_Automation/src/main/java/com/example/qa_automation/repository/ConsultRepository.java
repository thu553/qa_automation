package com.example.qa_automation.repository;

import com.example.qa_automation.entity.Consult;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ConsultRepository extends JpaRepository<Consult, Long> {
    List<Consult> findByAnsweredFalseOrderByCreatedAtAsc();
}
