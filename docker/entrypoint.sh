#!/bin/bash
# stop script if error
set -e

# wait for database to be ready
if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for PostgreSQL..."
    while ! nc -z ${POSTGRES_HOST:-db} ${POSTGRES_PORT:-5432}; do
    sleep 1
    done
    echo "PostgreSQL started"
fi

# run migration and collectstatic
python manage.py migrate --noinput
# python manage.py collectstatic --noinput

# check environment to decide command to run
if [ "$DEBUG" = "True" ] || [ "$DEBUG" = "1" ]; then
    echo "Running in DEVELOPMENT mode"
    # collect static files for dev mode (if needed)
    # python manage.py collectstatic --noinput
    # run runserver default command of Django
    exec python manage.py runserver 0.0.0.0:8000
else
    echo "Running in PRODUCTION mode"
    # collect static files (required for Production)
    python manage.py collectstatic --noinput
    # run Gunicorn (replace 'config' with the name of the directory containing wsgi.py)
    exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
fi
