package com.example.employee.service;

import com.example.employee.model.Employee;
import org.springframework.stereotype.Service;

import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.atomic.AtomicLong;

@Service
public class EmployeeService {

    private final ConcurrentMap<Long, Employee> employees = new ConcurrentHashMap<>();
    private final AtomicLong nextId = new AtomicLong(1);

    public List<Employee> getAllEmployees() {
        return employees.values().stream()
                .sorted(Comparator.comparing(Employee::id))
                .toList();
    }

    public Optional<Employee> getEmployeeById(long id) {
        return Optional.ofNullable(employees.get(id));
    }

    public Employee createEmployee(Employee employee) {
        Employee created = new Employee(
                nextId.getAndIncrement(),
                employee.name(),
                employee.department(),
                employee.email());
        employees.put(created.id(), created);
        return created;
    }

    public boolean deleteEmployee(long id) {
        return employees.remove(id) != null;
    }
}