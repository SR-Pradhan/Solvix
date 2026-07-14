package com.solvix.backend.service.scoring;

import com.solvix.backend.model.Submission;
import com.solvix.backend.repository.SubmissionRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.*;

@Service
public class CodeforcesScoringService {

    private final SubmissionRepository submissionRepository;

    public CodeforcesScoringService(SubmissionRepository submissionRepository) {
        this.submissionRepository = submissionRepository;
    }

    public List<TagScore> computeWeakTopics(Long userId) {
        List<Submission> submissions = submissionRepository.findByUserIdAndPlatform(userId, "CODEFORCES");

        Map<String, Integer> totalAttemptsByTag = new HashMap<>();
        Map<String, Integer> okAttemptsByTag = new HashMap<>();
        Map<String, LocalDateTime> mostRecentOkByTag = new HashMap<>();

        for (Submission sub : submissions) {
            boolean isOk = "OK".equals(sub.getVerdict());
            for (String tag : sub.getTags()) {
                totalAttemptsByTag.merge(tag, 1, Integer::sum);
                if (isOk) {
                    okAttemptsByTag.merge(tag, 1, Integer::sum);
                    mostRecentOkByTag.merge(tag, sub.getSolvedAt(),
                            (existing, incoming) -> incoming.isAfter(existing) ? incoming : existing);
                }
            }
        }

        List<TagScore> results = new ArrayList<>();
        LocalDateTime now = LocalDateTime.now();

        for (String tag : totalAttemptsByTag.keySet()) {
            int total = totalAttemptsByTag.get(tag);
            int ok = okAttemptsByTag.getOrDefault(tag, 0);
            double accuracyPct = total == 0 ? 0 : (double) ok / total * 100;

            LocalDateTime lastOk = mostRecentOkByTag.get(tag);
            long recencyDays = lastOk == null ? 999 : ChronoUnit.DAYS.between(lastOk, now);

            double normalizedRecency = Math.min(recencyDays / 90.0, 1.0); // cap at 90 days for normalization
            double weakScore = (1 - accuracyPct / 100.0) * 0.6 + normalizedRecency * 0.4;

            results.add(new TagScore(tag, accuracyPct, recencyDays, weakScore));
        }

        results.sort((a, b) -> Double.compare(b.weakScore(), a.weakScore())); // highest weak_score first
        return results;
    }

    public record TagScore(String tag, double accuracyPct, long recencyDays, double weakScore) {}
}