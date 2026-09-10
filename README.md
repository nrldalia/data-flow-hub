# 🚀 DataFlow Hub — AI Data Operations Suite (`v1.0.0`)

> **An end-to-end full-stack web application designed to automate unstructured retail data ingestion, data quality monitoring, and generative AI data cleansing.**

---

## 📌 Overview

Handling raw client payloads often means dealing with missing fields, messy whitespace, unstandardized dates, and inconsistent numbers. **DataFlow Hub** solves this by providing a unified workspace where data operators can upload unstructured datasets (`.csv` or `.json`), run automated Gemini AI transformations, inspect real-time audit trace logs, and export clean, standardized files.

---

## ✨ Features & Functionality

* 🤖 **AI-Driven Data Cleansing**: Uses Google Gemini AI to strip formatting errors, standardize date formats, and sanitize missing fields to standard `N/A` flags.
* 🔍 **Live Audit Trace & JSON Inspector**: View step-by-step transformation logs mapping exact field modifications alongside side-by-side raw vs. processed previews.
* 🏪 **Store Operations Dashboard**: Real-time multi-field search, status filtering (`Clean`, `Error`, `Pending`), and inline store record updates.
* ✉️ **Automated Compliance Emails**: One-click draft generator that creates client notification emails detailing missing payload fields.
* 📊 **Operations Hub Modules**: Integrated views detailing active data streams, quality validation rules, and system configuration settings.
* 📥 **Dynamic Dataset Export**: Export processed datasets back to `.csv` or `.json` streams instantly.

---

## 🛠️ Tech Stack

| Domain | Technology |
| :--- | :--- |
| **Frontend** | React, Vite, Tailwind CSS, Lucide React Icons |
| **Backend** | Python, Flask, Flask-CORS, Pandas |
| **AI & Storage** | Google Gemini API (`gemini-3.6-flash`), SQLite |

---

## ⚡ Quick Start & Setup

### Prerequisites
* Node.js (`v18+`) and `npm`
* Python (`v3.10+`)
* Google Gemini API Key

### 1. Backend Configuration
```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install flask flask-cors pandas google-genai

# Set your Gemini API Key (Windows CMD)
set GEMINI_API_KEY="your_api_key_here"

# Set your Gemini API Key (macOS/Linux)
# export GEMINI_API_KEY="your_api_key_here"

# Start Flask server (Runs on [http://127.0.0.1:5000](http://127.0.0.1:5000))
python app.py
