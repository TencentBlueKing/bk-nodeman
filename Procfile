web: gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile - --access-logformat '[%(h)s] %({request_id}i)s %(u)s %(t)s "%(r)s" %(s)s %(D)s %(b)s "%(f)s" "%(a)s"'
worker: python manage.py celery worker -P eventlet -c 100 -Q default
backend: python manage.py celery worker -P eventlet -c 100 -Q backend
beat: python manage.py celery beat -l info
pworker: python manage.py celery worker -P eventlet -c 100  -Q pipeline,pipeline_priority
pschedule: python manage.py celery worker -P eventlet -c 100  -Q service_schedule,service_schedule_priority
sworker: python manage.py celery worker -c 8  -Q saas