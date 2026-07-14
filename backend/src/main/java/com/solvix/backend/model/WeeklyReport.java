package com.solvix.backend.model;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDate;

@Entity
@Table(name = "weekly_reports")
@Getter
@Setter
public class WeeklyReport {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "week_start", nullable = false)
    private LocalDate weekStart;

    @Column(name = "problems_solved", nullable = false)
    private int problemsSolved;

    @Column(name = "weakest_tag")
    private String weakestTag;

    @Column(name = "strongest_tag")
    private String strongestTag;
}