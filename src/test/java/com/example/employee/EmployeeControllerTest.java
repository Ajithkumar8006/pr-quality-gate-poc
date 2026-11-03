package com.example.employee;

import com.example.employee.model.Employee;
import com.example.employee.controller.EmployeeController;
import com.example.employee.service.EmployeeService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

import java.util.List;
import java.util.Optional;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(EmployeeController.class)
class EmployeeControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private EmployeeService employeeService;

    @Test
    void getAllEmployeesReturnsEmployees() throws Exception {
        when(employeeService.getAllEmployees()).thenReturn(List.of(employee(1L)));

        mockMvc.perform(get("/api/employees"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].id").value(1))
                .andExpect(jsonPath("$[0].name").value("Alex Morgan"));
    }

    @Test
    void getEmployeeByIdReturnsEmployee() throws Exception {
        when(employeeService.getEmployeeById(1L)).thenReturn(Optional.of(employee(1L)));

        mockMvc.perform(get("/api/employees/1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(1))
                .andExpect(jsonPath("$.email").value("alex.morgan@example.com"));
    }

    @Test
    void getEmployeeByIdReturnsNotFoundWhenMissing() throws Exception {
        when(employeeService.getEmployeeById(42L)).thenReturn(Optional.empty());

        mockMvc.perform(get("/api/employees/42"))
                .andExpect(status().isNotFound());
    }

    @Test
    void createEmployeeReturnsCreatedEmployeeAndLocation() throws Exception {
        when(employeeService.createEmployee(any(Employee.class)))
                .thenReturn(employee(1L));

        mockMvc.perform(post("/api/employees")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"name":"Alex Morgan","department":"Engineering", "email":"alex.morgan@example.com"}
                                """))
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", "/api/employees/1"))
                .andExpect(jsonPath("$.id").value(1));
    }

    @Test
    void createEmployeeRejectsInvalidInput() throws Exception {
        mockMvc.perform(post("/api/employees")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"name":" ","department":"Engineering", "email":"not-an-email"}
                                """))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail").value("Invalid employee request"));

        verify(employeeService, never()).createEmployee(any(Employee.class));
    }

    @Test
    void deleteEmployeeReturnsNoContent() throws Exception {
        when(employeeService.deleteEmployee(1L)).thenReturn(true);

        mockMvc.perform(delete("/api/employees/1"))
                .andExpect(status().isNoContent());
    }

    @Test
    void deleteEmployeeReturnsNotFoundWhenMissing() throws Exception {
        when(employeeService.deleteEmployee(42L)).thenReturn(false);

        mockMvc.perform(delete("/api/employees/42"))
                .andExpect(status().isNotFound());
    }

    private Employee employee(Long id) {
        return new Employee(id, "Alex Morgan", "Engineering", "alex.morgan@example.com");
    }
}