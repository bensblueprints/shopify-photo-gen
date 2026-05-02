# Shopify Product Photo Generator

A web app that batch-processes your product images through the **xAI Grok Image API** to generate polished, Shopify-ready product photos. Upload your raw images, describe the style you want, and download a neatly named ZIP file with professional results.

---

## What It Does

- **Batch Upload** — Drag & drop multiple product images at once
- **AI Style Transfer / Editing** — Uses `grok-imagine-image` to transform photos based on your prompt
- **Smart File Naming** — Automatically generates Shopify-friendly filenames like `my-product_studio-white_20250115.png`
- **ZIP Download** — Packages everything into a single ZIP for easy Shopify bulk upload
- **Aspect Ratio & Resolution Control** — Choose output formats (1:1, 4:3, 16:9, 2K, etc.)

---

## Tech Stack

- **Backend**: Python / Flask
- **Frontend**: Vanilla JS + modern CSS (no build step)
- **AI Provider**: [xAI API](https://x.ai/api) (`grok-imagine-image`)
- **Deployment**: Docker + Coolify

---

## Quick Start (Local)

```bash
# 1. Clone / navigate to the project
cd shopify-product-photo-gen

# 2. Set up environment
cp .env.example .env
# Edit .env and add your XAI_API_KEY

# 3. Run with Docker Compose
docker-compose up --build

# 4. Open http://localhost:5000
```

---

## GitHub Setup

1. **Create a new repo** on GitHub (e.g. `shopify-photo-gen`)
2. **Push this code**:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/shopify-photo-gen.git
git push -u origin main
```

---

## Deploy to Coolify

Coolify is a self-hostable PaaS that deploys Docker apps from Git repos. This project is already configured for it.

### Step 1: Add Your GitHub Repo to Coolify
1. Open your Coolify dashboard
2. Go to **Projects** → Create or select a project
3. Click **Add Resource** → **Application**
4. Choose **GitHub** and select your `shopify-photo-gen` repo
5. Pick the `main` branch

### Step 2: Configure Build
Coolify auto-detects the `Dockerfile` and `docker-compose.yml`. Use **Docker Compose** deployment or **Dockerfile** build — both work.

### Step 3: Set Environment Variables
In Coolify, go to the **Environment** tab and add:

| Key | Value | Required |
|-----|-------|----------|
| `XAI_API_KEY` | Your xAI API key | ✅ Yes |
| `PORT` | `5000` | Optional |

> Get your xAI API key at [https://x.ai/api](https://x.ai/api)

### Step 4: Deploy
Click **Deploy** (or enable auto-deploy on push). Coolify will build and host your app.

### Step 5: Domain / SSL
- In Coolify, map a domain to your app
- Enable HTTPS / Let's Encrypt if desired
- Share the URL with your team or bookmark it for daily use

---

## Usage Guide

1. **Open the app** in your browser
2. **Upload images** — drag & drop or click the upload zone
3. **Write a prompt** describing the look you want, or click a preset:
   - *Studio White* — clean white background, catalog style
   - *Lifestyle* — modern interior, natural daylight
   - *Luxury Dark* — dramatic gradient background, premium feel
   - *Flat Lay* — top-down on marble, Pinterest aesthetic
4. **Pick aspect ratio & resolution** (optional)
5. Click **Generate Product Photos**
6. Wait for processing (each image takes ~5–15s)
7. **Preview & download** individual images or the full ZIP
8. **Upload to Shopify** — go to Shopify Admin → Products → Media → Add images

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Web UI |
| `POST` | `/api/process` | Upload images + prompt, returns job info |
| `GET` | `/api/download/<job_id>` | Download the ZIP of all generated images |
| `GET` | `/api/download-single/<job_id>/<filename>` | Download one image |
| `GET` | `/api/preview/<job_id>` | Get base64 previews for the gallery |

---

## Smart Naming Logic

Filenames are generated automatically from:
- Original file name (sanitized)
- Style keywords extracted from your prompt
- Date stamp

Example:
```
Original:  IMG_4382.jpg
Prompt:    "Professional studio product photo with clean white background..."
Output:    img-4382_studio-white_20250502.png
```

---

## Folder Structure

```
shopify-product-photo-gen/
├── app.py                 # Flask backend
├── requirements.txt       # Python deps
├── Dockerfile             # Container build
├── docker-compose.yml     # Local / Coolify compose
├── .env.example           # Env template
├── templates/
│   └── index.html         # Web UI
├── static/
│   ├── css/style.css      # Styles
│   └── js/app.js          # Frontend logic
└── README.md
```

---

## Important Notes

- **xAI API costs**: Image editing/generation is billed per image. Check [xAI pricing](https://x.ai/api) for current rates.
- **URL expiration**: Generated image URLs from xAI are temporary. The app downloads them immediately so you don't lose them.
- **File limits**: Up to 50MB per upload, 500MB total per batch (configurable in `app.py`).
- **Concurrent processing**: The app processes images sequentially to respect API rate limits. For large batches, go make a coffee.

---

## License

MIT — use it, fork it, deploy it for your store.
