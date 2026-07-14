package com.solvix.backend.repository;

import com.solvix.backend.model.Submission;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface SubmissionRepository extends JpaRepository<Submission, Long> {

    List<Submission> findByUserIdAndPlatform(Long userId, String platform);

    Optional<Submission> findByUserIdAndPlatformAndExternalProblemId(
            Long userId, String platform, String externalProblemId);
}