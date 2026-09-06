# Documentation

| Read this | For |
| --- | --- |
| [deployment.md](deployment.md) | running the analyzer for other people: Docker Compose, single container, reverse proxy, configuration, sizing, operations |
| [development.md](development.md) | local setup of the three projects, the test suites, editing the knowledge base, supporting a new OR-Tools version |
| [architecture.md](architecture.md) | how parser, backend, knowledge base and UI fit together, and why the analysis is line-anchored |
| [legacy-streamlit-app.md](legacy-streamlit-app.md) | the Streamlit app in the repository root: running it, its structure, its screenshots |
| [changelog.md](changelog.md) | notable changes to both implementations |

Component documentation lives next to the code:

| Where | What |
| --- | --- |
| [`v2/README.md`](../v2/README.md) | map of the v2 stack |
| [`v2/cpsatlog/README.md`](../v2/cpsatlog/README.md) | the parser library as a library: API, models, supported versions |
| [`v2/knowledge/README.md`](../v2/knowledge/README.md) | which file holds which text, and the format of each |
| [`v2/corpus/README.md`](../v2/corpus/README.md) | the committed benchmark log corpus and how to regenerate it |
| [`benchmarks/README.md`](../benchmarks/README.md) | the harness that collects logs from public instance sets, and the audits done with it |
