package com.solvix.backend.repository;

import com.solvix.backend.model.PlatformConnection;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface PlatformConnectionRepository extends JpaRepository<PlatformConnection, Long> {

    Optional<PlatformConnection> findByUserIdAndPlatform(Long userId, String platform);
}