package com.solvix.backend.dto.codeforces;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class CodeforcesSubmission {
    private Long id;
    private Long creationTimeSeconds;
    private CodeforcesProblem problem;
    private String verdict;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getCreationTimeSeconds() { return creationTimeSeconds; }
    public void setCreationTimeSeconds(Long creationTimeSeconds) { this.creationTimeSeconds = creationTimeSeconds; }
    public CodeforcesProblem getProblem() { return problem; }
    public void setProblem(CodeforcesProblem problem) { this.problem = problem; }
    public String getVerdict() { return verdict; }
    public void setVerdict(String verdict) { this.verdict = verdict; }
}