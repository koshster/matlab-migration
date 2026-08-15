# Statics Platform — Backend Architecture & Guide

## 1. Executive Summary

This backend powers the web-based Statics Problem Platform designed to replace legacy MATLAB desktop applications for engineering education. 

Students access homework problems directly in their web browser without installing MATLAB. The backend dynamically synthesizes randomized statics problems (starting with 2D Trusses, and extensible to Rigid Bodies, Frames, and Beams), evaluates student answers server-side with numerical tolerances, and securely records attempts in an access-controlled database.

---

## 2. Core Technologies Explained in Plain Terms

* **FastAPI (Python Web Server)**: The engine that listens for requests from the browser, runs our mechanics algorithms, and sends back problem diagrams and grading results.
* **Docker & Docker Compose**: Packages the Python code, dependencies, and database into isolated virtual containers. This ensures the application runs identically on any computer (Mac, Windows, Linux, or cloud servers) without configuration conflicts.
* **PostgreSQL (Database)**: A relational database where student accounts, assignments, random problem seeds, and attempt logs are stored.
* **SQLAlchemy & Alembic (Database Manager & Migrations)**:
  * *SQLAlchemy* connects Python code to the database without requiring raw database query languages.
  * *Alembic* acts as version control for database tables, ensuring schema updates can be applied smoothly over time.
* **NumPy & SciPy (Numerical Physics Engine)**: Python scientific computing libraries that perform linear algebra operations, matrix solutions, and Delaunay geometry triangulation.

---

## 3. SOLID Design Principles (Why the Architecture Scales)

To prevent the code duplication and maintenance challenges of the legacy MATLAB desktop apps, this backend strictly follows the **SOLID** software engineering principles:

* **S — Single Responsibility Principle (SRP)**:
  * *Concept*: Every component has one, and only one, job.
  * *In our code*: `geometry.py` only creates joint coordinates and triangles. `solver.py` only performs physics matrix algebra. `models.py` only defines database tables. No single file tries to do everything.
* **O — Open-Closed Principle (OCP)**:
  * *Concept*: Open for extension, closed for modification.
  * *In our code*: When adding future problem types (such as 2D Frames, Beams, or Centroids), we simply write one new domain class and register it with `ProblemRegistry`. We **never** need to modify the web controllers, database schemas, or grading pipelines.
* **L — Liskov Substitution Principle (LSP)**:
  * *Concept*: Any specialized component can be swapped in without breaking the system.
  * *In our code*: Every problem domain implements `ProblemGeneratorProtocol`. Whether the system is handling a 3-node Truss or a future 10-node Frame, the API server interacts with them identically.
* **I — Interface Segregation Principle (ISP)**:
  * *Concept*: Components only rely on the specific methods they need.
  * *In our code*: The student presentation contract (`ProblemDisplayData`) is completely separated from the server-side grading solver (`solve`), ensuring zero solution leakage to the browser.
* **D — Dependency Inversion Principle (DIP)**:
  * *Concept*: Depend on high-level abstractions, not hardcoded concrete implementations.
  * *In our code*: The web routes depend on abstract protocols and database session interfaces (`AsyncSession`), not on specific database drivers or hardcoded problem files.

---

## 4. How a Statics Problem Works (Workflow Diagram)


```mermaid
sequenceDiagram
    autonumber
    actor Student
    participant Frontend as React Web App
    participant Controller as FastAPI Server
    participant Generator as Problem Engine
    participant Solver as Matrix Solver (SciPy)
    participant Database as PostgreSQL Database

    Note over Student,Database: Step 1: Homework Generation
    Student->>Frontend: Opens Assignment Problem
    Frontend->>Controller: GET Problem (assignment_id, problem_index)
    Controller->>Database: Fetch Student Seed (e.g. seed = 42)
    Database-->>Controller: Return Seed & Parameters
    Controller->>Generator: generate(seed, params)
    Generator-->>Controller: Return Geometry, Supports, Loads (NO Solution)
    Controller-->>Frontend: Send Visual SVG Primitives & Answer Form
    Frontend-->>Student: Renders Interactive 2D Problem Diagram

    Note over Student,Database: Step 2: Answer Submission & Grading
    Student->>Frontend: Submits Calculated Member Forces & States
    Frontend->>Controller: POST Submission (answers, seed)
    Controller->>Generator: check(seed, answers, tolerance = 0.01)
    Generator->>Solver: solve(seed) -> Ground Truth Reactions & Forces
    Solver-->>Generator: Ground Truth Solution Values
    Generator->>Generator: Compare Student Answers against Ground Truth
    Generator-->>Controller: Grading Verdicts & Score (Pass / Fail)
    Controller->>Database: Save Attempt Log & Update Student Score
    Controller-->>Frontend: Return Pass/Fail Status & Feedback
    Frontend-->>Student: Display Real-Time Grading Results
```

