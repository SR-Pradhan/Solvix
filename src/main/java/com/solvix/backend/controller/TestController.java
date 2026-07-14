package com.solvix.backend.controller;

import com.solvix.backend.client.GroqApiClient;
import com.solvix.backend.service.CodeforcesIngestionService;
import com.solvix.backend.service.PlanService;
import com.solvix.backend.service.ReminderService;
import com.solvix.backend.service.WeeklyReportService;
import com.solvix.backend.service.scoring.CodeforcesScoringService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class TestController {

    private final CodeforcesIngestionService ingestionService;
    private final CodeforcesScoringService scoringService;
    private final GroqApiClient groqApiClient;
    private final PlanService planService;
    private final ReminderService reminderService;
    private final WeeklyReportService weeklyReportService;

    public TestController(CodeforcesIngestionService ingestionService,
                          CodeforcesScoringService scoringService,
                          GroqApiClient groqApiClient,
                          PlanService planService,
                          ReminderService reminderService,
                          WeeklyReportService weeklyReportService) {
        this.ingestionService = ingestionService;
        this.scoringService = scoringService;
        this.groqApiClient = groqApiClient;
        this.planService = planService;
        this.reminderService = reminderService;
        this.weeklyReportService = weeklyReportService;
    }

    @GetMapping("/test/sync")
    public String testSync(@RequestParam String handle) {
        int saved = ingestionService.syncUser(1L, handle);
        return "Saved " + saved + " new submissions for handle: " + handle;
    }

    @GetMapping("/test/weak-topics")
    public Object testWeakTopics() {
        return scoringService.computeWeakTopics(1L);
    }

    @GetMapping("/test/groq")
    public String testGroq() {
        return groqApiClient.generateContent("Say hello in one short sentence.");
    }

    @GetMapping("/test/daily-plan")
    public String testDailyPlan() {
        return planService.generateDailyPlan(1L);
    }

    @GetMapping("/test/reminders/generate")
    public String testGenerateReminders() {
        int count = reminderService.generateReminders(1L);
        return "Created " + count + " reminders";
    }

    @GetMapping("/test/reminders")
    public Object testGetReminders() {
        return reminderService.getReminders(1L);
    }

    @GetMapping("/test/weekly-report")
    public Object testWeeklyReport() {
        return weeklyReportService.generateReport(1L);
    }
}