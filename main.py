import os
import sqlite3
import re
from datetime import datetime
from flask import (Flask, g, render_template, request, redirect,
                   url_for, session, flash, jsonify)
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'content.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
# ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def save_uploaded_file(f):
    """Save a FileStorage to static/uploads and return the public URL path."""
    if not f or not getattr(f, 'filename', ''):
        return None
    filename = secure_filename(f.filename)
    # add timestamp to avoid collisions
    filename = f"{int(datetime.utcnow().timestamp())}_{filename}"
    dest = os.path.join(UPLOAD_FOLDER, filename)
    f.save(dest)
    # try to make a thumbnail (320x320) for images
    try:
        img = Image.open(dest)
        img.thumbnail((320, 320))
        thumb_name = f"thumb_{filename}"
        thumb_dest = os.path.join(UPLOAD_FOLDER, thumb_name)
        # convert RGBA to RGB background if needed
        if img.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            bg.save(thumb_dest, format="JPEG", quality=85)
        else:
            img.save(thumb_dest, quality=85)
    except Exception:
        # not an image or thumbnail failed
        pass
    return f"/static/uploads/{filename}"


def get_thumb_for(url):
    """Return thumbnail URL for a local upload if available, otherwise return original URL."""
    if not url:
        return url
    if url.startswith('/static/uploads/'):
        filename = url.split('/')[-1]
        thumb_name = f"thumb_{filename}"
        thumb_path = os.path.join(UPLOAD_FOLDER, thumb_name)
        if os.path.exists(thumb_path):
            return f"/static/uploads/{thumb_name}"
    return url

def get_yt_thumb(url):
    if not url:
        return None
    # Extraction for various YouTube URL patterns
    yt_regex = (
        r'(?:https?://)?(?:www\.)?'
        r'(?:youtube\.com/(?:watch\?v=|embed/|v/|shorts/|live/)|youtu\.be/|youtube\.com/shorts/)'
        r'([^&=%\? \n]{11})'
    )
    match = re.search(yt_regex, url)
    if match:
        video_id = match.group(1)
        # Try higher res first, but use hqdefault as fallback if it fails
        return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    return None

@app.context_processor
def utility_processor():
    return dict(get_yt_thumb=get_yt_thumb, get_thumb_for=get_thumb_for)

# Admin password - check Secrets for ADMIN_PASSWORD
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'adminpass')


def get_db():
    # Database connection management
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def init_db():
    # Initialize database tables if they do not exist
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        summary TEXT,
        type TEXT CHECK(type IN ('Writing','Multimedia')) NOT NULL,
        subtype TEXT,
        publication TEXT,
        url TEXT,
        date TEXT,
        featured INTEGER DEFAULT 0,
        category TEXT,
        image_url TEXT
    )
    ''')
    # Migrate image_url if not exists
    c.execute("PRAGMA table_info(content)")
    cols = [row[1] for row in c.fetchall()]
    if 'image_url' not in cols:
        c.execute("ALTER TABLE content ADD COLUMN image_url TEXT")
        
    c.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        message TEXT,
        date TEXT
    )
    ''')
    c.execute('CREATE TABLE IF NOT EXISTS profile (key TEXT PRIMARY KEY, value TEXT)')
    
    # Add initial profile data if empty
    c.execute("SELECT COUNT(*) FROM profile")
    if c.fetchone()[0] == 0:
        initial_data = [
            ('name', 'Aanchal Ghatak'),
            ('tagline', 'Journalist & Multimedia Storyteller'),
            ('bio', 'An inquisitive mind with a passion for uncovering stories that matter. Specialized in investigative journalism and digital multimedia. MSc Computational and Data Journalism student at Cardiff University. Previously Senior Correspondent with Dataquest India and Staff Writer at IDG.'),
            ('email', 'aanchal.ghatak05@gmail.com'),
            ('linkedin', '#'),
            ('twitter', 'https://x.com/AanchalGhatak')
        ]
        c.executemany("INSERT INTO profile (key, value) VALUES (?, ?)", initial_data)
        
    conn.commit()
    conn.close()


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def admin_required(fn):
    def wrapper(*args, **kwargs):
        if not session.get('admin'):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"status": "error", "message": "Unauthorized"}), 401
            return redirect(url_for('admin_login', next=request.path))
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


def get_profile():
    res = query_db("SELECT key, value FROM profile")
    if not res:
        return {}
    return {r['key']: r['value'] for r in res}


@app.route('/')
def home():
    profile = get_profile()
    res_featured = query_db("SELECT * FROM content WHERE featured=1 ORDER BY date DESC LIMIT 3")
    featured = res_featured if res_featured else []
    res_latest = query_db("SELECT * FROM content ORDER BY date DESC LIMIT 5")
    latest = res_latest if res_latest else []
    return render_template('home.html', featured=featured, latest=latest, profile=profile)


