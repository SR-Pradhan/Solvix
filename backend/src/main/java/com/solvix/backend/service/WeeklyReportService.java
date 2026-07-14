package com.solvix.backend.service;

import com.solvix.backend.model.Submission;
import com.solvix.backend.model.WeeklyReport;
import com.solvix.backend.repository.SubmissionRepository;
import com.solvix.backend.repository.WeeklyReportRepository;
import com.solvix.backend.service.scoring.CodeforcesScoringService;
import org.springframework.stereotype.Service;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.temporal.TemporalAdjusters;
import java.util.List;

@Service
public class WeeklyReportService {

    private final SubmissionRepository submissionRepository;
    private final CodeforcesScoringService scoringService;
    private final WeeklyReportRepository weeklyReportRepository;

    public WeeklyReportService(SubmissionRepository submissionRepository,
                               CodeforcesScoringService scoringService,
                               WeeklyReportRepository weeklyReportRepository) {
        this.submissionRepository = submissionRepository;
        this.scoringService = scoringService;
        this.weeklyReportRepository = weeklyReportRepository;
    }

    public WeeklyReport generateReport(Long userId) {
        LocalDate weekStart = LocalDate.now().with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY));

        List<Submission> submissions = submissionRepository.findByUserIdAndPlatform(userId, "CODEFORCES");
        long solvedThisWeek = submissions.stream()
                .filter(s -> "OK".equals(s.getVerdict()))
                .filter(s -> !s.getSolvedAt().toLocalDate().isBefore(weekStart))
                .count();

        List<CodeforcesScoringService.TagScore> scores = scoringService.computeWeakTopics(userId);
        String weakest = scores.isEmpty() ? "N/A" : scores.get(0).tag();
        String strongest = scores.isEmpty() ? "N/A" : scores.get(scores.size() - 1).tag();

        WeeklyReport report = weeklyReportRepository
                .findByUserIdAndWeekStart(userId, weekStart)
                .orElse(new WeeklyReport());

        report.setUserId(userId);
        report.setWeekStart(weekStart);
        report.setProblemsSolved((int) solvedThisWeek);
        report.setWeakestTag(weakest);
        report.setStrongestTag(strongest);

        return weeklyReportRepository.save(report);
    }
}