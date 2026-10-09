# Task Executors

This package holds deterministic calculation kernels grouped by the main value
they estimate. The functions assume SI units at their boundaries: seconds,
meters, cubic meters, and rates in 1/s.

| Folder | Calculation output |
| --- | --- |
| `effective_removal_rate/` | Room loss rates and clean-air removal capacity |
| `well_mixed_concentration/` | Well-mixed concentration over time and at steady state |
| `inhalation_hazard/` | Per-susceptible airborne infection hazard |
| `indoor_reproductive_number/` | Expected transmissions over a scenario |
| `cumulative_exposure_bound/` | Maximum occupancy-time under a risk tolerance |
| `quanta_concentration/` | Inferred exhaled quanta concentration from outbreak data |
| `outbreak_attack_probability/` | Outbreak count normalization for Cq calibration |
| `outbreak_search/` | Scoped outbreak-search queries for Cq calibration |
| `evidence_extraction/` | Configured LLM adapters for structured outbreak-fact extraction |
| `respiratory_jet/` | Short-range respiratory plume correction |
| `relative_risk_index/` | Coarse relative event-risk score |
| `room_geometry/` | Room volume and effective height from admitted venue dimensions |
| `unit_conversion/` | Literature-facing conversions into SI units |

