package com.solvix.backend.model;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;
import java.util.List;

@Entity
@Table(name = "submissions")
@Getter
@Setter
public class Submission {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(nullable = false)
    private String platform; // "CODEFORCES" or "LEETCODE"

    @Column(name = "external_problem_id", nullable = false)
    private String externalProblemId; // e.g. "2239D"

    @Column(name = "problem_name")
    private String problemName;

    @ElementCollection
    @CollectionTable(name = "submission_tags", joinColumns = @JoinColumn(name = "submission_id"))
    @Column(name = "tag")
    private List<String> tags;

    @Column(name = "difficulty_rating")
    private Integer difficultyRating;

    @Column
    private String verdict;

    @Column(name = "solved_at", nullable = false)
    private LocalDateTime solvedAt;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();
}