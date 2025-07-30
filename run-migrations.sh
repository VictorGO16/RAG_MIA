# Clean previous data
rm -rf db.sqlite3

# Source env variables
source .env

# Make migrations
python manage.py makemigrations
python manage.py migrate

# Load initial data
python manage.py loaddata profiles/fixtures/initial_data.json

# Create superuser
python manage.py createsuperuser --noinput --username admin --email admin@localhost


