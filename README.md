# Local Faces Agency — 5-Week Summer Camp

A Django website and application system for the Local Faces Agency 5-Week Summer Camp. The public application form at `/` (also available at `/apply/`) saves applicant details and private photographs, then presents a confirmation page with an applicant-triggered WhatsApp handoff. A staff dashboard and Django Admin support application review.

## Run locally

Python 3.11+ is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

**Local start command:** `python manage.py runserver`

Open `http://127.0.0.1:8000/` for the application page. The confirmation appears only after submission. The private staff dashboard is at `/agency/applications/`; Django Admin is at `/django-admin/`. Only staff accounts can access either management area.

The default database is local SQLite. For PostgreSQL, set `DJANGO_DB_ENGINE=django.db.backends.postgresql` and supply `DJANGO_DB_NAME`, `DJANGO_DB_USER`, `DJANGO_DB_PASSWORD`, `DJANGO_DB_HOST` and `DJANGO_DB_PORT`.

## Applicant-triggered WhatsApp handoff

No WhatsApp API or messaging service is used. After Django successfully saves an application, the confirmation page offers a **Send application via WhatsApp** button. It opens a standard `wa.me` URL with a concise message already composed; the applicant reviews it and taps **Send** inside WhatsApp. The application remains saved if they do not send the message.

Set `LOCAL_FACES_WHATSAPP_NUMBER` to the agency's international number using digits only (no plus sign, spaces or punctuation). The default is `27671012841`. The message contains the application reference, key applicant details, a private photo-page link and a private full-application link. It omits the applicant's long personal statement.

Each application has a random UUID-based private link token. Anyone with the application or photo URL can view that applicant's submitted information, so treat the WhatsApp message as private. These bearer links do not expose sequential application IDs and do not expire. Configure the site's public HTTPS hostname correctly so generated links point to the deployed site.

## Applicant photographs and privacy

Uploaded images are validated as images and stored outside public static files in `private_uploads/`. The form requires a headshot and full-body photo and accepts one optional additional photo. Only JPG/JPEG and PNG are accepted. `MAX_APPLICATION_PHOTO_BYTES` sets the per-photo byte limit (default 8 MiB); `MAX_APPLICATION_PHOTOS` sets the total limit from 2 through 3. Public media serving is deliberately not enabled. The UUID-token photo and application pages are the only non-staff access path. Back up and restrict access to the database and private upload directory together.

Applicants enter their date of birth; age is calculated by the browser for display and independently calculated by Django when saving. The form also collects contact/WhatsApp numbers, current occupation, preferred time, five-week availability, experience, Instagram, and an optional personal statement. For applicants under 18, parent/guardian contact details and agreement are required. Confirm the programme's actual eligibility and consent requirements before accepting applications.

The submission includes a unique idempotency key, so a repeated POST with the same form does not create another application. The submit button is disabled while the first submission is processing.

## Editable programme details and imagery

The supplied `img/1.jpg` and `img/2.jpg` campaign posters are displayed on the application page. Eligibility, dates, venue and fee details should be confirmed before launch. Edit `templates/camp/apply.html` for application-page content.

## Deploy to Render

The included `render.yaml` Blueprint configures the Django web service, PostgreSQL, production static files, HTTPS settings, a health check and a persistent disk for private application photos. The web service and database use paid Render plans so applicant data and uploaded images persist. Review current Render pricing and region availability before creating the Blueprint.

1. Push this project to a GitHub or GitLab repository.
2. In the Render Dashboard, choose **New → Blueprint Instance**, select the repository and review the services and costs in `render.yaml`.
3. Apply the Blueprint. Render runs the build command, which installs dependencies, applies migrations and collects static files. Render then starts the app with Gunicorn.
4. Create an agency administrator from the Render Shell with `python manage.py createsuperuser`.
5. Set `LOCAL_FACES_WHATSAPP_NUMBER` to the agency number in international digits-only format.
6. Visit the `onrender.com` URL to check the site and `/django-admin/` to manage applications. Add any custom domain to `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` in the service environment.

**Render build command:** `bash build.sh`

**Render start command:** `gunicorn localfaces.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

For a local production-style build, run `python manage.py collectstatic --noinput`. `build.sh` is a Bash script for Render/Linux, not Windows PowerShell.

Render automatically configures `DATABASE_URL` for PostgreSQL and `DJANGO_MEDIA_ROOT` for the persistent upload disk. Do not remove that disk or serve applicant uploads from the public static directory. Back up the database and upload disk together.

## Production checklist

- Set `DJANGO_SECRET_KEY` to a unique secret and `DJANGO_DEBUG=False`.
- Set `DJANGO_ALLOWED_HOSTS` and configure HTTPS / trusted proxy settings for the hosting provider.
- Use managed PostgreSQL and private, access-controlled media storage with backups.
- Configure `LOCAL_FACES_WHATSAPP_NUMBER` and test the `wa.me` handoff against the live hostname. No API credentials are needed.
- Verify that `DATABASE_URL` uses PostgreSQL and `DJANGO_MEDIA_ROOT` points to persistent private storage.
- Run `python manage.py migrate` and `python manage.py collectstatic --noinput` as part of deployment.
- Establish the agency's privacy notice, consent wording, data-retention schedule and deletion process before collecting real applicants' information.

## Tests

```powershell
python manage.py test camp
```
