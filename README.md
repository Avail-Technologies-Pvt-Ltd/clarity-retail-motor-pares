# Clarity Retail POS — with ZIMRA FDMS Fiscalisation

Django-based point-of-sale system with integrated ZIMRA fiscalisation (open day, sign + submit receipts, close day) for Zimbabwean tax compliance.

End-to-end validated against the ZIMRA test environment: `https://fdmsapitest.zimra.co.zw`.

---

## Architecture & Deployment Overview

Clarity POS is packaged as a production-ready containerized solution using Docker and Docker Compose, supported by an automated GitHub Actions CI/CD pipeline and one-click update automation for Windows client machines.

```mermaid
flowchart TD
    subgraph Developer Machine
        Dev["Developer Code Changes"] --> Push["Double-Click push.bat"]
    end

    subgraph GitHub & CI/CD
        Push --> GitMaster["Git Push origin master"]
        GitMaster --> GHActions["GitHub Actions (build-and-push.yml)"]
        GHActions --> DockerHub["Docker Hub (tinashemp/clarity-pos:latest)"]
    end

    subgraph Client / Store Server (C:\avail\pos-app)
        DockerHub --> UpdateBat["Double-Click update.bat"]
        UpdateBat --> Pull["docker pull & compose up -d"]
        Pull --> DB["PostgreSQL 13 (pos-postgres)"]
        Pull --> Web["Gunicorn Django (pos-app)"]
        Web --> Port["Access via http://localhost:8085"]
    end
```

---

## 🚀 One-Step Push to GitHub (Developer Machine)

To stage, commit, and push changes to GitHub and trigger an automated Docker image build:

Double-click `push.bat` (or execute in PowerShell/CMD):
```cmd
push.bat "Your commit message here"
```
If you omit the message and simply press **Enter**, it automatically creates a timestamped commit (e.g. `Update: 2026-09-23 14:30`).

### What `push.bat` does:
1. Detects the active branch (`master`).
2. Stages modified files respecting `.gitignore` and `.dockerignore`.
3. Commits and pushes to `origin master`.
4. Triggers the GitHub Actions workflow at `https://github.com/Recusants/CLARITY-POS/actions`.
5. GitHub Actions builds the Docker image and publishes it to `tinashemp/clarity-pos:latest`.

---

## ⚡ One-Click Docker Deployment (`update.bat`)

To update or deploy the application in Docker on the local machine or target store server:

Double-click `update.bat`:
```cmd
update.bat
```

### What `update.bat` does:
1. **Detects application directory**: Checks `C:\avail\pos-app` or the current directory automatically.
2. **Validates Docker**: Ensures Docker Desktop is running before proceeding.
3. **Pulls the latest image**: Downloads `tinashemp/clarity-pos:latest` from Docker Hub.
4. **Applies updates**: Recreates the application container with `docker-compose.prod.yml` (PostgreSQL stays running without downtime).
5. **Database migrations**: Verifies and runs `python manage.py migrate --noinput`.
6. **Static files**: Runs `python manage.py collectstatic --noinput`.
7. **Housekeeping**: Prunes obsolete `<none>` images to conserve disk space.
8. **Summary**: Displays live status and connection URL (`http://localhost:8085`).

---

## 💻 Deploying on a New Client Machine (`C:\avail\pos-app`)

On the client machine (POS terminal or in-store server), **you do NOT need Python, Git, or source code installed**.

### 1. Prerequisites on Client Machine
- Install **[Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)** (WSL2 backend enabled).
- Start Docker Desktop and ensure the engine status is **Running**.
- *(If the Docker Hub image is private)*: Run `docker login` once in PowerShell.

### 2. Prepare the Client Package (on Dev Machine)
Run:
```cmd
deploy\package-for-client.bat
```
This automatically produces a lightweight zip file:
📁 **`deploy\ClarityPOS_Client_Deployment.zip`**

### 3. Install on Client Machine
1. Copy `ClarityPOS_Client_Deployment.zip` to the client machine.
2. Extract the archive into:
   ```text
   C:\avail\pos-app
   ```
3. Open `C:\avail\pos-app\.env` in Notepad and configure:
   - `SECRET_KEY` (set a secure random string)
   - `DB_PASSWORD` (set your database password)
   - ZIMRA fiscal device credentials (if applicable)
4. Double-click **`update.bat`**.
5. Once complete, access Clarity POS in the browser at:
   ```text
   http://localhost:8085
   ```
   *(Or double-click `Open Clarity POS.bat`)*.

### 4. Updating in the Future
Whenever an update is pushed, simply double-click `update.bat` in `C:\avail\pos-app`. The system updates in place with zero database data loss.

---

## ⚙️ Environment Configuration (`.env`)

A template is provided in `.env.example`. Copy it to `.env`:

```ini
# Django Security
SECRET_KEY=your-django-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,host.docker.internal

# PostgreSQL Database
DB_NAME=clarity_pos
DB_USER=pos_user
DB_PASSWORD=your_secure_db_password
DB_HOST=db
DB_PORT=5432

# Docker Registry
DOCKER_REGISTRY=tinashemp
TAG=latest

# ZIMRA Fiscalisation (Optional)
ZIMRA_DEVICE_ID=
ZIMRA_SERIAL_NO=
ZIMRA_ACTIVATION_KEY=
ZIMRA_TEST_MODE=True
ZIMRA_COMPANY_NAME=
ZIMRA_MODEL_NAME=Server
ZIMRA_MODEL_VERSION=v1
```

