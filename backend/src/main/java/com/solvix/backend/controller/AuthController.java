package com.solvix.backend.controller;

import com.solvix.backend.dto.AuthRequest;
import com.solvix.backend.service.AuthService;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/register")
    public String register(@RequestBody AuthRequest request) {
        return authService.register(request.getEmail(), request.getPassword(), request.getDisplayName());
    }

    @PostMapping("/login")
    public String login(@RequestBody AuthRequest request) {
        return authService.login(request.getEmail(), request.getPassword());
    }
}