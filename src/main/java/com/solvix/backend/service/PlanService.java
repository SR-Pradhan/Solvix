package com.solvix.backend.service;

import com.solvix.backend.client.GroqApiClient;
import com.solvix.backend.service.scoring.CodeforcesScoringService;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class PlanService {

    private final CodeforcesScoringService scoringService;
    private final GroqApiClient groqApiClient;

    public PlanService(CodeforcesScoringService scoringService, GroqApiClient groqApiClient) {
        this.scoringService = scoringService;
        this.groqApiClient = groqApiClient;
    }

    public String generateDailyPlan(Long userId) {
        List<CodeforcesScoringService.TagScore> weakTopics = scoringService.computeWeakTopics(userId);

        List<CodeforcesScoringService.TagScore> topWeak = weakTopics.stream()
                .limit(5)
                .collect(Collectors.toList());

        String prompt = buildPrompt(topWeak);
        return groqApiClient.generateContent(prompt);
    }

    private String buildPrompt(List<CodeforcesScoringService.TagScore> topWeak) {
        StringBuilder sb = new StringBuilder();
        sb.append("You are a DSA (Data Structures & Algorithms) coach for a competitive programming student. ");
        sb.append("Based on the following weak topics, write a short, motivating daily study plan. ");
        sb.append("For each topic, mention the accuracy percentage and how many days since last practiced, ");
        sb.append("then suggest a focus area. Keep the total response under 150 words. ");
        sb.append("Do not use markdown formatting, just plain text.\n\n");
        sb.append("Weak topics:\n");

        for (CodeforcesScoringService.TagScore tag : topWeak) {
            sb.append(String.format("- %s: %.1f%% accuracy, last practiced %d days ago\n",
                    tag.tag(), tag.accuracyPct(), tag.recencyDays()));
        }

        return sb.toString();
    }
}