@app.route('/writing')
def writing():
    profile = get_profile()
    year = request.args.get('year')
    category = request.args.get('category')
    
    q = "SELECT * FROM content WHERE type='Writing'"
    args = []
    if category and category != 'All':
        q += " AND category = ?"
        args.append(category)
    if year and year != 'All':
        q += " AND substr(date, 1, 4) = ?"
        args.append(year)
    q += " ORDER BY date DESC"
    
    items = query_db(q, args) or []
    
    # Available years and categories for filters
    res_years = query_db("SELECT DISTINCT substr(date, 1, 4) as y FROM content WHERE type='Writing' AND date IS NOT NULL ORDER BY y DESC")
    years = [r['y'] for r in res_years] if res_years else []
    
    res_cats = query_db("SELECT DISTINCT category FROM content WHERE type='Writing' AND category IS NOT NULL AND category != ''")
    categories = [r['category'] for r in res_cats] if res_cats else []
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('writing_items.html', items=items)
        
    return render_template('writing.html', items=items, years=years, categories=categories, selected_year=year, selected_category=category, profile=profile)


@app.route('/multimedia')
def multimedia():
    profile = get_profile()
    items = query_db("SELECT * FROM content WHERE type='Multimedia' ORDER BY date DESC") or []
    return render_template('multimedia.html', items=items, profile=profile)


@app.route('/about')
def about():
    profile = get_profile()
    return render_template('about.html', profile=profile)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    profile = get_profile()
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        date = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        try:
            db = get_db()
            db.execute('INSERT INTO messages (name, email, message, date) VALUES (?,?,?,?)', (name, email, message, date))
            db.commit()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"status": "success", "message": "Thank you — your message was recorded."})
            flash('Thank you — your message was recorded.')
            return redirect(url_for('contact'))
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"status": "error", "message": "Could not save message."}), 500
            flash('Error saving message.', 'error')
            return redirect(url_for('contact'))
    return render_template('contact.html', profile=profile)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    profile = get_profile()
    if request.method == 'POST':
        pwd = request.form.get('password', '')
        if pwd == ADMIN_PASSWORD:
            session['admin'] = True
            flash('Logged in')
            next_url = request.args.get('next') or url_for('admin_index')
            return redirect(next_url)
        flash('Invalid password', 'error')
    return render_template('admin_login.html', profile=profile)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash('Logged out')
    return redirect(url_for('home'))


@app.route('/admin')
@admin_required
def admin_index():
    # Show the admin dashboard with cards linking to content, messages, and profile
    profile = get_profile()
    return render_template('admin_index.html', profile=profile)


@app.route('/admin/profile', methods=['GET', 'POST'])
@admin_required
def admin_profile():
    profile = get_profile()
    if request.method == 'POST':
        # Accept various profile fields and upsert into profile table
        try:
            fields = ['name', 'tagline', 'bio', 'email', 'linkedin', 'twitter', 'image_url']
            db = get_db()
            for f in fields:
                val = request.form.get(f)
                if val is None:
                    # ensure empty string is stored as empty rather than NULL
                    val = ''
                db.execute('REPLACE INTO profile (key, value) VALUES (?, ?)', (f, val))

            # handle uploaded profile image
            profile_file = request.files.get('profile_image_file')
            if profile_file and getattr(profile_file, 'filename', ''):
                saved = save_uploaded_file(profile_file)
                if saved:
                    db.execute('REPLACE INTO profile (key, value) VALUES (?, ?)', ('image_url', saved))
                else:
                    print('Warning: profile image upload did not return a path')

            # handle about gallery uploads and urls
            # existing list from form (comma separated)
            about_urls = (request.form.get('about_images') or '').strip()
            uploaded = []
            files = request.files.getlist('about_images_files') or []
            for f in files:
                if f and getattr(f, 'filename', ''):
                    try:
                        s = save_uploaded_file(f)
                        if s:
                            uploaded.append(s)
                        else:
                            print(f'Warning: uploaded file {getattr(f, "filename", "")!r} was not saved')
                    except Exception as e:
                        print('Error saving uploaded about image:', e)

            combined = []
            if about_urls:
                combined.extend([u.strip() for u in about_urls.split(',') if u.strip()])
            combined.extend(uploaded)
            if combined:
                db.execute('REPLACE INTO profile (key, value) VALUES (?, ?)', ('about_images', ','.join(combined)))
            db.commit()
        except Exception as e:
            # log error for debugging and return JSON error for AJAX
            print('Error updating profile:', e)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500
            flash('Error updating profile', 'error')
            return redirect(url_for('admin_profile'))

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"status": "success", "message": "Profile updated"})
        flash('Profile updated')
        return redirect(url_for('admin_index'))

    return render_template('admin_profile.html', profile=profile)


