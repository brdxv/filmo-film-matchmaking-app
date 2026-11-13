# FILMO: Film Matchmaking App

A desktop social app that connects people through shared taste in movies and TV shows. Users build a profile around their **Top 4 Movies** and **Top 4 TV Shows**. FILMO calculates a match percentage from those picks and lets matched users chat, post, and review together.

> Final project for **CS Elective 2 (Python)**, BS Computer Science, University of Rizal System – Morong (May 2026).

## Features

- **Accounts & profiles:** registration, login (hashed passwords), editable profiles with bio, interests, and Top 4 Movies / Top 4 TV Shows pickers
- **People & matchmaking:** match percentage based on shared Top 4 titles (8 total), match requests, and a matches list
- **Chats:** messaging that unlocks only between matched users
- **Discover feed:** posts with local image/video attachments, likes, and comments
- **Reviews:** search and filter titles, with star ratings that support half stars
- **Instants:** short story-style posts with a dedicated viewer
- **Responsive UI:** sidebar layout on wide windows, mobile-style bottom navigation on narrow windows

## Tech Stack

| Layer | Technology |
|---|---|
| Desktop shell | Electron |
| UI | HTML, CSS, JavaScript |
| Backend API | Python, Flask, Flask-CORS |
| Database | SQLite |
| Security | Werkzeug password hashing |

## Architecture

```text
Electron (electron-main.js, preload.js)
   └─ loads frontend/ (index.html, renderer.js, styles.css)
         └─ HTTP → Flask API (backend/app.py)
                     └─ SQLite (backend/data/filmo.db)
```

## Running Locally

Requirements: Node.js 18+ and Python 3.10+.

```bash
cd backend
py -m pip install -r requirements.txt
cd ..
npm install
npm start
```

On Windows you can also run `run_windows.bat`.

Sample accounts (password `password`): `ian`, `mika`, `leo`, `ara`.

## Media Assets

Movie posters, TV show art, film clips, and sample profile/feed media are **not included** in this repository for copyright reasons. Place your own files in `backend/static/Resources/` using the paths listed in [`RESOURCE_PATHS.md`](RESOURCE_PATHS.md). The app still runs without them; images just won't show.

See [`CHANGELOG.md`](CHANGELOG.md) for the list of revisions.

## Author

**Ian Kurt G. Valencia**, BS Computer Science, University of Rizal System – Morong
