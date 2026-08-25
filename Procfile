web: gunicorn -w 1 --bind 0.0.0.0:$PORT wsgi:application
release: python init_db.py && python init_helios_db.py
