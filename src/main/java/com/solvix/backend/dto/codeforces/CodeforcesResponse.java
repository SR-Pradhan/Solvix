package com.solvix.backend.dto.codeforces;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class CodeforcesResponse {
    private String status;
    private List<CodeforcesSubmission> result;

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public List<CodeforcesSubmission> getResult() { return result; }
    public void setResult(List<CodeforcesSubmission> result) { this.result = result; }
}