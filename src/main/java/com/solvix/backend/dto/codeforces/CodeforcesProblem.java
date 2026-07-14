package com.solvix.backend.dto.codeforces;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class CodeforcesProblem {
    private Long contestId;
    private String index;
    private String name;
    private Integer rating;
    private List<String> tags;

    public Long getContestId() { return contestId; }
    public void setContestId(Long contestId) { this.contestId = contestId; }
    public String getIndex() { return index; }
    public void setIndex(String index) { this.index = index; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public Integer getRating() { return rating; }
    public void setRating(Integer rating) { this.rating = rating; }
    public List<String> getTags() { return tags; }
    public void setTags(List<String> tags) { this.tags = tags; }
}