---

## 5. Mechanics Generation & Equilibrium Rules

The 2D Truss problem generator follows classical structural analysis principles:
1. **Integer Coordinate Grid**: All joints/nodes lie on clean integer coordinates for ease of student calculation.
2. **Angle Invariant**: Internal member angles are strictly constrained to at least 45 degrees, preventing needle-thin or overlapping members.
3. **Simple Truss Determinacy**: Structural geometry enforces the planar simple truss formula:
   $$m = 2n - 3$$
   *(where $m$ is member count and $n$ is joint count)*.
4. **Support Boundary Conditions**: Pin and roller supports are placed on boundary joints with guaranteed moment arms, ensuring static determinacy (non-singular equilibrium matrix).
5. **Applied Point Loads**: Integer force magnitudes (1 to 5 kN) are applied strictly to unsupported upper joints.

---

## 6. Database Schema & Entity Relationships

The database maintains strict separation between course administration and problem mechanics. The Entity-Relationship diagram below illustrates how all records link together:

```mermaid
erDiagram
    STUDENT ||--o{ COURSE_ENROLLMENT : holds
    COURSE ||--o{ COURSE_ENROLLMENT : rosters
    INSTRUCTOR ||--o{ COURSE : teaches
    COURSE ||--o{ ASSIGNMENT : contains
    ASSIGNMENT ||--o{ ASSIGNMENT_PROBLEM : includes
    ASSIGNMENT ||--o{ STUDENT_ASSIGNMENT : tracks
    STUDENT ||--o{ STUDENT_ASSIGNMENT : undertakes
    STUDENT_ASSIGNMENT ||--o{ SUBMISSION : records

    STUDENT {
        uuid id PK
        string pid UK "UCSD Student PID (e.g. A12345678)"
        string email UK "@ucsd.edu university email"
        string name "Student full name"
        datetime created_at
    }

    INSTRUCTOR {
        uuid id PK
        string email UK "Login email"
        string password_hash "Argon2id password hash"
        string name "Instructor / TA name"
        datetime created_at
    }

    COURSE {
        uuid id PK
        uuid instructor_id FK "Course creator"
        string code "e.g. MAE 130A"
        string term "e.g. Fall 2026"
        datetime created_at
    }

    COURSE_ENROLLMENT {
        uuid id PK
        uuid course_id FK "Course section"
        uuid student_id FK "Enrolled student"
        string status "active, dropped, auditing"
        datetime enrolled_at
        datetime dropped_at "Set if student drops course"
    }

    ASSIGNMENT {
        uuid id PK
        uuid course_id FK "Owning course"
        string title "e.g. Homework 1: Trusses"
        float tolerance "Default 0.01 (+/- 1%)"
        string feedback_mode "Default per_field"
        int max_attempts "Default NULL (Unlimited)"
        float penalty_per_attempt "Default 0.0"
        string scoring_strategy "Default pass_fail (1 or 0)"
        boolean allow_late "Default false (No late accepted)"
        float late_penalty_rate "Default 0.0"
        boolean is_active "Default true"
        datetime due_at "Official deadline"
        datetime hard_deadline_at "Hard cutoff"
        datetime created_at
    }

    ASSIGNMENT_PROBLEM {
        uuid id PK
        uuid assignment_id FK "Owning assignment"
        string problem_type "e.g. truss, frame_2d"
        int order_index "Problem slot (1 to N)"
        jsonb params "Config parameters (e.g. num_nodes)"
    }

    STUDENT_ASSIGNMENT {
        uuid id PK
        uuid student_id FK "Student"
        uuid assignment_id FK "Assignment"
        int seed "Unique immutable random seed per student/assignment"
        datetime started_at
        datetime submitted_at
        float final_score "Total assignment grade"
    }

    SUBMISSION {
        uuid id PK
        uuid student_assignment_id FK "Student session"
        uuid assignment_problem_id FK "Problem slot"
        int attempt_number "Attempt count (1, 2, 3...)"
        jsonb answers "Submitted student answer dictionary"
        float raw_score "Unadjusted score (1.0 or 0.0)"
        float net_score "Score after any penalties"
        boolean is_passed "True if all answers within tolerance"
        jsonb field_verdicts "Detailed per-member pass/fail verdicts"
        datetime submitted_at
    }
```

