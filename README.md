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
