package com.solvix.backend.controller;

import com.solvix.backend.service.CodeforcesIngestionService;
import com.solvix.backend.service.scoring.CodeforcesScoringService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class TestController {

    private final CodeforcesIngestionService ingestionService;
    private final CodeforcesScoringService scoringService;

    public TestController(CodeforcesIngestionService ingestionService,
                          CodeforcesScoringService scoringService) {
        this.ingestionService = ingestionService;
        this.scoringService = scoringService;
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
}