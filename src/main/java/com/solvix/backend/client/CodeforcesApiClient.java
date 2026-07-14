package com.solvix.backend.client;

import com.solvix.backend.dto.codeforces.CodeforcesResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class CodeforcesApiClient {

    private final RestClient restClient;

    public CodeforcesApiClient() {
        this.restClient = RestClient.builder()
                .baseUrl("https://codeforces.com/api")
                .build();
    }

    public CodeforcesResponse getUserSubmissions(String handle) {
        return restClient.get()
                .uri(uriBuilder -> uriBuilder
                        .path("/user.status")
                        .queryParam("handle", handle)
                        .queryParam("from", 1)
                        .queryParam("count", 100)
                        .build())
                .retrieve()
                .body(CodeforcesResponse.class);
    }
}