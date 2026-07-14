package com.solvix.backend.service;

import com.solvix.backend.client.CodeforcesApiClient;
import com.solvix.backend.dto.codeforces.CodeforcesResponse;
import com.solvix.backend.dto.codeforces.CodeforcesSubmission;
import com.solvix.backend.model.Submission;
import com.solvix.backend.repository.SubmissionRepository;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.Optional;

@Service
public class CodeforcesIngestionService {

    private final CodeforcesApiClient codeforcesApiClient;
    private final SubmissionRepository submissionRepository;

    public CodeforcesIngestionService(CodeforcesApiClient codeforcesApiClient,
                                      SubmissionRepository submissionRepository) {
        this.codeforcesApiClient = codeforcesApiClient;
        this.submissionRepository = submissionRepository;
    }

    public int syncUser(Long userId, String handle) {
        CodeforcesResponse response = codeforcesApiClient.getUserSubmissions(handle);

        if (response == null || !"OK".equals(response.getStatus()) || response.getResult() == null) {
            throw new RuntimeException("Codeforces API did not return OK status for handle: " + handle);
        }

        int savedCount = 0;

        for (CodeforcesSubmission cfSub : response.getResult()) {
            String externalProblemId = cfSub.getProblem().getContestId() + cfSub.getProblem().getIndex();

            // Dedupe: only keep the BEST verdict per problem, but for now (Step 9) we save every row.
            // We'll add proper dedupe logic in the scoring step — don't over-build this yet.
            Optional<Submission> existing = submissionRepository
                    .findByUserIdAndPlatformAndExternalProblemId(userId, "CODEFORCES", externalProblemId);

            if (existing.isPresent()) {
                continue; // already ingested this problem before, skip
            }

            Submission submission = new Submission();
            submission.setUserId(userId);
            submission.setPlatform("CODEFORCES");
            submission.setExternalProblemId(externalProblemId);
            submission.setProblemName(cfSub.getProblem().getName());
            submission.setTags(cfSub.getProblem().getTags());
            submission.setDifficultyRating(cfSub.getProblem().getRating());
            submission.setVerdict(cfSub.getVerdict());
            submission.setSolvedAt(
                    LocalDateTime.ofInstant(Instant.ofEpochSecond(cfSub.getCreationTimeSeconds()), ZoneId.systemDefault())
            );

            submissionRepository.save(submission);
            savedCount++;
        }

        return savedCount;
    }
}