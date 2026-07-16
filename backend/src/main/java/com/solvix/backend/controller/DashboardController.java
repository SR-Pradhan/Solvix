package com.solvix.backend.controller;

import com.solvix.backend.service.PlanService;
import com.solvix.backend.service.scoring.CodeforcesScoringService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class DashboardController {

    private final CodeforcesScoringService scoringService;
    private final PlanService planService;

    public DashboardController(CodeforcesScoringService scoringService, PlanService planService) {
        this.scoringService = scoringService;
        this.planService = planService;
    }

    @GetMapping("/api/dashboard/weak-topics")
    public Object weakTopics(HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        return scoringService.computeWeakTopics(userId);
    }

    @GetMapping("/api/plans/daily")
    public String dailyPlan(HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        return planService.generateDailyPlan(userId);
    }
}