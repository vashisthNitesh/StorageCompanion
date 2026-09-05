# Deploying SpeedCloud on Render Free Tier (Automated Without Command Prompt)

On Render's Free Tier, there is **no SSH or interactive command prompt / shell**. Everything (database migrations, demo plan seeding, building the Vue 3 SPA, and binding to `$PORT`) must execute automatically through the build and startup entrypoint.

This repository is pre-configured to run automatically on Render with **zero manual CLI commands required**.

---

## Method 1: Docker Web Service (Recommended — Single Container)

Because SpeedCloud follows the single-server architecture (Nginx serving the pre-compiled Vue 3 SPA + reverse proxying `/api/` to Gunicorn on port `$PORT`), this Docker setup works completely out of the box.

### Step 1: Connect GitHub to Render
1. Log in to your [Render Dashboard](https://dashboard.render.com).
2. Click **New +** > **Web Service**.
3. Select **Build and deploy from a Git repository** and pick `StorageCompanion`.

### Step 2: Configure Service Settings
- **Name**: `speedcloud` (or your chosen name)
- **Region**: Oregon (or Frankfurt / Singapore)
- **Branch**: `main`
- **Runtime**: **Docker**
- **Plan Type**: **Free**

Render will automatically discover the root `Dockerfile` and `render-entrypoint.sh`.

### Step 3: Add Environment Variables
Under the **Environment Variables** section in Render, add:

| Key | Value | Notes |
|---|---|---|
| `ENVIRONMENT` | `prod` | Enables production security |
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` | |
| `SECRET_KEY` | *(Click "Generate")* | 64-char random string |
| `ALLOWED_HOSTS` | `.onrender.com,localhost,127.0.0.1` | Permits your `.onrender.com` domain |
| `CSRF_TRUSTED_ORIGINS` | `https://*.onrender.com` | Prevents CSRF errors |
| `PAYMENT_PROVIDER` | `razorpay` | Razorpay gateway |
| `DEFAULT_CURRENCY` | `INR` | Indian Rupees |
| `RAZORPAY_KEY_ID` | `rzp_test_sample` | Replace with live key when ready |
| `RAZORPAY_KEY_SECRET` | `sample_secret_key` | |
| `DATABASE_URL` | *(Optional)* | Link a free Render Postgres or Neon/Supabase URL |

> [!TIP]
> If you do not provide a `DATABASE_URL`, SpeedCloud will automatically fall back to an internal SQLite database (`db.sqlite3`) so your app boots up immediately without errors!

### Step 4: Click "Deploy Web Service"
What happens automatically:
1. **Stage 1**: Node builds the Vue 3 frontend (`dist/`).
2. **Stage 2**: Python 3.12 installs dependencies and prepares Nginx.
3. **Startup (`render-entrypoint.sh`)**:
   - `python manage.py migrate --noinput` runs automatically.
   - `python manage.py seed_demo` runs automatically (creating the ₹199/mo Personal & ₹499/mo Business plans and `demo@speedcloud.local` account).
   - Nginx binds to Render's dynamic `$PORT` (10000).
   - Gunicorn starts on `127.0.0.1:8000`.

Your site is immediately live at `https://<your-service-name>.onrender.com`!

---

## Method 2: Native Python Web Service (Alternative)

If you prefer not to use Docker, you can use Render's native Python runtime:

- **Runtime**: **Python 3**
- **Build Command**: `./render-build.sh`
- **Start Command**:
  ```bash
  sh -c "python backend/manage.py migrate --noinput && python backend/manage.py seed_demo && gunicorn --chdir backend config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 -k uvicorn.workers.UvicornWorker"
  ```

---

## Method 3: 1-Click Render Blueprint (`render.yaml`)

1. In Render Dashboard, click **New +** > **Blueprint**.
2. Select your repository `vashisthNitesh/StorageCompanion`.
3. Render reads `render.yaml` and provisions the Web Service automatically with all required settings!
