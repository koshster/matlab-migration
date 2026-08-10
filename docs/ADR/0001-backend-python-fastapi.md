# ADR 0001 — Backend: Python 3.12 + FastAPI + Pydantic v2

**Status:** Accepted

## Decision
Use Python 3.12 with FastAPI as the HTTP framework and Pydantic v2 for data validation.

## Reason
The numerical core (NumPy/SciPy) maps directly from MATLAB. Python is the natural target for porting `genTruss.m`, `findSolutions.m`, and `trussSols.m`. FastAPI provides async support, automatic OpenAPI generation, and typed request/response models via Pydantic.

## Consequences
- `numpy.linalg.solve` replaces `linsolve`; `scipy.spatial.Delaunay` replaces MATLAB's `delaunay`.
- Type checking via `mypy --strict` is enforced; no `Any`.
- All numerical constants (tolerance, max attempts, etc.) are config values, not hardcoded in the port.
