# Local Faces

The initial Local Faces Talent Agency & Entertainment website, built with Django and a custom editorial-style responsive homepage.

## Current stage

The site includes a responsive homepage, model applications, training information and a training cart. Merchandise details remain pending.

The model application collects details and photographs and uses a WhatsApp handoff. Other talent categories are not yet accepting applications. The old training application has been replaced by training details and the shop; existing application records remain available to staff. The 2027 training shop offers terms 1–4, a R3,000 group course and one-on-one training with Semu at R1,500 per hour, both in Durban, Johannesburg or Cape Town. The R500 non-refundable group-course registration fee is paid by EFT or bank deposit; the remaining R2,500 course fee is arranged separately with Local Faces. Actual dates and arrangements are confirmed separately.

People interested in starting an academy can contact Local Faces to enquire about their proposed city, availability and operating terms.

Each group-course and one-on-one booking requires an applicant form, sizes and two photographs before it can be added to the cart. The one-on-one form follows the talent-pool application, while the group form includes course availability questions. The R500 registration fee remains the only group-course amount due in the cart, and staff arrange and track the balance separately. Applications are stored when submitted, even if the cart is abandoned or the item is removed; staff can review them in Django admin. Existing training cart items without an application must be removed and added again.

On the training details pages, customers can expand a city to see fees and follow its purchase link to the training selection form with that city preselected. They can still change their city and select their training type and term before completing the applicant form.

## Application email notifications

New model and training applications are emailed to info@localfaces.com, including submitted details and training selection where applicable. Photographs are not attached: the email links to the staff-only Django admin application page, where an authorized staff member can review them. Applications are saved even when email delivery fails; the applicant is warned and staff can filter Application emails by pending or failed status, then select the related applications and use "Retry pending or failed application emails" in Django admin. A process interruption can leave a notification pending; check both pending and failed regularly. Acceptance by Resend does not guarantee final inbox delivery. A retry after an interrupted send may result in a duplicate email.

Application notifications use Resend's HTTPS API. Verify the `localfaces.co.za` sender domain in Resend by adding its required DNS records, create a sending API key, and set `RESEND_API_KEY` privately in the Render web service's environment. `DEFAULT_FROM_EMAIL` defaults to `info@localfaces.co.za`; change it only to an address on a verified Resend domain. The sender domain may differ from the recipient, info@localfaces.com. Never put API keys in source control or chat. Deploy and submit a test application, then confirm receipt at info@localfaces.com and check Resend's delivery logs. Without a configured API key or verified sender, email cannot be delivered; the application remains saved and staff must retry failed notifications manually. Resend's idempotency key reduces duplicate sends on retries within its 24-hour window.

## EFT payment

The cart is session-based and displays EFT or bank-deposit instructions directly; no new order is created or persisted. Customers use the applicant's name as the payment reference and email proof of payment to info@localfaces.co.za with the applicant's name. Staff must reconcile the deposit and booking details manually; an application or proof of payment alone does not confirm a deposit. Academy cart selections are not otherwise stored.

The group-course balance and any outstanding academy instalments from earlier arrangements must be collected and tracked separately. Existing orders retain their original amounts. Pending legacy PayFast orders direct customers to contact Local Faces before paying again. The existing PayFast notification endpoint and its `PAYFAST_MERCHANT_ID`, `PAYFAST_MERCHANT_KEY`, `PAYFAST_PASSPHRASE`, `PAYFAST_SITE_URL`, and `PAYFAST_SANDBOX` settings remain temporarily for verifying in-progress legacy payments only. Keep the existing deployment settings until those payments are reconciled.

## Run locally

Requires Python 3.12 or newer.

1. Create and activate a virtual environment.
2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Apply migrations and start the development server:

   ```powershell
   python manage.py migrate
   python manage.py runserver
   ```

4. Open `http://127.0.0.1:8000/`.

The local default is SQLite. For local work, Django uses a development-only fallback secret key; set `SECRET_KEY` to a private value for any shared or deployed environment.

## Deploy to Render

### Blueprint (recommended)

Push the repository to GitHub, then in Render choose **New → Blueprint** and select it. `render.yaml` provisions the web service and a PostgreSQL database, generates `SECRET_KEY`, wires `DATABASE_URL`, runs `build.sh` (install, `collectstatic`, `migrate`) and starts Gunicorn. `RENDER_EXTERNAL_HOSTNAME` is added to the allowed hosts and CSRF trusted origins automatically; add custom domains through `ALLOWED_HOSTS`. After the first deploy, create an admin user from the Render shell with `python manage.py createsuperuser`.

Free Render plans have an ephemeral disk and a short-lived database; upgrade before real use.

### Manual setup

Alternatively, create a Web Service and a PostgreSQL database by hand and set the following environment variables in the Render dashboard (the app refuses to start with `DEBUG=False` and no `SECRET_KEY`):

- `SECRET_KEY`: a long, unique secret value.
- `DEBUG`: `False`.
- `ALLOWED_HOSTS`: the Render hostname (and any custom domains), comma-separated.
- `DATABASE_URL`: the Render PostgreSQL connection string.
- `SECURE_SSL_REDIRECT`: `True` (the production default).

Use the following build command:

```text
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
```

Set the start command to `gunicorn localfaces.wsgi:application` (also defined in `Procfile`). Static files are served through WhiteNoise. Run migrations during deployment or as a Render pre-deploy command when available.

Applicant photos require durable private storage in production. The Render blueprint configures a persistent disk; other deployments must configure their own durable private storage, access controls and retention rules. Do not serve private applicant files as public static content.
