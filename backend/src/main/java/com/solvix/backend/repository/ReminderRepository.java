package com.solvix.backend.repository;

import com.solvix.backend.model.Reminder;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

public interface ReminderRepository extends JpaRepository<Reminder, Long> {
    List<Reminder> findByUserId(Long userId);
    Optional<Reminder> findByUserIdAndTagAndTriggeredAtAfter(Long userId, String tag, LocalDateTime after);
}