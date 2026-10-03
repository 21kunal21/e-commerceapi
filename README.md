E-Commerce API

Backend e-commerce API built with Django REST Framework.

Features
JWT authentication
Products and categories
Cart and checkout
Orders and payments
Inventory management
Seller dashboard
Redis caching
Celery background tasks and email notifications
Automated tests
Swagger/OpenAPI documentation
Docker + PostgreSQL
Tech Stack

Python, Django, DRF, PostgreSQL, Redis, Celery, Docker.

Run
docker compose up --build

API: http://localhost:8000/

Swagger: http://localhost:8000/api/docs/

Tests
docker compose exec web python manage.py test