# HSIF thesis visual-assets generation report

Date: 2026-11-19

## Generated figures and exports

Each figure has an editable Mermaid source at `diagram_sources/<figure-id>.mmd`, its exact-name JSON render specification at `diagram_sources/<figure-id>.json`, and PNG/SVG exports in the category directory listed below. The Python specification/generator and PowerShell PNG renderer are retained in `source/`.

| Figure | Editable source | PNG export | SVG export |
|---:|---|---|---|
| 2.1 | `diagram_sources/fig_2_1_overall_system_architecture.mmd` | `architecture/fig_2_1_overall_system_architecture.png` | `architecture/fig_2_1_overall_system_architecture.svg` |
| 2.2 | `diagram_sources/fig_2_2_frontend_backend_architecture.mmd` | `architecture/fig_2_2_frontend_backend_architecture.png` | `architecture/fig_2_2_frontend_backend_architecture.svg` |
| 2.3 | `diagram_sources/fig_2_3_backend_component_architecture.mmd` | `architecture/fig_2_3_backend_component_architecture.png` | `architecture/fig_2_3_backend_component_architecture.svg` |
| 2.4 | `diagram_sources/fig_2_4_audio_upload_workflow.mmd` | `workflows/fig_2_4_audio_upload_workflow.png` | `workflows/fig_2_4_audio_upload_workflow.svg` |
| 2.5 | `diagram_sources/fig_2_5_text_processing_workflow.mmd` | `workflows/fig_2_5_text_processing_workflow.png` | `workflows/fig_2_5_text_processing_workflow.svg` |
| 2.6 | `diagram_sources/fig_2_6_websocket_workflow.mmd` | `workflows/fig_2_6_websocket_workflow.png` | `workflows/fig_2_6_websocket_workflow.svg` |
| 2.7 | `diagram_sources/fig_2_7_speech_preprocessing_workflow.mmd` | `workflows/fig_2_7_speech_preprocessing_workflow.png` | `workflows/fig_2_7_speech_preprocessing_workflow.svg` |
| 2.8 | `diagram_sources/fig_2_8_hsr_architecture.mmd` | `human_state/fig_2_8_hsr_architecture.png` | `human_state/fig_2_8_hsr_architecture.svg` |
| 2.9 | `diagram_sources/fig_2_9_five_hsr_dimensions.mmd` | `human_state/fig_2_9_five_hsr_dimensions.png` | `human_state/fig_2_9_five_hsr_dimensions.svg` |
| 2.10 | `diagram_sources/fig_2_10_state_fusion_temporal_smoothing.mmd` | `human_state/fig_2_10_state_fusion_temporal_smoothing.png` | `human_state/fig_2_10_state_fusion_temporal_smoothing.svg` |
| 2.11 | `diagram_sources/fig_2_11_observation_validity.mmd` | `human_state/fig_2_11_observation_validity.png` | `human_state/fig_2_11_observation_validity.svg` |
| 2.12 | `diagram_sources/fig_2_12_adaptive_dialogue_workflow.mmd` | `dialogue/fig_2_12_adaptive_dialogue_workflow.png` | `dialogue/fig_2_12_adaptive_dialogue_workflow.svg` |
| 2.13 | `diagram_sources/fig_2_13_dialogue_strategy_decision.mmd` | `dialogue/fig_2_13_dialogue_strategy_decision.png` | `dialogue/fig_2_13_dialogue_strategy_decision.svg` |
| 2.14 | `diagram_sources/fig_2_14_llm_provider_integration.mmd` | `dialogue/fig_2_14_llm_provider_integration.png` | `dialogue/fig_2_14_llm_provider_integration.svg` |
| 2.15 | `diagram_sources/fig_2_15_database_erd.mmd` | `database_api/fig_2_15_database_erd.png` | `database_api/fig_2_15_database_erd.svg` |
| 2.16 | `diagram_sources/fig_2_16_api_interaction.mmd` | `database_api/fig_2_16_api_interaction.png` | `database_api/fig_2_16_api_interaction.svg` |
| 2.17 | `diagram_sources/fig_2_17_persistence_workflow.mmd` | `database_api/fig_2_17_persistence_workflow.png` | `database_api/fig_2_17_persistence_workflow.svg` |
| 2.18 | `diagram_sources/fig_2_18_deployment_architecture.mmd` | `deployment_security/fig_2_18_deployment_architecture.png` | `deployment_security/fig_2_18_deployment_architecture.svg` |
| 2.19 | `diagram_sources/fig_2_19_security_data_flow.mmd` | `deployment_security/fig_2_19_security_data_flow.png` | `deployment_security/fig_2_19_security_data_flow.svg` |
| 4.1 | `diagram_sources/fig_4_1_evaluation_methodology.mmd` | `evaluation/fig_4_1_evaluation_methodology.png` | `evaluation/fig_4_1_evaluation_methodology.svg` |
| 4.2 | `diagram_sources/fig_4_2_cremad_evaluation.mmd` | `evaluation/fig_4_2_cremad_evaluation.png` | `evaluation/fig_4_2_cremad_evaluation.svg` |
| 4.3 | `diagram_sources/fig_4_3_speech_benchmark.mmd` | `evaluation/fig_4_3_speech_benchmark.png` | `evaluation/fig_4_3_speech_benchmark.svg` |
| 4.4 | `diagram_sources/fig_4_4_hsr_benchmark.mmd` | `evaluation/fig_4_4_hsr_benchmark.png` | `evaluation/fig_4_4_hsr_benchmark.svg` |
| 4.5 | `diagram_sources/fig_4_5_dialogue_benchmark.mmd` | `evaluation/fig_4_5_dialogue_benchmark.png` | `evaluation/fig_4_5_dialogue_benchmark.svg` |
| 4.6 | `diagram_sources/fig_4_6_gemini_response_comparison.mmd` | `evaluation/fig_4_6_gemini_response_comparison.png` | `evaluation/fig_4_6_gemini_response_comparison.svg` |

