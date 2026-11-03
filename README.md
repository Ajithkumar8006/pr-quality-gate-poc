# Employee Management REST API

A small in-memory REST API for managing employees. It is built with Java 17 and Spring Boot and is intended to serve as the Java application for a later GitHub Actions and CodeQL quality-gate POC. This repository does not include CI workflows or security-gate configuration.

## Architecture

- `EmployeeController` exposes the HTTP API and delegates application operations.
- `EmployeeService` owns employee storage and ID generation using thread-safe in-memory components.
- `Employee` is an immutable request/response model with Jakarta Bean Validation constraints.
- `ApiExceptionHandler` returns stable, non-sensitive error messages for invalid request bodies.
- `EmployeeControllerTest` exercises the HTTP contract with MockMvc and a mocked service.

## Technology

- Java 17
- Spring Boot 3.4
- Maven
- Spring MVC and Jakarta Bean Validation
- JUnit 5, Spring Boot Test, and MockMvc

## Prerequisites

- JDK 17
- Maven 3.6.3 or later

Check the installed tools with `java -version` and `mvn -version`.

## Build and test

From the project root, run:

```sh
mvn clean compile
mvn test
mvn clean package
```

## Start the application

```sh
mvn spring-boot:run
```

The API listens on `http://localhost:8080`. Data is kept in memory and is cleared when the application restarts.

## API

| Method | Path | Success | Description |
| --- | --- | --- | --- |
| `GET` | `/api/employees` | `200 OK` | Return all employees, or an empty array. |
| `GET` | `/api/employees/{id}` | `200 OK` | Return one employee; `404 Not Found` if absent. |
| `POST` | `/api/employees` | `201 Created` | Validate and create an employee. |
| `DELETE` | `/api/employees/{id}` | `204 No Content` | Delete an employee; `404 Not Found` if absent. |

Employee request fields are `name`, `department`, and `email`. The ID is assigned by the service and must not be supplied when creating an employee. Name and department must be nonblank and at most 100 characters. Email must be nonblank, valid, and at most 254 characters. Invalid JSON or validation failures return `400 Bad Request` with a generic problem detail. Missing employee IDs return `404 Not Found`.

### Create an employee

```sh
curl -i -X POST http://localhost:8080/api/employees \
	-H 'Content-Type: application/json' \
	-d '{"name":"Alex Morgan","department":"Engineering","email":"alex.morgan@example.com"}'
```

Example response (`201 Created`):

```json
{
	"id": 1,
	"name": "Alex Morgan",
	"department": "Engineering",
	"email": "alex.morgan@example.com"
}
```

### List employees

```sh
curl http://localhost:8080/api/employees
```

Example response (`200 OK`):

```json
[
	{
		"id": 1,
		"name": "Alex Morgan",
		"department": "Engineering",
		"email": "alex.morgan@example.com"
	}
]
```

### Get or delete an employee

```sh
curl -i http://localhost:8080/api/employees/1
curl -i -X DELETE http://localhost:8080/api/employees/1
```