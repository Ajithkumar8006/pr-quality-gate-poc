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

## CodeQL PR quality gate

The workflow at `.github/workflows/codeql-pr-quality-gate.yml` builds and tests with Temurin Java 17, runs CodeQL for Java, writes the CodeQL SARIF report, uploads it to code scanning, and evaluates every result in that report. It does **not** compare against `main` or filter to newly introduced findings. Baseline comparison is not implemented.

The gate reads `security-severity` from each SARIF rule and associates results with rule IDs. Scores 9.0-10.0 are Critical, 7.0-8.9 High, 4.0-6.9 Medium, and below 4.0 Low. Critical, High, and Medium always fail. Missing, malformed, non-finite, or out-of-range severity metadata is counted as Unclassified; the default policy is to fail on Unclassified. A manual run can explicitly choose `pass`, but that only exempts Unclassified findings and never permits Critical, High, or Medium findings. Missing or structurally invalid SARIF always fails.

The Actions job summary reports findings by severity, the unclassified policy, build/test/scan outcomes, and the gate result. The evaluator's stdlib-only regression tests cover score boundaries, rule matching, unknown metadata, empty results, and missing/invalid reports:

```sh
python3 -m unittest tools.test_codeql_sarif_gate
```

### GitHub requirements and PR availability

- Workflow permissions are limited to `contents: read` and `security-events: write`; no repository secrets are required. Repository or organization Actions policy must allow the listed GitHub actions.
- Code scanning must be available for the repository. Public repositories can use GitHub code scanning; private/internal repositories generally require GitHub Advanced Security licensing and enablement. Check **Settings > Code security and analysis**.
- GitHub uses the workflow definition on the PR's base branch for `pull_request` processing. Since this file is initially only on the feature branch, it will not validate a PR targeting `main` until an administrator makes the workflow available on `main` (for example, by separately adding/approving the workflow file). A PR cannot bootstrap its own required workflow check. Branch protection/rulesets requiring this check also require administrator configuration.
- `workflow_dispatch` is included, but GitHub requires the workflow file to exist on the repository's default branch before it can be manually dispatched. Therefore feature-branch-only manual runs also require the workflow to be made available on the default branch. Without that administrator step, use a separate test repository with this workflow on its default branch, or run the evaluator tests locally. A manual dispatch is not a PR event and does not prove PR validation works.
- To avoid changing `main`, an administrator can use a separate test repository whose default branch contains this workflow, then test PRs from a test feature branch into that repository's default branch. This verifies event and action behavior, but is not a run against this repository's actual PR.

### Branch and PR steps

From a clone with this feature branch checked out:

```sh
git switch feature/codeql-quality-gate-poc
git push -u origin feature/codeql-quality-gate-poc
```

Create a PR with base `main` and compare/head `feature/codeql-quality-gate-poc`, either in GitHub's PR UI or with GitHub CLI:

```sh
gh pr create --base main --head feature/codeql-quality-gate-poc
```

Do not merge the PR to test the workflow. A pushed branch can be tested once an administrator has made the workflow available as described above. For manual testing, open **Actions > CodeQL PR Quality Gate > Run workflow**, select the feature branch, and leave the Unclassified policy at `fail` unless there is a specific reason to test the configurable `pass` behavior. `workflow_dispatch` must first be present on the default branch.

### Scenario testing

- Valid application and no findings: compile, tests, scan, and gate should pass.
- Compilation error: make a temporary change on an isolated test branch; Build should fail and later validation steps should be skipped. Revert the temporary change after observing the run.
- Unit test failure: introduce a temporary failing test on an isolated test branch; Unit tests should fail. Remove it in a follow-up commit.
- Critical, High, or Medium: evaluator tests use synthetic SARIF metadata to validate all blocking thresholds. To test actual CodeQL detection, use an isolated test repository or temporary feature-branch-only test code with a CodeQL-recognized weakness. Query severity is defined by the CodeQL query metadata, so application code alone cannot reliably force an arbitrary CVSS bucket. Never add such test code to `main`; remove it from the test branch after verification.
- Low-only: synthetic SARIF with scores below 4.0 passes; real CodeQL results pass only when no blocking or default-blocking Unclassified results are present.
- No findings: a valid SARIF run with an empty `results` array passes.
- Missing or invalid SARIF: the evaluator rejects a missing file, malformed JSON, unsupported SARIF version, or invalid required report structure and fails.

Run the SARIF evaluator tests locally with the command above. They validate policy behavior, not GitHub-hosted CodeQL execution. For an actual scan, inspect **Security > Code scanning** in the repository after a successful analysis; the SARIF is also uploaded by the workflow. Do not report PR validation as passed until the `pull_request` workflow has actually run on a PR targeting `main`.