---

## 7. Architecture & File Structure

```mermaid
graph TD
    Client["Student / Instructor Browser"] -->|HTTP / JSON| Controller["FastAPI Controllers (app/api/v1/)"]
    
    subgraph Backend Architecture
        Controller -->|Lookup| Registry["Problem Registry (app/problems/registry.py)"]
        Controller -->|Query / Save| Session["Async Database Session (app/db/session.py)"]
        
        Registry -->|Dispatch| Domain["Problem Domain Engine (app/problems/truss/)"]
        Domain -->|Generate| Geometry["Geometry & Supports Builder"]
        Domain -->|Solve| Solver["Matrix Equilibrium Solver (A * s = b)"]
        
        Session -->|Read / Write| Postgres[("PostgreSQL Database")]
    end
```

### Directory Layout

```
backend/
├── alembic/                 # Database schema migration scripts
├── app/
│   ├── api/v1/              # Web route controllers (health, problems, assignments)
│   ├── core/                # Configuration and environment settings
│   ├── db/                  # Database session and SQLAlchemy table models
│   │   ├── session.py       # Async engine & get_db dependency
│   │   └── models.py        # Relational ORM models
│   └── problems/            # Mechanics domain engine
│       ├── base.py          # Unified problem generator interface protocol
│       ├── registry.py      # Dynamic problem type registry
│       └── truss/           # 2D Truss generator, geometry, supports, loads, solver
│           ├── generator.py # TrussGenerator implementing protocol
│           ├── geometry.py  # Delaunay triangulation & angle checks
│           ├── supports.py  # Pin & roller support placement
│           ├── loads.py     # External point force generator
│           └── solver.py    # Reactions & member forces linear solvers
├── tests/                   # Automated test suite (physics, database, API routes)
├── Dockerfile               # Container build blueprint
└── pyproject.toml           # Python dependency and build configuration
```

---

## 8. How to Run and Test the Backend (Step-by-Step Guide)


You do not need prior software engineering experience or Python installations on your computer to run and test this backend. Docker manages all dependencies automatically.

---

### Step 1: Ensure Docker Desktop is Running
1. Open the **Docker Desktop** application from your Applications or Start Menu.
2. Wait a few seconds until the status in the bottom-left corner turns green and indicates **"Engine running"**.

---

### Step 2: Start the Backend Server
Open your terminal (PowerShell on Windows or Terminal on Mac) in the project directory and run:

```bash
docker compose up backend postgres
```

What happens:
* Starts the PostgreSQL database container.
* Starts the FastAPI backend server with live auto-reloading.

---

### Step 3: Test and Generate Problems in Your Web Browser
Once the backend is running, open your web browser (Chrome, Safari, Edge, or Firefox) and navigate to:

**`http://localhost:8000/api/docs`**

This opens an interactive graphical testing dashboard (Swagger UI):
1. Scroll to the **`problems`** section.
2. Click on **`POST /api/v1/problems/{problem_type}/generate`**.
3. Click the white **Try it out** button on the right.
4. Set `problem_type` to: `truss`
5. In the request body text box, enter:
   ```json
   {
     "seed": 42
   }
   ```
6. Click the blue **Execute** button.
7. Under **Server response (Code 200)**, you will see the generated structural geometry (joints, member connections, pin/roller supports, and downward point loads).

---

### Step 4: Run the Complete Automated Verification Test Suite
To verify that all physics math, database operations, and API endpoints are working correctly without starting the browser, open a new terminal window and run:

```bash
docker compose run --rm backend pytest -v
```

What this test suite verifies:
* **Physics & Solvability (`test_problems.py`)**: Tests 40+ random seeds to verify that joint equilibrium equations ($\sum F_x = 0, \sum F_y = 0, \sum M = 0$), matrix solver calculations, minimum $45^\circ$ angles, integer coordinates, and $m = 2n - 3$ determinacy are 100% mathematically correct.
* **Security & Invariants**: Confirms that internal reaction forces and member answers are never leaked in student-facing payloads.
* **Database & Enrollments (`test_db.py`)**: Verifies that instructors, student rosters, courses, assignment problem slots, student seeds, and attempt logs persist correctly.
* **API Endpoints (`test_api_problems.py`)**: Verifies that the web server answers generation and grading requests properly.

A green `PASSED` next to every test confirms that the backend is fully verified and ready.

---

### Step 5: How to Stop the Backend
When you are finished testing, return to the terminal where the server is running and press **`Ctrl + C`** on your keyboard to shut down the containers cleanly.
