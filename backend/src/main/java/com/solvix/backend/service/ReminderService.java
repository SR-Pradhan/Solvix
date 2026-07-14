package com.solvix.backend.service;

import com.solvix.backend.model.Reminder;
import com.solvix.backend.repository.ReminderRepository;
import com.solvix.backend.service.scoring.CodeforcesScoringService;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class ReminderService {

    private static final int RECENCY_THRESHOLD_DAYS = 14;
    private static final int MAX_REMINDERS_PER_RUN = 5;

    private final CodeforcesScoringService scoringService;
    private final ReminderRepository reminderRepository;

    public ReminderService(CodeforcesScoringService scoringService, ReminderRepository reminderRepository) {
        this.scoringService = scoringService;
        this.reminderRepository = reminderRepository;
    }

    public int generateReminders(Long userId) {
        List<CodeforcesScoringService.TagScore> weakTopics = scoringService.computeWeakTopics(userId);
        LocalDateTime last24h = LocalDateTime.now().minusHours(24);
        int created = 0;

        List<CodeforcesScoringService.TagScore> toRemind = weakTopics.stream()
                .filter(tag -> tag.recencyDays() >= RECENCY_THRESHOLD_DAYS)
                .limit(MAX_REMINDERS_PER_RUN)
                .toList();

        for (CodeforcesScoringService.TagScore tag : toRemind) {
            boolean alreadySent = reminderRepository
                    .findByUserIdAndTagAndTriggeredAtAfter(userId, tag.tag(), last24h)
                    .isPresent();
            if (alreadySent) continue;

            Reminder reminder = new Reminder();
            reminder.setUserId(userId);
            reminder.setTag(tag.tag());
            reminderRepository.save(reminder);
            created++;
        }
        return created;
    }

    public List<Reminder> getReminders(Long userId) {
        return reminderRepository.findByUserId(userId);
    }
}