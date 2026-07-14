package com.solvix.backend.controller;

import com.solvix.backend.client.GroqApiClient;
import com.solvix.backend.service.CodeforcesIngestionService;
import com.solvix.backend.service.PlanService;
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

    public TestController(CodeforcesIngestionService ingestionService,
                          CodeforcesScoringService scoringService,
                          GroqApiClient groqApiClient,
                          PlanService planService) {
        this.ingestionService = ingestionService;
        this.scoringService = scoringService;
        this.groqApiClient = groqApiClient;
        this.planService = planService;
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
}