---

## 🔒 GitHub Actions Secrets Setup

To enable automated Docker image builds on GitHub, ensure the following repository secrets are configured at `https://github.com/Recusants/CLARITY-POS/settings/secrets/actions`:

| Secret Name | Description | Example |
|---|---|---|
| `DOCKER_USERNAME` | Docker Hub username | `tinashemp` |
| `DOCKER_TOKEN` | Docker Hub Personal Access Token | `dckr_pat_...` |

---

## 🛠️ Local Development Setup (Without Docker, ~5 mins)

If you prefer to run the raw Python Django development server:

```bash
# 1. Clone repository
git clone https://github.com/Recusants/CLARITY-POS.git
cd CLARITY-POS

# 2. Virtual environment
python -m venv venv
venv\Scripts\activate       # Linux/Mac: source venv/bin/activate

# 3. Install requirements
pip install -r requirements.txt

# 4. Migrate (SQLite for dev)
python manage.py migrate --settings=point_of_sale.settings_dev

# 5. Start development server
python manage.py runserver --settings=point_of_sale.settings_dev
```

Open `http://localhost:8000/fiscalisation/devices/` to access the setup interface.

---

## 🧾 First-Time ZIMRA Device Setup (Web UI)

The system is designed so an administrator or reseller can add a new ZIMRA device through the web UI without touching code:

1. Browse to `/fiscalisation/devices/` → click **+ Add Device**
2. Fill the form with credentials issued by ZIMRA:
   - `device_id` (e.g. `35454`)
   - `serial_no` (e.g. `testserial2`)
   - `activation_key` — pad to 8 digits (e.g. `82671` → `00082671`)
   - `company_name`
   - `is_test_mode` — check for ZIMRA test, uncheck for production
3. **Install certificate** — choose one option on the device detail page:
   - **Generate CSR + Fetch Cert** — generates a fresh RSA-2048 keypair, sends the CSR to ZIMRA, saves the issued certificate. Requires internet + valid activation key.
   - **Upload existing cert + key** — for a device already registered; upload matching `.crt` and `.key` PEM files.
4. Click **Test connection** to confirm `ping`, `getStatus`, and `getConfig`.
5. Click **Set as Active Device** — the running application immediately uses this device for receipts. No restart needed.

---

## 📊 Operational Dashboard

The dashboard at `/fiscalisation/dashboard/` is the operator's control panel (auto-refreshes every 15 seconds):

- **Active device card** — ID, serial, company, environment, certificate expiry days remaining.
- **Current fiscal day card** — day number, status (open/closed), opened-at, hours open vs cap, receipt counters.
- **Receipt counters** — Total, Synced (SUCCESS), Pending, Failed.
- **Failed Receipts list** — rejected receipts with RCPTxxx validation codes and plain-English explanations.
- **Pending Receipts list** — signed receipts queued for submission once network returns.
- **Recent receipts** — sync status badges and clickable ZIMRA verification QR links.
- **Closed-day summaries** — historical day-close records.

### Pause Fiscalisation (Emergency Trading)
If ZIMRA is unreachable, the certificate is expired, or maintenance is needed:
1. Click **Pause Fiscalisation** on the dashboard.
2. Select a reason and add optional notes.
3. While paused, sales and payments are recorded to the local database, but no ZIMRA receipt is issued.
4. Click **Resume Fiscalisation** when ready to resume normal operations.

---

## 🔧 Useful Operational Commands

```cmd
# Check container status
docker compose -f docker-compose.prod.yml ps

# View live container logs
docker logs -f pos-app

# View database logs
docker logs -f pos-postgres

# Restart containers
docker compose -f docker-compose.prod.yml restart

# Stop containers
docker compose -f docker-compose.prod.yml down
```

---

## 📁 Repository Structure

```text
├── .github/workflows/         # CI/CD workflows (build-and-push.yml, ci.yml)
├── deploy/                    # Deployment scripts & packaging utilities
│   ├── package-for-client.bat # Creates client deployment zip archive
│   ├── windows-update.bat     # Windows update launcher
│   └── windows-update.ps1     # Core PowerShell deployment engine
├── enventory/                 # Products, stock, and inventory batches
├── fiscalisation/             # ZIMRA FDMS integration, scheduler, and dashboard
├── order/                     # Order processing
├── payments/                  # Sales, transactions, and fiscal receipt tracking
├── point_of_sale/             # Django settings (dev, prod, docker)
├── pos/                       # Cashier till, cart, and receipt printing
├── Dockerfile                 # Multi-stage production container build
├── docker-compose.prod.yml    # Production compose configuration (Web + PostgreSQL)
├── push.bat                   # 1-step git push & auto Docker Hub build
├── update.bat                 # 1-click Docker deployment script
└── requirements-docker.txt    # Production Python dependencies
```
