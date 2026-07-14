package com.solvix.backend.model;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Entity
@Table(name = "platform_connections")
@Getter
@Setter
public class PlatformConnection {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(nullable = false)
    private String platform;

    @Column(name = "handle_or_repo", nullable = false)
    private String handleOrRepo;

    @Column(name = "sync_status")
    private String syncStatus = "OK";

    @Column(name = "last_synced_at")
    private LocalDateTime lastSyncedAt;
}