## Verification performed

- 25 figure specifications generated with 25 Mermaid source files and 25 JSON specifications.
- 25 SVGs generated from the shared Python figure specifications; the SVG files are structurally parsed as XML during verification.
- 25 PNGs rendered at 300 DPI metadata with dimensions larger than 1,800 pixels wide; every PNG was opened through System.Drawing to verify decoding and dimensions.
- Representative architecture, workflow, strategy, ERD, and evaluation figures were visually inspected. Mermaid CLI is not installed, so `.mmd` source syntax was not independently rendered by Mermaid. The PNG/SVG outputs were rendered from the same Python specifications, not from Mermaid source.
- No application tests were run because no application code changed.

## Source files

- `source/build_assets.py` — declarative source data for every diagram/chart and SVG/Mermaid/document-catalog generator.
- `source/render_png.ps1` — PNG export from the generated per-figure JSON specifications.
- `diagram_sources/fig_*.mmd` — editable Mermaid representations.
- `diagram_sources/fig_*.json` — per-figure renderer inputs.

## Unverified items and discrepancies

- Thesis, paper, PowerPoint, and capstone template were not found; no existing figures, claims, captions, numbering, or placeholders could be reconciled.
- The ERD represents SQLAlchemy declarations, not a live database schema inspection.
- No live database, provider, or production deployment was verified for this task.
- No genuine application screenshots were supplied/captured.
- The Gemini rating artifact is exploratory and reviewer provenance is missing; its README has conflicting values. The plotted values follow the audit’s artifact-derived calculations.
- CREMA-D files are not tracked and the results lack a code revision fingerprint. Reported metrics must remain scoped to the identified artifact.
- HSR and dialogue synthetic tests are behavior checks, not user/model accuracy or LLM quality studies.
- These generated figures do not resolve unknown thesis references, authorship, costs, or human-study details.
