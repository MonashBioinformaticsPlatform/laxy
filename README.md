# Laxy Genomics Pipelines

## Fronted development server

```
cd laxy_frontend
npm install
npm start
open http://localhost:9997/
```

## Creating the UML diagram(s) for the Django models

```bash
./manage.py graph_models --pygraphviz -a -g -o docs/models_uml.png
```

## Backend

DRF CoreAPI docs: http://localhost:8000/coreapi/
Swagger docs: http://localhost:8000/swagger/
OpenAPI JSON: http://localhost:8000/swagger/?format=openapi
drf_docs docs: http://localhost:8000/drfdocs/
drf_openapi docs: http://localhost:8000/api/v1/schema/ (not yet working)
