#!/bin/bash

set -euo pipefail

python manage.py makemigrations --check --dry-run

python manage.py migrate
