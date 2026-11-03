package com.example.employee.model;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Null;
import jakarta.validation.constraints.Size;

public record Employee(
        @Null(message = "ID must not be provided") Long id,
        @NotBlank @Size(max = 100) String name,
        @NotBlank @Size(max = 100) String department,
        @NotBlank @Email @Size(max = 254) String email) {
}