@app.route('/admin/profile/delete_image', methods=['POST'])
@admin_required
def admin_profile_delete_image():
    img = request.form.get('image')
    if not img:
        return jsonify({"status":"error","message":"No image specified"}), 400
    db = get_db()
    current = query_db("SELECT value FROM profile WHERE key='about_images'", one=True)
    imgs = []
    if current and current['value']:
        imgs = [s.strip() for s in current['value'].split(',') if s.strip()]
    if img in imgs:
        imgs.remove(img)
        newv = ','.join(imgs)
        db.execute('REPLACE INTO profile (key, value) VALUES (?,?)', ('about_images', newv))
        db.commit()
        # delete local files if under uploads
        try:
            if img.startswith('/static/uploads/'):
                fn = img.split('/')[-1]
                p = os.path.join(UPLOAD_FOLDER, fn)
                if os.path.exists(p):
                    os.remove(p)
                thumb = os.path.join(UPLOAD_FOLDER, f"thumb_{fn}")
                if os.path.exists(thumb):
                    os.remove(thumb)
        except Exception:
            pass
        return jsonify({"status":"success","message":"Deleted"})
    return jsonify({"status":"error","message":"Not found"}), 404


@app.route('/admin/content')
@admin_required
def admin_content():
    profile = get_profile()
    items = query_db('SELECT * FROM content ORDER BY date DESC') or []
    return render_template('admin_content.html', items=items, profile=profile)


@app.route('/admin/messages')
@admin_required
def admin_messages():
    profile = get_profile()
    messages = query_db('SELECT * FROM messages ORDER BY date DESC') or []
    return render_template('admin_messages.html', messages=messages, profile=profile)


@app.route('/admin/messages/delete/<int:msg_id>', methods=['POST'])
@admin_required
def admin_delete_message(msg_id):
    db = get_db()
    db.execute('DELETE FROM messages WHERE id = ?', (msg_id,))
    db.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"status": "success", "message": "Message deleted"})
    flash('Message deleted')
    return redirect(url_for('admin_messages'))


@app.route('/admin/new', methods=['GET', 'POST'])
@admin_required
def admin_new():
    profile = get_profile()
    if request.method == 'POST':
        data = {
            'title': request.form.get('title'),
            'summary': request.form.get('summary'),
            'type': request.form.get('type'),
            'subtype': request.form.get('subtype'),
            'publication': request.form.get('publication'),
            'url': request.form.get('url'),
            'date': request.form.get('date') or datetime.utcnow().strftime('%Y-%m-%d'),
            'featured': 1 if request.form.get('featured') == 'on' else 0,
            'category': request.form.get('category'),
            'image_url': request.form.get('image_url')
        }
        # handle uploaded image file (prefer upload over URL if provided)
        file = request.files.get('image_file')
        if file and getattr(file, 'filename', ''):
            saved = save_uploaded_file(file)
            if saved:
                data['image_url'] = saved
        db = get_db()
        db.execute('''INSERT INTO content (title, summary, type, subtype, publication, url, date, featured, category, image_url)
                      VALUES (?,?,?,?,?,?,?,?,?,?)''',
                   (data['title'], data['summary'], data['type'], data['subtype'], data['publication'], data['url'], data['date'], data['featured'], data['category'], data['image_url']))
        db.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"status": "success", "message": "Created"})
        flash('Created')
        return redirect(url_for('admin_content'))
    return render_template('admin_edit.html', item=None, profile=profile)


@app.route('/admin/edit/<int:item_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit(item_id):
    profile = get_profile()
    item = query_db('SELECT * FROM content WHERE id = ?', (item_id,), one=True)
    if not item:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"status": "error", "message": "Not found"}), 404
        flash('Not found', 'error')
        return redirect(url_for('admin_content'))
    if request.method == 'POST':
        data = {
            'title': request.form.get('title'),
            'summary': request.form.get('summary'),
            'type': request.form.get('type'),
            'subtype': request.form.get('subtype'),
            'publication': request.form.get('publication'),
            'url': request.form.get('url'),
            'date': request.form.get('date') or (item['date'] if item and 'date' in item.keys() else datetime.utcnow().strftime('%Y-%m-%d')),
            'featured': 1 if request.form.get('featured') == 'on' else 0,
            'category': request.form.get('category'),
            'image_url': request.form.get('image_url')
        }
        # handle uploaded image file (prefer upload over URL if provided)
        file = request.files.get('image_file')
        if file and getattr(file, 'filename', ''):
            saved = save_uploaded_file(file)
            if saved:
                data['image_url'] = saved
        db = get_db()
        db.execute('''UPDATE content SET title=?, summary=?, type=?, subtype=?, publication=?, url=?, date=?, featured=?, category=?, image_url=? WHERE id=?''',
                   (data['title'], data['summary'], data['type'], data['subtype'], data['publication'], data['url'], data['date'], data['featured'], data['category'], data['image_url'], item_id))
        db.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"status": "success", "message": "Updated"})
        flash('Updated')
        return redirect(url_for('admin_content'))
    return render_template('admin_edit.html', item=item, profile=profile)


@app.route('/admin/delete/<int:item_id>', methods=['POST'])
@admin_required
def admin_delete(item_id):
    db = get_db()
    db.execute('DELETE FROM content WHERE id = ?', (item_id,))
    db.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"status": "success", "message": "Deleted"})
    flash('Deleted')
    return redirect(url_for('admin_content'))


if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    # Respect PORT env var so restarts can pick a non-conflicting port
    port = int(os.environ.get('PORT', '5003'))
    app.run(host='0.0.0.0', port=port)
