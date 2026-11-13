# FILMO Electron + Python Revised Version

This revised build keeps the Electron + Python architecture, but improves the layout and feature behavior.

## Major Updates

- Fully responsive layout with mobile-style bottom navigation at small window widths
- Reduced Electron minimum window size
- Clickable profile icon opens the Profile page
- Profile page now shows the user’s own posts and reviews at the bottom
- Post and review counts scroll to the Profile Activity section
- Edit Profile includes Top 4 Movies and Top 4 TV Shows search/edit tools
- Discover supports attaching local image/video files
- Posts no longer auto-attach an unrelated sample image
- Like and comment actions update without jumping back to the top
- Media is displayed naturally instead of being aggressively cropped
- People page calculates match percentage from shared Top 4 Movies + Top 4 TV Shows IDs over 8 total titles
- Chats page shows matched users only
- Instants now have a separate viewer inspired by the provided UI guide
- New Instants resource folder: `Resources/Images/Instants/` and `Resources/Videos/Instants/`
- Reviews page uses search + filter instead of dropdown selection
- Reviews page supports clickable star rating with half-star support by double-clicking a star

## How to Run

Open this folder in PowerShell or VS Code terminal.

```bash
cd backend
py -m pip install -r requirements.txt
cd ..
npm install
npm start
```

If packages are already installed, run only:

```bash
npm start
```

## Sample Accounts

```text
ian / password
mika / password
leo / password
ara / password
```

## Resource Paths

The database still stores paths like:

```text
Resources/Images/Profiles/ian_pfp.png
Resources/Images/Movies/Past_Lives.png
Resources/Images/TV_Shows/Breaking_Bad.png
Resources/Images/Instants/ian_instant1.png
```

The actual files are served from:

```text
backend/static/Resources/
```

## Resetting the database

If you want a clean reset, stop the app, delete:

```text
backend/data/filmo.db
```

Then run:

```bash
npm start
```

The backend will recreate the demo data.


## Final Revision Notes

- Profile page now allows uploading a new profile photo from local files.
- Instants are now 100% opacity.
- Instants advance by clicking the instant photo/card instead of swiping.
- Instant cards animate away randomly to the sides or with a spin.
- Chat message input is raised on mobile sizes so the bottom navigation does not cover it.


## Upload Fix

This package fixes the profile photo upload error where the frontend showed:

```text
Unexpected token '<', "<!doctype"... is not valid JSON
```

The backend profile-photo upload route now returns JSON errors instead of an HTML error page.


## Refined Registration/Profile Revision

- Account creation now asks only for username and password.
- Profile photo upload during account creation is optional.
- New users can complete bio, location, taste summary, looking for, talk about, and hobbies after logging in through Profile > Edit Profile.
- Profile photo change now saves uploaded images into `Resources/Images/Profiles/` and updates the user record in the database.
- Instants fallback media now uses `Resources/Images/Instants/default_instant.png` instead of feed images.
- Android-style back/forward buttons no longer invert yellow icons into blue.
- Removed the inner icon button circle background from the back/forward buttons.

## Latest Requested Refinements

- Create Account now shows only username, password, confirm password, and optional profile photo.
- Profile icon menu now includes Account Settings for username/password changes.
- Added requested movies and TV shows into the bundled database and backend seed logic.
- Added sample users that use the newly added movies and shows in their Top 4 selections.


## Final Working Revision

This build fixes the create-account photo upload issue by changing the backend `/api/register` route to accept multipart form data instead of forcing `request.json`.

Final fixes included:
- Create Account supports username, password, confirm password, and optional profile photo upload.
- Uploaded profile photos are saved under `backend/static/Resources/Images/Profiles/`.
- Uploaded profile photos are renamed based on username, for example `mark_pfp.jpg`.
- Only `.png`, `.jpg`, and `.jpeg` are accepted for profile photo uploads.
- Profile page Change Profile Photo now uses the same upload logic.
- Top 4 editing now preserves poster images when removing one of the selected titles.
- Search now uses contains matching, so titles like `God's Own Country` can be found more easily.
- `Severance` and `God's Own Country` are confirmed in the bundled database.
- Added a pending like/request for Ian and sample messages from Mika.
