from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from pathlib import Path
import sqlite3, uuid, re, traceback
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "filmo.db"
STATIC_DIR = BASE_DIR / "static"
app = Flask(__name__, static_folder=str(STATIC_DIR))
CORS(app)

def now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row; return con
def one(r): return dict(r) if r else None
def many(rows): return [dict(r) for r in rows]
def ensure_col(con, table, col, spec):
    cols = [r['name'] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
    if col not in cols: con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {spec}")
def add_asset(con, typ, cat, fp, alt='', owner_type=None, owner_id=None):
    key = f"{cat}_{uuid.uuid4().hex[:12]}"
    con.execute("""INSERT INTO resource_assets(asset_key,asset_type,category,file_path,alt_text,owner_type,owner_id,created_at)
                   VALUES(?,?,?,?,?,?,?,?)""", (key,typ,cat,fp,alt,owner_type,owner_id,now()))
    return con.execute("SELECT id FROM resource_assets WHERE asset_key=?",(key,)).fetchone()['id']


def safe_name_for_file(value):
    safe = secure_filename((value or "").strip().lower().replace(" ", "_"))
    safe = safe.replace("-", "_")
    safe = re.sub(r"[^a-zA-Z0-9_]+", "", safe)
    return safe or "user"

def save_profile_photo_file(file, user_id, username=None):
    filename = secure_filename(file.filename or "")
    ext = Path(filename).suffix.lower()
    if ext not in [".png", ".jpg", ".jpeg"]:
        raise ValueError("Please upload a PNG, JPG, or JPEG image only.")
    new_name = f"{safe_name_for_file(username or f'user_{user_id}')}_pfp{ext}"
    save_dir = STATIC_DIR / "Resources" / "Images" / "Profiles"
    save_dir.mkdir(parents=True, exist_ok=True)
    file.save(save_dir / new_name)
    return f"Resources/Images/Profiles/{new_name}", filename

def save_upload(file, category):
    filename = secure_filename(file.filename or '')
    ext = Path(filename).suffix.lower()
    is_video = ext in ['.mp4','.mov','.webm','.avi','.mkv']
    if category == 'instant': folder = 'Videos/Instants' if is_video else 'Images/Instants'; cat='instant'
    else: folder = 'Videos/Feed' if is_video else 'Images/Feed'; cat='feed'
    new_name = f"{category}_{uuid.uuid4().hex[:10]}{ext or ('.mp4' if is_video else '.png')}"
    save_dir = STATIC_DIR / 'Resources' / folder; save_dir.mkdir(parents=True, exist_ok=True)
    file.save(save_dir / new_name)
    return f"Resources/{folder}/{new_name}", ('video' if is_video else 'image'), cat

def init_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS resource_assets(id INTEGER PRIMARY KEY AUTOINCREMENT,asset_key TEXT UNIQUE NOT NULL,asset_type TEXT NOT NULL,category TEXT NOT NULL,file_path TEXT NOT NULL,alt_text TEXT,owner_type TEXT,owner_id INTEGER,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,display_name TEXT NOT NULL,bio TEXT DEFAULT '',location TEXT DEFAULT '',taste_summary TEXT DEFAULT '',looking_for TEXT DEFAULT '',hobbies TEXT DEFAULT '',talk_about TEXT DEFAULT '',profile_asset_id INTEGER,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS media_movies(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,original_title TEXT,release_year INTEGER,runtime_minutes INTEGER,genres TEXT,country TEXT,language TEXT,overview TEXT,poster_asset_id INTEGER,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS media_tv_shows(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,original_title TEXT,first_air_year INTEGER,last_air_year INTEGER,number_of_seasons INTEGER,number_of_episodes INTEGER,episode_runtime_minutes INTEGER,genres TEXT,country TEXT,language TEXT,overview TEXT,poster_asset_id INTEGER,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS user_top_movies(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,movie_id INTEGER NOT NULL,ranking INTEGER NOT NULL,created_at TEXT NOT NULL,UNIQUE(user_id,ranking));
        CREATE TABLE IF NOT EXISTS user_top_tv_shows(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,tv_show_id INTEGER NOT NULL,ranking INTEGER NOT NULL,created_at TEXT NOT NULL,UNIQUE(user_id,ranking));
        CREATE TABLE IF NOT EXISTS posts(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,content TEXT NOT NULL,media_asset_id INTEGER,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS post_likes(id INTEGER PRIMARY KEY AUTOINCREMENT,post_id INTEGER NOT NULL,user_id INTEGER NOT NULL,created_at TEXT NOT NULL,UNIQUE(post_id,user_id));
        CREATE TABLE IF NOT EXISTS comments(id INTEGER PRIMARY KEY AUTOINCREMENT,post_id INTEGER NOT NULL,user_id INTEGER NOT NULL,comment_text TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS match_requests(id INTEGER PRIMARY KEY AUTOINCREMENT,sender_id INTEGER NOT NULL,receiver_id INTEGER NOT NULL,message TEXT DEFAULT '',status TEXT DEFAULT 'pending',created_at TEXT NOT NULL,UNIQUE(sender_id,receiver_id));
        CREATE TABLE IF NOT EXISTS matches(id INTEGER PRIMARY KEY AUTOINCREMENT,user1_id INTEGER NOT NULL,user2_id INTEGER NOT NULL,created_at TEXT NOT NULL,UNIQUE(user1_id,user2_id));
        CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id INTEGER NOT NULL,sender_id INTEGER NOT NULL,message_text TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,target_type TEXT NOT NULL,movie_id INTEGER,tv_show_id INTEGER,rating REAL NOT NULL,review_text TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS review_likes(id INTEGER PRIMARY KEY AUTOINCREMENT,review_id INTEGER NOT NULL,user_id INTEGER NOT NULL,created_at TEXT NOT NULL,UNIQUE(review_id,user_id));
        CREATE TABLE IF NOT EXISTS review_comments(id INTEGER PRIMARY KEY AUTOINCREMENT,review_id INTEGER NOT NULL,user_id INTEGER NOT NULL,comment_text TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS stories(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,story_type TEXT DEFAULT 'image',content TEXT DEFAULT '',media_asset_id INTEGER,expires_at TEXT NOT NULL,created_at TEXT NOT NULL);
        """)
        ensure_col(con,'stories','receiver_id','INTEGER')
        ensure_col(con,'stories','is_instant','INTEGER DEFAULT 1')
        ensure_col(con,'stories','archived','INTEGER DEFAULT 0')
        ensure_col(con,'resource_assets','owner_type','TEXT')
        ensure_col(con,'resource_assets','owner_id','INTEGER')
        ensure_col(con,'media_movies','director','TEXT')
        ensure_col(con,'media_movies','cast','TEXT')
        ensure_col(con,'media_tv_shows','creator','TEXT')
        ensure_col(con,'media_tv_shows','cast','TEXT')
        con.executescript('''
        CREATE TABLE IF NOT EXISTS instant_reactions(id INTEGER PRIMARY KEY AUTOINCREMENT,story_id INTEGER NOT NULL,user_id INTEGER NOT NULL,reaction TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS instant_replies(id INTEGER PRIMARY KEY AUTOINCREMENT,story_id INTEGER NOT NULL,sender_id INTEGER NOT NULL,reply_text TEXT NOT NULL,created_at TEXT NOT NULL);
        ''')
        seed_demo(con)

def asset(con,key,typ,cat,fp,alt):
    con.execute("INSERT OR IGNORE INTO resource_assets(asset_key,asset_type,category,file_path,alt_text,created_at) VALUES(?,?,?,?,?,?)",(key,typ,cat,fp,alt,now()))
    return con.execute("SELECT id FROM resource_assets WHERE asset_key=?",(key,)).fetchone()['id']

def seed_demo(con):
    asset(con,'loginpage_main','image','profile','Resources/Images/Profiles/loginpage_main.png','login page main')
    for key,fp in {
        'eye_icon':'Resources/Images/Icons/eye_icon.png','eye_off_icon':'Resources/Images/Icons/eye_off_icon.png','heart_icon':'Resources/Images/Icons/heart_icon.png','x_icon':'Resources/Images/Icons/x_icon.png','send_icon':'Resources/Images/Icons/send_icon.png','sent_icon':'Resources/Images/Icons/sent_icon.png','back_icon':'Resources/Images/Icons/back_icon.png','forward_icon':'Resources/Images/Icons/forward_icon.png','play_icon':'Resources/Images/Icons/play_icon.png','rewind_icon':'Resources/Images/Icons/rewind_icon.png','forward5_icon':'Resources/Images/Icons/forward5_icon.png'
    }.items(): asset(con,key,'image','icon',fp,key)
    for key,fp in {'heart_emoji':'Resources/Images/Emojis/heart_emoji.png','laugh_emoji':'Resources/Images/Emojis/laugh_emoji.png','vomit_emoji':'Resources/Images/Emojis/vomit_emoji.png','fire_emoji':'Resources/Images/Emojis/fire_emoji.png','plus_emoji':'Resources/Images/Emojis/plus_emoji.png'}.items(): asset(con,key,'image','emoji',fp,key)
    # Fill movie/TV extra details for existing DBs
    for title,director,cast in [
        ('Past Lives','Celine Song','Greta Lee, Teo Yoo, John Magaro'),('Aftersun','Charlotte Wells','Paul Mescal, Frankie Corio'),('Before Sunrise','Richard Linklater','Ethan Hawke, Julie Delpy'),('Her','Spike Jonze','Joaquin Phoenix, Scarlett Johansson, Amy Adams'),('Interstellar','Christopher Nolan','Matthew McConaughey, Anne Hathaway'),('Arrival','Denis Villeneuve','Amy Adams, Jeremy Renner'),('Se7en','David Fincher','Brad Pitt, Morgan Freeman'),('Inception','Christopher Nolan','Leonardo DiCaprio, Joseph Gordon-Levitt'),('Spirited Away','Hayao Miyazaki','Rumi Hiiragi, Miyu Irino'),('Lady Bird','Greta Gerwig','Saoirse Ronan, Laurie Metcalf'),('Portrait of a Lady on Fire','Céline Sciamma','Noémie Merlant, Adèle Haenel'),('Cleaners','Glenn Barit','Ianna Taguinod, Leomar Baloran')]:
        con.execute('UPDATE media_movies SET director=?, cast=? WHERE title=?',(director,cast,title))
    for title,creator,cast in [('Normal People','Sally Rooney, Alice Birch, Mark O\'Rowe','Daisy Edgar-Jones, Paul Mescal'),('Fleabag','Phoebe Waller-Bridge','Phoebe Waller-Bridge, Sian Clifford'),('The Bear','Christopher Storer','Jeremy Allen White, Ayo Edebiri'),('Breaking Bad','Vince Gilligan','Bryan Cranston, Aaron Paul'),('Better Call Saul','Vince Gilligan, Peter Gould','Bob Odenkirk, Rhea Seehorn'),('Dark','Baran bo Odar, Jantje Friese','Louis Hofmann, Lisa Vicari'),('The Last of Us','Craig Mazin, Neil Druckmann','Pedro Pascal, Bella Ramsey'),('Stranger Things','The Duffer Brothers','Millie Bobby Brown, Finn Wolfhard'),('Avatar: The Last Airbender','Michael Dante DiMartino, Bryan Konietzko','Zach Tyler Eisen, Mae Whitman'),('The Office','Greg Daniels','Steve Carell, Rainn Wilson')]:
        con.execute('UPDATE media_tv_shows SET creator=?, cast=? WHERE title=?',(creator,cast,title))
    if con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        pa={n:asset(con,f'profile_{n}','image','profile',f'Resources/Images/Profiles/{n}_pfp.png',f'{n} profile') for n in ['ian','mika','leo','ara']}
        fa={n:asset(con,f'feed_{n}_img1','image','feed',f'Resources/Images/Feed/{n}_feed_img1.png',f'{n} feed') for n in ['ian','mika','leo','ara']}
        ia={n:asset(con,f'instant_{n}_1','image','instant',f'Resources/Images/Instants/{n}_instant1.png',f'{n} instant') for n in ['ian','mika','leo','ara']}
        ma={}
        for t,fn in {'Past Lives':'Past_Lives.png','Aftersun':'Aftersun.png','Before Sunrise':'Before_Sunrise.png','Her':'Her.png','Interstellar':'Interstellar.png','Arrival':'Arrival.png','Se7en':'Se7en.png','Inception':'Inception.png','Spirited Away':'Spirited_Away.png','Lady Bird':'Lady_Bird.png','Portrait of a Lady on Fire':'Portrait_of_a_Lady_on_Fire.png','Cleaners':'Cleaners.png'}.items():
            ma[t]=asset(con,'movie_'+fn.lower().replace('.png',''),'image','movie_poster',f'Resources/Images/Movies/{fn}',t)
        ta={}
        for t,fn in {'Normal People':'Normal_People.png','Fleabag':'Fleabag.png','The Bear':'The_Bear.png','Breaking Bad':'Breaking_Bad.png','Better Call Saul':'Better_Call_Saul.png','Dark':'Dark.png','The Last of Us':'The_Last_of_Us.png','Stranger Things':'Stranger_Things.png','Avatar: The Last Airbender':'Avatar_The_Last_Airbender.png','The Office':'The_Office.png'}.items():
            ta[t]=asset(con,'tv_'+fn.lower().replace('.png',''),'image','tv_poster',f'Resources/Images/TV_Shows/{fn}',t)
        users=[('ian','Ian','I like films that make me feel human again.','Rizal, Philippines','Drama, Romance, Coming-of-age, Psychological','Movie buddy, deep film talks, possible connection','Video editing, writing reviews, watching films','Favorite endings, comfort movies, cinematography'),('mika','Mika','I like quiet films, painful endings, and characters who say everything by saying almost nothing.','Manila, Philippines','Drama, Romance, Indie, Coming-of-age','Someone to exchange film thoughts with, movie buddy, possible connection','Photography, cafe hopping, writing','Favorite endings, soft cinematography, films that feel like memories'),('leo','Leo','Sci-fi, thrillers, and films that make my brain restart.','Quezon City, Philippines','Sci-Fi, Thriller, Mystery, Crime','Friends who like theories, rewatches, and late-night debates','Gaming, podcasts, coding','Plot twists, directors, theories, endings'),('ara','Ara','Comfort films, animation, and sitcoms are basically my love language.','Antipolo, Philippines','Animation, Comedy, Romance, Drama','Mutuals, movie nights, soft conversations','Drawing, music, sitcoms','Comfort shows, romance films, animation, cozy recommendations')]
        ids={}
        for u in users:
            con.execute("INSERT INTO users(username,password_hash,display_name,bio,location,taste_summary,looking_for,hobbies,talk_about,profile_asset_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(u[0],generate_password_hash('password'),u[1],u[2],u[3],u[4],u[5],u[6],u[7],pa[u[0]],now()))
            ids[u[0]]=con.execute("SELECT id FROM users WHERE username=?",(u[0],)).fetchone()['id']
        movies=[('Past Lives',2023,106,'Drama, Romance',ma['Past Lives']),('Aftersun',2022,102,'Drama',ma['Aftersun']),('Before Sunrise',1995,101,'Drama, Romance',ma['Before Sunrise']),('Her',2013,126,'Drama, Romance, Sci-Fi',ma['Her']),('Interstellar',2014,169,'Adventure, Drama, Sci-Fi',ma['Interstellar']),('Arrival',2016,116,'Drama, Mystery, Sci-Fi',ma['Arrival']),('Se7en',1995,127,'Crime, Mystery, Thriller',ma['Se7en']),('Inception',2010,148,'Action, Adventure, Sci-Fi',ma['Inception']),('Spirited Away',2001,125,'Animation, Adventure, Fantasy',ma['Spirited Away']),('Lady Bird',2017,94,'Comedy, Drama',ma['Lady Bird']),('Portrait of a Lady on Fire',2019,122,'Drama, Romance',ma['Portrait of a Lady on Fire']),('Cleaners',2019,78,'Comedy, Drama',ma['Cleaners'])]
        mids={}
        for m in movies:
            con.execute("INSERT INTO media_movies(title,original_title,release_year,runtime_minutes,genres,country,language,overview,poster_asset_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",(m[0],m[0],m[1],m[2],m[3],'','',m[0],m[4],now()))
            mids[m[0]]=con.execute("SELECT id FROM media_movies WHERE title=?",(m[0],)).fetchone()['id']
        tvs=[('Normal People',2020,2020,1,12,30,'Drama, Romance',ta['Normal People']),('Fleabag',2016,2019,2,12,26,'Comedy, Drama',ta['Fleabag']),('The Bear',2022,None,3,28,30,'Comedy, Drama',ta['The Bear']),('Breaking Bad',2008,2013,5,62,47,'Crime, Drama, Thriller',ta['Breaking Bad']),('Better Call Saul',2015,2022,6,63,46,'Crime, Drama',ta['Better Call Saul']),('Dark',2017,2020,3,26,50,'Crime, Drama, Mystery, Sci-Fi',ta['Dark']),('The Last of Us',2023,None,1,9,56,'Drama, Action, Adventure',ta['The Last of Us']),('Stranger Things',2016,None,4,34,50,'Drama, Fantasy, Horror, Sci-Fi',ta['Stranger Things']),('Avatar: The Last Airbender',2005,2008,3,61,23,'Animation, Action, Adventure',ta['Avatar: The Last Airbender']),('The Office',2005,2013,9,201,22,'Comedy',ta['The Office'])]
        tids={}
        for t in tvs:
            con.execute("INSERT INTO media_tv_shows(title,original_title,first_air_year,last_air_year,number_of_seasons,number_of_episodes,episode_runtime_minutes,genres,country,language,overview,poster_asset_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(t[0],t[0],t[1],t[2],t[3],t[4],t[5],t[6],'','',t[0],t[7],now()))
            tids[t[0]]=con.execute("SELECT id FROM media_tv_shows WHERE title=?",(t[0],)).fetchone()['id']
        topm={'ian':['Past Lives','Aftersun','Portrait of a Lady on Fire','Cleaners'],'mika':['Past Lives','Aftersun','Before Sunrise','Her'],'leo':['Interstellar','Arrival','Se7en','Inception'],'ara':['Spirited Away','Lady Bird','Her','Before Sunrise']}
        topt={'ian':['Breaking Bad','Better Call Saul','The Bear','Normal People'],'mika':['Normal People','Fleabag','The Bear','Breaking Bad'],'leo':['Dark','Breaking Bad','The Last of Us','Stranger Things'],'ara':['Avatar: The Last Airbender','The Office','Fleabag','The Bear']}
        for u,lst in topm.items():
            for r,t in enumerate(lst,1): con.execute("INSERT INTO user_top_movies(user_id,movie_id,ranking,created_at) VALUES(?,?,?,?)",(ids[u],mids[t],r,now()))
        for u,lst in topt.items():
            for r,t in enumerate(lst,1): con.execute("INSERT INTO user_top_tv_shows(user_id,tv_show_id,ranking,created_at) VALUES(?,?,?,?)",(ids[u],tids[t],r,now()))
        posts=[('ian','What movie made you realize that cinema can actually change how you see life?'),('mika','Aftersun still feels like a memory I accidentally borrowed from someone else.'),('leo','Rewatching Arrival tonight. Some sci-fi films really age like literature.'),('ara','Comfort movie night. I need something soft, warm, and emotionally devastating.')]
        for u,c in posts: con.execute("INSERT INTO posts(user_id,content,media_asset_id,created_at) VALUES(?,?,?,?)",(ids[u],c,fa[u],now()))
        con.execute("INSERT INTO reviews(user_id,target_type,movie_id,rating,review_text,created_at) VALUES(?,?,?,?,?,?)",(ids['ian'],'movie',mids['Portrait of a Lady on Fire'],5,'A quiet film that understands memory, longing, and the pain of looking back.',now()))
        con.execute("INSERT INTO reviews(user_id,target_type,movie_id,rating,review_text,created_at) VALUES(?,?,?,?,?,?)",(ids['mika'],'movie',mids['Past Lives'],5,'A soft and painful film about timing, memory, and the quiet grief of the life you did not choose.',now()))
        con.execute("INSERT INTO reviews(user_id,target_type,movie_id,rating,review_text,created_at) VALUES(?,?,?,?,?,?)",(ids['leo'],'movie',mids['Arrival'],4.5,'Science fiction at its most human. Beautiful, patient, and devastating.',now()))
        con.execute("INSERT INTO reviews(user_id,target_type,tv_show_id,rating,review_text,created_at) VALUES(?,?,?,?,?,?)",(ids['ara'],'tv',tids['Avatar: The Last Airbender'],5,'A comfort show that still understands growth, friendship, grief, and hope.',now()))
    # Add matches and instants for both new and old DBs
    uid={r['username']:r['id'] for r in con.execute('SELECT id,username FROM users').fetchall()}
    for a,b in [('ian','mika'),('ian','leo')]:
        if a in uid and b in uid: con.execute("INSERT OR IGNORE INTO matches(user1_id,user2_id,created_at) VALUES(?,?,?)",(*sorted([uid[a],uid[b]]),now()))
    # Instants intentionally start empty for each user. Add them from the Chats page.

@app.route('/')
def health(): return jsonify({'ok': True, 'name': 'FILMO Python Backend'})
@app.route('/static/<path:filename>')
def static_files(filename): return send_from_directory(STATIC_DIR, filename)
@app.route('/api/login', methods=['POST'])
def login():
    data=request.json or {}
    with connect() as con:
        u=con.execute('SELECT * FROM users WHERE username=?',(data.get('username','').strip(),)).fetchone()
        if u and check_password_hash(u['password_hash'], data.get('password','')): return jsonify({'ok':True,'user':one(u)})
    return jsonify({'ok':False,'message':'Invalid username or password'}),401
@app.route('/api/register', methods=['POST'])
def register():
    is_form = bool(request.content_type and "multipart/form-data" in request.content_type)
    data = request.form if is_form else (request.get_json(silent=True) or {})

    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({'ok': False, 'message': 'Username and password are required.'}), 400

    try:
        with connect() as con:
            default = con.execute("SELECT id FROM resource_assets WHERE asset_key='profile_ian'").fetchone()
            con.execute(
                'INSERT INTO users(username,password_hash,display_name,bio,location,taste_summary,looking_for,hobbies,talk_about,profile_asset_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (username, generate_password_hash(password), username, '', '', '', '', '', '', default['id'] if default else None, now())
            )
            user_id = con.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()['id']

            file = request.files.get('profile_photo') if is_form else None
            if file and file.filename:
                relative_path, original_name = save_profile_photo_file(file, user_id, username)
                asset_id = add_asset(con, 'image', 'profile', relative_path, original_name, 'user', user_id)
                con.execute('UPDATE users SET profile_asset_id=? WHERE id=?', (asset_id, user_id))

            user = con.execute("""
                SELECT u.*, ra.file_path AS profile_image
                FROM users u
                LEFT JOIN resource_assets ra ON u.profile_asset_id=ra.id
                WHERE u.id=?
            """, (user_id,)).fetchone()

        return jsonify({'ok': True, 'user': one(user)})
    except sqlite3.IntegrityError:
        return jsonify({'ok': False, 'message': 'Username is already taken'}), 409
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'message': f'Account creation failed: {str(e)}'}), 500

def user_query(user_id):
    with connect() as con:
        return one(con.execute('SELECT u.*, ra.file_path AS profile_image FROM users u LEFT JOIN resource_assets ra ON u.profile_asset_id=ra.id WHERE u.id=?',(user_id,)).fetchone())
def top_movies(user_id):
    with connect() as con:
        return many(con.execute('SELECT m.*, ra.file_path AS poster_path, utm.ranking FROM user_top_movies utm JOIN media_movies m ON utm.movie_id=m.id LEFT JOIN resource_assets ra ON m.poster_asset_id=ra.id WHERE utm.user_id=? ORDER BY utm.ranking',(user_id,)).fetchall())
def top_tv(user_id):
    with connect() as con:
        return many(con.execute('SELECT tv.*, ra.file_path AS poster_path, uttv.ranking FROM user_top_tv_shows uttv JOIN media_tv_shows tv ON uttv.tv_show_id=tv.id LEFT JOIN resource_assets ra ON tv.poster_asset_id=ra.id WHERE uttv.user_id=? ORDER BY uttv.ranking',(user_id,)).fetchall())
@app.route('/api/user/<int:user_id>/profile-photo', methods=['POST'])
def update_profile_photo(user_id):
    try:
        file = request.files.get('profile_photo')
        if not file or not file.filename:
            return jsonify({'ok': False, 'message': 'No profile photo selected'}), 400

        with connect() as con:
            existing = con.execute('SELECT id, username FROM users WHERE id=?', (user_id,)).fetchone()
            if not existing:
                return jsonify({'ok': False, 'message': 'User not found'}), 404

            relative_path, original_name = save_profile_photo_file(file, user_id, existing['username'])
            asset_id = add_asset(con, 'image', 'profile', relative_path, original_name, 'user', user_id)
            con.execute('UPDATE users SET profile_asset_id=? WHERE id=?', (asset_id, user_id))

            user = con.execute("""
                SELECT u.*, ra.file_path AS profile_image
                FROM users u
                LEFT JOIN resource_assets ra ON u.profile_asset_id=ra.id
                WHERE u.id=?
            """, (user_id,)).fetchone()

        return jsonify({'ok': True, 'user': one(user)})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'message': f'Profile photo upload failed: {str(e)}'}), 500

@app.route('/api/account/<int:user_id>', methods=['PUT'])
def update_account_credentials(user_id):
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    current_password = data.get('current_password') or ''
    new_password = data.get('new_password') or ''

    if not username:
        return jsonify({'ok': False, 'message': 'Username is required.'}), 400

    try:
        with connect() as con:
            user = con.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
            if not user:
                return jsonify({'ok': False, 'message': 'User not found.'}), 404

            taken = con.execute('SELECT id FROM users WHERE username=? AND id<>?', (username, user_id)).fetchone()
            if taken:
                return jsonify({'ok': False, 'message': 'Username is already taken.'}), 409

            if new_password:
                if not current_password or not check_password_hash(user['password_hash'], current_password):
                    return jsonify({'ok': False, 'message': 'Current password is incorrect.'}), 400
                con.execute("UPDATE users SET username=?, display_name=CASE WHEN display_name=? THEN ? ELSE display_name END, password_hash=? WHERE id=?",
                            (username, user['username'], username, generate_password_hash(new_password), user_id))
            else:
                con.execute("UPDATE users SET username=?, display_name=CASE WHEN display_name=? THEN ? ELSE display_name END WHERE id=?",
                            (username, user['username'], username, user_id))

            updated = con.execute("""
                SELECT u.*, ra.file_path AS profile_image
                FROM users u
                LEFT JOIN resource_assets ra ON u.profile_asset_id=ra.id
                WHERE u.id=?
            """, (user_id,)).fetchone()

        return jsonify({'ok': True, 'user': one(updated)})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'message': f'Account update failed: {str(e)}'}), 500

@app.route('/api/user/<int:user_id>')
def get_user(user_id):
    u=user_query(user_id)
    if not u: return jsonify({'ok':False}),404
    with connect() as con:
        counts={'posts':con.execute('SELECT COUNT(*) FROM posts WHERE user_id=?',(user_id,)).fetchone()[0],'reviews':con.execute('SELECT COUNT(*) FROM reviews WHERE user_id=?',(user_id,)).fetchone()[0],'matches':con.execute('SELECT COUNT(*) FROM matches WHERE user1_id=? OR user2_id=?',(user_id,user_id)).fetchone()[0]}
    return jsonify({'ok':True,'user':u,'top_movies':top_movies(user_id),'top_tv':top_tv(user_id),'counts':counts})
@app.route('/api/user/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    d=request.json or {}
    with connect() as con:
        con.execute('UPDATE users SET display_name=?, bio=?, location=?, taste_summary=?, looking_for=?, hobbies=?, talk_about=? WHERE id=?',(d.get('display_name',''),d.get('bio',''),d.get('location',''),d.get('taste_summary',''),d.get('looking_for',''),d.get('hobbies',''),d.get('talk_about',''),user_id))
    return jsonify({'ok':True})
@app.route('/api/user/<int:user_id>/content')
def user_content(user_id):
    viewer_id = int(request.args.get('viewer_id', user_id))
    with connect() as con:
        posts=many(con.execute('SELECT p.*, u.display_name,u.username,up.file_path AS profile_image,ma.file_path AS media_path,ma.asset_type AS media_type,(SELECT COUNT(*) FROM post_likes WHERE post_id=p.id) AS like_count,(SELECT COUNT(*) FROM comments WHERE post_id=p.id) AS comment_count,EXISTS(SELECT 1 FROM post_likes WHERE post_id=p.id AND user_id=?) AS liked_by_me FROM posts p JOIN users u ON p.user_id=u.id LEFT JOIN resource_assets up ON u.profile_asset_id=up.id LEFT JOIN resource_assets ma ON p.media_asset_id=ma.id WHERE p.user_id=? ORDER BY p.id DESC',(viewer_id,user_id)).fetchall())
        reviews=many(con.execute('SELECT r.*,u.display_name,u.username,up.file_path AS profile_image,COALESCE(mm.title,tv.title) AS title,COALESCE(mm.release_year,tv.first_air_year) AS year,COALESCE(mp.file_path,tvp.file_path) AS poster_path,(SELECT COUNT(*) FROM review_likes WHERE review_id=r.id) AS like_count,(SELECT COUNT(*) FROM review_comments WHERE review_id=r.id) AS comment_count,EXISTS(SELECT 1 FROM review_likes WHERE review_id=r.id AND user_id=?) AS liked_by_me FROM reviews r JOIN users u ON r.user_id=u.id LEFT JOIN resource_assets up ON u.profile_asset_id=up.id LEFT JOIN media_movies mm ON r.movie_id=mm.id LEFT JOIN media_tv_shows tv ON r.tv_show_id=tv.id LEFT JOIN resource_assets mp ON mm.poster_asset_id=mp.id LEFT JOIN resource_assets tvp ON tv.poster_asset_id=tvp.id WHERE r.user_id=? ORDER BY r.id DESC',(viewer_id,user_id)).fetchall())
    return jsonify({'ok':True,'posts':posts,'reviews':reviews})
@app.route('/api/feed/<int:user_id>')
def feed(user_id):
    with connect() as con:
        posts=many(con.execute('SELECT p.*,u.display_name,u.username,up.file_path AS profile_image,ma.file_path AS media_path,ma.asset_type AS media_type,(SELECT COUNT(*) FROM post_likes WHERE post_id=p.id) AS like_count,(SELECT COUNT(*) FROM comments WHERE post_id=p.id) AS comment_count,EXISTS(SELECT 1 FROM post_likes WHERE post_id=p.id AND user_id=?) AS liked_by_me FROM posts p JOIN users u ON p.user_id=u.id LEFT JOIN resource_assets up ON u.profile_asset_id=up.id LEFT JOIN resource_assets ma ON p.media_asset_id=ma.id ORDER BY p.id DESC',(user_id,)).fetchall())
    return jsonify({'ok':True,'posts':posts})
@app.route('/api/post', methods=['POST'])
def create_post():
    user_id=int(request.form.get('user_id')); content=request.form.get('content','').strip(); media_asset_id=None
    with connect() as con:
        f=request.files.get('media')
        if f and f.filename:
            rel,typ,cat=save_upload(f,'feed'); media_asset_id=add_asset(con,typ,cat,rel,f.filename,'post',user_id)
        con.execute('INSERT INTO posts(user_id,content,media_asset_id,created_at) VALUES(?,?,?,?)',(user_id,content,media_asset_id,now()))
    return jsonify({'ok':True})
@app.route('/api/post/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    user_id=(request.json or {})['user_id']
    with connect() as con:
        e=con.execute('SELECT id FROM post_likes WHERE post_id=? AND user_id=?',(post_id,user_id)).fetchone()
        if e: con.execute('DELETE FROM post_likes WHERE id=?',(e['id'],)); liked=False
        else: con.execute('INSERT OR IGNORE INTO post_likes(post_id,user_id,created_at) VALUES(?,?,?)',(post_id,user_id,now())); liked=True
        count=con.execute('SELECT COUNT(*) FROM post_likes WHERE post_id=?',(post_id,)).fetchone()[0]
    return jsonify({'ok':True,'liked':liked,'like_count':count})
@app.route('/api/post/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    user_id=int(request.args.get('user_id'))
    with connect() as con:
        if con.execute('SELECT id FROM posts WHERE id=? AND user_id=?',(post_id,user_id)).fetchone():
            con.execute('DELETE FROM comments WHERE post_id=?',(post_id,)); con.execute('DELETE FROM post_likes WHERE post_id=?',(post_id,)); con.execute('DELETE FROM posts WHERE id=?',(post_id,))
    return jsonify({'ok':True})
@app.route('/api/post/<int:post_id>/comments')
def comments(post_id):
    with connect() as con:
        c=many(con.execute('SELECT c.*,u.display_name FROM comments c JOIN users u ON c.user_id=u.id WHERE c.post_id=? ORDER BY c.id',(post_id,)).fetchall())
    return jsonify({'ok':True,'comments':c})
@app.route('/api/post/<int:post_id>/comments', methods=['POST'])
def add_comment(post_id):
    d=request.json or {}
    with connect() as con:
        con.execute('INSERT INTO comments(post_id,user_id,comment_text,created_at) VALUES(?,?,?,?)',(post_id,d['user_id'],d['comment_text'],now()))
        count=con.execute('SELECT COUNT(*) FROM comments WHERE post_id=?',(post_id,)).fetchone()[0]
    return jsonify({'ok':True,'comment_count':count})

def already_matched(con,a,b):
    low,high=sorted([a,b]); return con.execute('SELECT id FROM matches WHERE user1_id=? AND user2_id=?',(low,high)).fetchone()
def create_match(con,a,b):
    low,high=sorted([a,b]); con.execute('INSERT OR IGNORE INTO matches(user1_id,user2_id,created_at) VALUES(?,?,?)',(low,high,now()))
def score_top8(con,a,b):
    am={f"m{r['movie_id']}" for r in con.execute('SELECT movie_id FROM user_top_movies WHERE user_id=?',(a,)).fetchall()} | {f"t{r['tv_show_id']}" for r in con.execute('SELECT tv_show_id FROM user_top_tv_shows WHERE user_id=?',(a,)).fetchall()}
    bm={f"m{r['movie_id']}" for r in con.execute('SELECT movie_id FROM user_top_movies WHERE user_id=?',(b,)).fetchall()} | {f"t{r['tv_show_id']}" for r in con.execute('SELECT tv_show_id FROM user_top_tv_shows WHERE user_id=?',(b,)).fetchall()}
    shared=len(am&bm); pct=round(shared/8*100,1); label='High Match' if pct>=90 else 'Strong Match' if pct>=70 else 'Moderate Match' if pct>=50 else 'Low Match'; return pct,shared,label
@app.route('/api/people/<int:user_id>')
def people(user_id):
    cards=[]
    with connect() as con:
        users=many(con.execute("SELECT u.*,ra.file_path AS profile_image FROM users u LEFT JOIN resource_assets ra ON u.profile_asset_id=ra.id WHERE u.id!=? AND u.id NOT IN (SELECT receiver_id FROM match_requests WHERE sender_id=? AND status='pending')",(user_id,user_id)).fetchall())
        for u in users:
            if already_matched(con,user_id,u['id']): continue
            pct,shared,label=score_top8(con,user_id,u['id'])
            cards.append({'user':u,'score':pct,'shared_count':shared,'compatibility_label':label,'top_movies':top_movies(u['id']),'top_tv':top_tv(u['id'])})
    return jsonify({'ok':True,'cards':sorted(cards,key=lambda x:x['score'], reverse=True)})
@app.route('/api/match/request', methods=['POST'])
def match_request():
    d=request.json or {}; sender=int(d['sender_id']); receiver=int(d['receiver_id'])
    with connect() as con:
        rev=con.execute("SELECT * FROM match_requests WHERE sender_id=? AND receiver_id=? AND status='pending'",(receiver,sender)).fetchone()
        if rev: con.execute('UPDATE match_requests SET status="accepted" WHERE id=?',(rev['id'],)); create_match(con,sender,receiver); return jsonify({'ok':True,'status':'matched'})
        con.execute("INSERT OR IGNORE INTO match_requests(sender_id,receiver_id,message,status,created_at) VALUES(?,?,?,'pending',?)",(sender,receiver,d.get('message',''),now()))
    return jsonify({'ok':True,'status':'sent'})
@app.route('/api/liked-you/<int:user_id>')
def liked_you(user_id):
    with connect() as con:
        req=many(con.execute("SELECT mr.*,u.display_name,u.username,u.bio,u.location,u.taste_summary,up.file_path AS profile_image FROM match_requests mr JOIN users u ON mr.sender_id=u.id LEFT JOIN resource_assets up ON u.profile_asset_id=up.id WHERE mr.receiver_id=? AND mr.status='pending' ORDER BY mr.id DESC",(user_id,)).fetchall())
    return jsonify({'ok':True,'requests':req})
@app.route('/api/match/respond', methods=['POST'])
def respond_match():
    d=request.json or {}
    with connect() as con:
        req=con.execute('SELECT * FROM match_requests WHERE id=? AND receiver_id=?',(d['request_id'],d['user_id'])).fetchone()
        if req and d['action']=='accept': con.execute("UPDATE match_requests SET status='accepted' WHERE id=?",(d['request_id'],)); create_match(con,req['sender_id'],req['receiver_id'])
        elif req: con.execute("UPDATE match_requests SET status='declined' WHERE id=?",(d['request_id'],))
    return jsonify({'ok':True})

def matched_ids(con,user_id):
    return [r['user2_id'] if r['user1_id']==user_id else r['user1_id'] for r in con.execute('SELECT * FROM matches WHERE user1_id=? OR user2_id=?',(user_id,user_id)).fetchall()]
@app.route('/api/chats/<int:user_id>')
def chats(user_id):
    with connect() as con:
        rows=many(con.execute('SELECT m.*,CASE WHEN m.user1_id=? THEN u2.display_name ELSE u1.display_name END AS other_name,CASE WHEN m.user1_id=? THEN u2.username ELSE u1.username END AS other_username,CASE WHEN m.user1_id=? THEN up2.file_path ELSE up1.file_path END AS other_image,CASE WHEN m.user1_id=? THEN u2.id ELSE u1.id END AS other_id,(SELECT message_text FROM messages WHERE match_id=m.id ORDER BY id DESC LIMIT 1) AS latest_message FROM matches m JOIN users u1 ON m.user1_id=u1.id JOIN users u2 ON m.user2_id=u2.id LEFT JOIN resource_assets up1 ON u1.profile_asset_id=up1.id LEFT JOIN resource_assets up2 ON u2.profile_asset_id=up2.id WHERE m.user1_id=? OR m.user2_id=? ORDER BY m.id DESC',(user_id,user_id,user_id,user_id,user_id,user_id)).fetchall())
    return jsonify({'ok':True,'matches':rows})
@app.route('/api/instants/<int:user_id>')
def instants(user_id):
    with connect() as con:
        ids=matched_ids(con,user_id)
        instant_users=[]
        for uid in ids:
            row=con.execute("SELECT u.id,u.display_name,u.username,up.file_path AS profile_image,EXISTS(SELECT 1 FROM stories s WHERE s.user_id=u.id AND datetime(s.expires_at)>datetime('now') AND COALESCE(s.archived,0)=0) AS has_instant FROM users u LEFT JOIN resource_assets up ON u.profile_asset_id=up.id WHERE u.id=?",(uid,)).fetchone()
            if row: instant_users.append(dict(row))
        me=con.execute("SELECT u.id,u.display_name,u.username,up.file_path AS profile_image,EXISTS(SELECT 1 FROM stories s WHERE s.user_id=u.id AND datetime(s.expires_at)>datetime('now') AND COALESCE(s.archived,0)=0) AS has_instant FROM users u LEFT JOIN resource_assets up ON u.profile_asset_id=up.id WHERE u.id=?",(user_id,)).fetchone()
    return jsonify({'ok':True,'me':one(me),'instant_users':instant_users})
@app.route('/api/instants/<int:user_id>/<int:target_id>')
def instants_for_user(user_id,target_id):
    with connect() as con:
        if not already_matched(con,user_id,target_id) and user_id!=target_id: return jsonify({'ok':False,'message':'Not matched'}),403
        stories=many(con.execute("SELECT s.*,u.display_name,u.username,up.file_path AS profile_image,ma.file_path AS media_path,ma.asset_type AS media_type FROM stories s JOIN users u ON s.user_id=u.id LEFT JOIN resource_assets up ON u.profile_asset_id=up.id LEFT JOIN resource_assets ma ON s.media_asset_id=ma.id WHERE s.user_id=? AND datetime(s.expires_at)>datetime('now') AND COALESCE(s.archived,0)=0 ORDER BY s.id DESC",(target_id,)).fetchall())
    return jsonify({'ok':True,'stories':stories})

@app.route('/api/instants/archive/<int:user_id>')
def instant_archive(user_id):
    with connect() as con:
        stories=many(con.execute("SELECT s.*,u.display_name,u.username,up.file_path AS profile_image,ma.file_path AS media_path,ma.asset_type AS media_type FROM stories s JOIN users u ON s.user_id=u.id LEFT JOIN resource_assets up ON u.profile_asset_id=up.id LEFT JOIN resource_assets ma ON s.media_asset_id=ma.id WHERE s.user_id=? AND (datetime(s.expires_at)<=datetime('now') OR COALESCE(s.archived,0)=1) ORDER BY s.id DESC",(user_id,)).fetchall())
    return jsonify({'ok':True,'stories':stories})
@app.route('/api/instant', methods=['POST'])
def create_instant():
    user_id=int(request.form.get('user_id')); content=request.form.get('content','').strip(); media_asset_id=None; stype='image'
    with connect() as con:
        f=request.files.get('media')
        if f and f.filename:
            rel,typ,cat=save_upload(f,'instant'); stype=typ; media_asset_id=add_asset(con,typ,cat,rel,f.filename,'instant',user_id)
        else:
            a=con.execute("SELECT id FROM resource_assets WHERE asset_key='instant_ian_1'").fetchone(); media_asset_id=a['id'] if a else None
        exp=(datetime.now()+timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        con.execute('INSERT INTO stories(user_id,story_type,content,media_asset_id,expires_at,created_at,receiver_id,is_instant,archived) VALUES(?,?,?,?,?,?,NULL,1,0)',(user_id,stype,content,media_asset_id,exp,now()))
    return jsonify({'ok':True})
@app.route('/api/match-id')
def match_id():
    a=int(request.args.get('a')); b=int(request.args.get('b'))
    with connect() as con:
        low,high=sorted([a,b]); m=con.execute('SELECT id FROM matches WHERE user1_id=? AND user2_id=?',(low,high)).fetchone()
    return jsonify({'ok':bool(m),'match_id':m['id'] if m else None})
@app.route('/api/messages/<int:mid>')
def messages(mid):
    user_id=int(request.args.get('user_id'))
    with connect() as con:
        m=con.execute('SELECT * FROM matches WHERE id=? AND (user1_id=? OR user2_id=?)',(mid,user_id,user_id)).fetchone()
        if not m: return jsonify({'ok':False}),404
        msgs=many(con.execute('SELECT msg.*,u.display_name FROM messages msg JOIN users u ON msg.sender_id=u.id WHERE msg.match_id=? ORDER BY msg.id',(mid,)).fetchall())
    return jsonify({'ok':True,'messages':msgs})
@app.route('/api/messages/<int:mid>', methods=['POST'])
def add_message(mid):
    d=request.json or {}
    with connect() as con: con.execute('INSERT INTO messages(match_id,sender_id,message_text,created_at) VALUES(?,?,?,?)',(mid,d['sender_id'],d['message_text'],now()))
    return jsonify({'ok':True})
@app.route('/api/reviews/<int:user_id>')
def reviews(user_id):
    with connect() as con:
        rows=many(con.execute('SELECT r.*,u.display_name,u.username,up.file_path AS profile_image,COALESCE(mm.title,tv.title) AS title,COALESCE(mm.release_year,tv.first_air_year) AS year,COALESCE(mp.file_path,tvp.file_path) AS poster_path,(SELECT COUNT(*) FROM review_likes WHERE review_id=r.id) AS like_count,(SELECT COUNT(*) FROM review_comments WHERE review_id=r.id) AS comment_count,EXISTS(SELECT 1 FROM review_likes WHERE review_id=r.id AND user_id=?) AS liked_by_me FROM reviews r JOIN users u ON r.user_id=u.id LEFT JOIN resource_assets up ON u.profile_asset_id=up.id LEFT JOIN media_movies mm ON r.movie_id=mm.id LEFT JOIN media_tv_shows tv ON r.tv_show_id=tv.id LEFT JOIN resource_assets mp ON mm.poster_asset_id=mp.id LEFT JOIN resource_assets tvp ON tv.poster_asset_id=tvp.id ORDER BY r.id DESC',(user_id,)).fetchall())
    return jsonify({'ok':True,'reviews':rows})
@app.route('/api/search-media')
def search_media():
    q=(request.args.get('q') or '').lower().strip(); typ=request.args.get('type','all'); results=[]
    if not q: return jsonify({'ok':True,'results':[]})
    pattern=f'%{q}%'
    with connect() as con:
        if typ in ['movie','all']:
            results+=many(con.execute("SELECT m.id,m.title,m.release_year AS year,'movie' AS media_type,ra.file_path AS poster_path FROM media_movies m LEFT JOIN resource_assets ra ON m.poster_asset_id=ra.id WHERE lower(m.title) LIKE ? ORDER BY m.title LIMIT 20",(pattern,)).fetchall())
        if typ in ['tv','all']:
            results+=many(con.execute("SELECT tv.id,tv.title,tv.first_air_year AS year,'tv' AS media_type,ra.file_path AS poster_path FROM media_tv_shows tv LEFT JOIN resource_assets ra ON tv.poster_asset_id=ra.id WHERE lower(tv.title) LIKE ? ORDER BY tv.title LIMIT 20",(pattern,)).fetchall())
    return jsonify({'ok':True,'results':results[:30]})

@app.route('/api/review', methods=['POST'])
def create_review():
    d=request.json or {}; t=d['target_type']; movie=d['target_id'] if t=='movie' else None; tv=d['target_id'] if t=='tv' else None
    with connect() as con: con.execute('INSERT INTO reviews(user_id,target_type,movie_id,tv_show_id,rating,review_text,created_at) VALUES(?,?,?,?,?,?,?)',(d['user_id'],t,movie,tv,float(d['rating']),d['review_text'],now()))
    return jsonify({'ok':True})
@app.route('/api/review/<int:rid>/like', methods=['POST'])
def like_review(rid):
    uid=(request.json or {})['user_id']
    with connect() as con:
        e=con.execute('SELECT id FROM review_likes WHERE review_id=? AND user_id=?',(rid,uid)).fetchone()
        if e: con.execute('DELETE FROM review_likes WHERE id=?',(e['id'],)); liked=False
        else: con.execute('INSERT OR IGNORE INTO review_likes(review_id,user_id,created_at) VALUES(?,?,?)',(rid,uid,now())); liked=True
        count=con.execute('SELECT COUNT(*) FROM review_likes WHERE review_id=?',(rid,)).fetchone()[0]
    return jsonify({'ok':True,'liked':liked,'like_count':count})
@app.route('/api/top-media/<int:user_id>', methods=['PUT'])
def update_top_media(user_id):
    d=request.json or {}; ids=d.get('ids',[])[:4]
    with connect() as con:
        if d['media_type']=='movie':
            con.execute('DELETE FROM user_top_movies WHERE user_id=?',(user_id,))
            for i,mid in enumerate(ids,1): con.execute('INSERT INTO user_top_movies(user_id,movie_id,ranking,created_at) VALUES(?,?,?,?)',(user_id,mid,i,now()))
        else:
            con.execute('DELETE FROM user_top_tv_shows WHERE user_id=?',(user_id,))
            for i,tid in enumerate(ids,1): con.execute('INSERT INTO user_top_tv_shows(user_id,tv_show_id,ranking,created_at) VALUES(?,?,?,?)',(user_id,tid,i,now()))
    return jsonify({'ok':True})



@app.route('/api/review/<int:review_id>', methods=['PUT'])
def update_review(review_id):
    d=request.json or {}; uid=d['user_id']
    with connect() as con:
        e=con.execute('SELECT id FROM reviews WHERE id=? AND user_id=?',(review_id,uid)).fetchone()
        if not e: return jsonify({'ok':False,'message':'Review not found or not yours'}),404
        con.execute('UPDATE reviews SET rating=?, review_text=? WHERE id=?',(float(d['rating']),d['review_text'],review_id))
    return jsonify({'ok':True})
@app.route('/api/review/<int:review_id>', methods=['DELETE'])
def delete_review(review_id):
    uid=int(request.args.get('user_id'))
    with connect() as con:
        e=con.execute('SELECT id FROM reviews WHERE id=? AND user_id=?',(review_id,uid)).fetchone()
        if not e: return jsonify({'ok':False,'message':'Review not found or not yours'}),404
        con.execute('DELETE FROM review_comments WHERE review_id=?',(review_id,))
        con.execute('DELETE FROM review_likes WHERE review_id=?',(review_id,))
        con.execute('DELETE FROM reviews WHERE id=?',(review_id,))
    return jsonify({'ok':True})
@app.route('/api/review/<int:review_id>/comments')
def review_comments(review_id):
    with connect() as con:
        comments=many(con.execute('SELECT rc.*,u.display_name FROM review_comments rc JOIN users u ON rc.user_id=u.id WHERE rc.review_id=? ORDER BY rc.id',(review_id,)).fetchall())
    return jsonify({'ok':True,'comments':comments})

@app.route('/api/review/<int:review_id>/comments', methods=['POST'])
def add_review_comment(review_id):
    d=request.json or {}
    with connect() as con:
        con.execute('INSERT INTO review_comments(review_id,user_id,comment_text,created_at) VALUES(?,?,?,?)',(review_id,d['user_id'],d['comment_text'],now()))
        count=con.execute('SELECT COUNT(*) FROM review_comments WHERE review_id=?',(review_id,)).fetchone()[0]
    return jsonify({'ok':True,'comment_count':count})


@app.route('/api/instant/<int:story_id>/archive', methods=['POST'])
def archive_instant(story_id):
    d = request.get_json(silent=True) or {}
    user_id = int(d.get('user_id', 0))
    with connect() as con:
        story = con.execute('SELECT id FROM stories WHERE id=? AND user_id=?', (story_id, user_id)).fetchone()
        if not story:
            return jsonify({'ok': False, 'message': 'Instant not found or not yours.'}), 404
        con.execute('UPDATE stories SET archived=1 WHERE id=?', (story_id,))
    return jsonify({'ok': True})

@app.route('/api/instant/<int:story_id>', methods=['DELETE'])
def delete_instant(story_id):
    user_id = int(request.args.get('user_id', 0))
    with connect() as con:
        story = con.execute('SELECT id FROM stories WHERE id=? AND user_id=?', (story_id, user_id)).fetchone()
        if not story:
            return jsonify({'ok': False, 'message': 'Instant not found or not yours.'}), 404
        con.execute('DELETE FROM instant_reactions WHERE story_id=?', (story_id,))
        con.execute('DELETE FROM instant_replies WHERE story_id=?', (story_id,))
        con.execute('DELETE FROM stories WHERE id=?', (story_id,))
    return jsonify({'ok': True})

@app.route('/api/instant/<int:story_id>/react', methods=['POST'])
def react_instant(story_id):
    d=request.json or {}
    with connect() as con:
        con.execute('INSERT INTO instant_reactions(story_id,user_id,reaction,created_at) VALUES(?,?,?,?)',(story_id,d['user_id'],d['reaction'],now()))
    return jsonify({'ok':True})

@app.route('/api/instant/<int:story_id>/reply', methods=['POST'])
def reply_instant(story_id):
    d=request.json or {}
    with connect() as con:
        con.execute('INSERT INTO instant_replies(story_id,sender_id,reply_text,created_at) VALUES(?,?,?,?)',(story_id,d['sender_id'],d['reply_text'],now()))
    return jsonify({'ok':True})

@app.route('/api/media/<media_type>/<int:media_id>')
def media_details(media_type, media_id):
    with connect() as con:
        if media_type=='movie':
            media=con.execute("SELECT m.*,ra.file_path AS poster_path,(SELECT ROUND(AVG(rating),1) FROM reviews WHERE target_type='movie' AND movie_id=m.id) AS platform_rating,(SELECT COUNT(*) FROM reviews WHERE target_type='movie' AND movie_id=m.id) AS review_count FROM media_movies m LEFT JOIN resource_assets ra ON m.poster_asset_id=ra.id WHERE m.id=?",(media_id,)).fetchone()
            reviews=con.execute("SELECT r.*,u.display_name,u.username FROM reviews r JOIN users u ON r.user_id=u.id WHERE r.target_type='movie' AND r.movie_id=? ORDER BY r.id DESC",(media_id,)).fetchall()
        else:
            media=con.execute("SELECT tv.*,ra.file_path AS poster_path,(SELECT ROUND(AVG(rating),1) FROM reviews WHERE target_type='tv' AND tv_show_id=tv.id) AS platform_rating,(SELECT COUNT(*) FROM reviews WHERE target_type='tv' AND tv_show_id=tv.id) AS review_count FROM media_tv_shows tv LEFT JOIN resource_assets ra ON tv.poster_asset_id=ra.id WHERE tv.id=?",(media_id,)).fetchone()
            reviews=con.execute("SELECT r.*,u.display_name,u.username FROM reviews r JOIN users u ON r.user_id=u.id WHERE r.target_type='tv' AND r.tv_show_id=? ORDER BY r.id DESC",(media_id,)).fetchall()
    if not media: return jsonify({'ok':False,'message':'Media not found'}),404
    return jsonify({'ok':True,'media':one(media),'reviews':many(reviews)})

if __name__ == '__main__':
    init_db()
    app.run(host='127.0.0.1', port=5050, debug=False)
