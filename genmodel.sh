#!/bin/bash

python manage.py graph_models services | dot -Tpng -Gdpi=200 -o models.png /proc/self/fd/0