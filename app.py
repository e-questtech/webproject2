from flask import Flask, render_template, request, redirect, url_for, session,g, jsonify, flash,Response, make_response
from datetime import timedelta
import hashlib   
import random
import re
import datetime
from datetime import datetime
import pymysql
from flask_caching import Cache
from config import Config
import os
from functools import wraps
# Cloudinary to store the uploaded blog images
from cloudinary.uploader import upload
from cloudinary.utils import cloudinary_url
from flask_mail import Mail, Message


app = Flask(__name__)

app.config.from_object(Config)
app.config['DEBUG'] = True

MAIL_SERVER = app.config['MAIL_SERVER']
MAIL_PORT = app.config['MAIL_PORT']
MAIL_USERNAME = app.config['MAIL_USERNAME']
MAIL_PASSWORD = app.config['MAIL_PASSWORD']
MAIL_USE_TLS = app.config['MAIL_USE_TLS']
MAIL_USE_SSL = app.config['MAIL_USE_SSL']
 
mail = Mail(app) 


# LInk to the online database ffrom Aiven
connection = pymysql.connect(
        host=app.config['DATABASE_HOST'],
        user=app.config['DATABASE_USER'],
        password=app.config['DATABASE_PASSWORD'],
        db=app.config['DATABASE_NAME'],
        port=app.config['DATABASE_PORT'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    
cursor = connection.cursor()

# For sessions

app.config['PERMANENT_SESSION_LIFETIME'] =  timedelta(minutes=30)


# To Make secret key

app.secret_key = app.config['SECRET_KEY']


app.config['CACHE_TYPE'] = 'SimpleCache'  # You can also use 'RedisCache', 'FileSystemCache', etc.
app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # Cache timeout (in seconds)

# Initialize Cache
cache = Cache(app)
# _____________________________________________________________________
# PROGRAM STARTS

def roles_required(allowed_roles):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session:
                flash('Session Timeout', 'warning')
            elif session['role'] not in allowed_roles:
                flash('You do not have permission to access this page.', 'danger')
                # Modify a custom error template for admin roles
                return redirect(url_for('admin_login'))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper


def log_admin_action(admin_email, action, details=None):
    sql = """
    INSERT INTO admin_logs (admin_email, action, details)
    VALUES (%s, %s, %s)
    """
    cursor.execute(sql, (admin_email, action, details))

    connection.commit()
    

# Homepage
@app.route('/')
def index():
    return render_template('index.html')
        
#Contact 
@app.route("/contact/", methods = ["GET", "POST"])
def contact():
    return render_template('contact.html')

# Blog 
@app.route("/blog/", methods = ["GET", "POST"])
def blog():
    sql = "select * from Blog order by publish_date desc"
    cursor.execute(sql)
    blogs = cursor.fetchall()
    category_sql = "select category from Blog"
    cursor.execute(category_sql)
    category = cursor.fetchall()
    return render_template('all_blogs.html', blogs = blogs, category = category)

# # Blog Category
# @app.route("/blog/category/<name>/", methods = ["GET", "POST"])
# def category(name):
#     category_sql = "select category from Blog"
#     cursor.execute(category_sql)
#     category = cursor.fetchall()
#     return render_template('all_blogs.html', category = category)

# Single Blog Post
@app.route("/blog/<blog_link>/", methods=["GET", "POST"])
def blog_post(blog_link):
    sql = "SELECT * FROM Blog WHERE blog_link = %s"
    cursor.execute(sql, (blog_link,))
    blog = cursor.fetchone()
    
    if blog:
        return render_template('blog.html', blog=blog)
    else:
        return render_template('404.html')
            
# About Page
@app.route("/about/")
def about():
    return render_template('about.html')

#Cohort
@app.route("/cohort/")
def cohort():
    return render_template('cohort.html')
        
# Display the videos in the site
@app.route('/videos/')
def videos():
    sql_select = "select * from Videos"
    cursor.execute(sql_select)
    videos = cursor.fetchall()
    return render_template('videos.html', videos=videos)


# Admin Panel

# For admin login
@app.route('/admin/login/', methods =['GET', 'POST']) 
def admin_login():
    msg = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = str(request.form['email'])
        _password = str(request.form['password'])
        password = hashlib.sha256(_password.encode()).hexdigest()
        sql_select = "SELECT * FROM Admins WHERE EMAIL = '%s' AND PASSWORD_ = '%s'"%(email, password)
        cursor.execute(sql_select)
        verify = cursor.fetchone()
        if verify:
            session['loggedin'] = True
            session['password'] = verify['PASSWORD_']
            session['email'] = verify['EMAIL']
            session['role'] = verify['role']
            return redirect(url_for('dashboard'))
        else:
            msg = 'Invalid Email Address / Password!!'
            flash(msg, 'error')
    return render_template('login.html')

# Create Admin
@app.route("/admin/create/", methods=["GET", "POST"])
@roles_required('superadmin')
def create_admin():
    msg = ''
    if 'loggedin' in session and session['role'] == 'superadmin':
        if request.method == 'POST' and all(key in request.form for key in ['first_name', 'last_name', 'email', 'password', 'role']):
            first_name = request.form['first_name'].strip().upper()
            last_name = request.form['last_name'].strip().upper()
            email = request.form['email'].strip()
            role = request.form['role'].strip()

            # Validate the email format
            if not re.match(r'^[a-zA-Z]+\.[a-zA-Z]+@tequant\.ng$', email):
                msg = 'Invalid email address!'
                flash(msg, 'error')
                return render_template('create_admin.html')

            _password = request.form['password']
            password = hashlib.sha256(_password.encode()).hexdigest()

            # Check if email already exists in the database
            cursor.execute("SELECT * FROM Admins WHERE EMAIL = %s", (email,))
            if cursor.fetchone():
                msg = 'Account already exists!'
                flash(msg, 'error')
                return render_template('create_admin.html')

            # Insert the new admin with role
            sql = """INSERT INTO Admins(FIRST_NAME, LAST_NAME, EMAIL, PASSWORD_, ROLE) VALUES(%s, %s, %s, %s, %s)"""
            vals = (first_name, last_name, email, password, role)
            cursor.execute(sql, vals)
            connection.commit()
            log_admin_action(session['email'], 'Created a new Admin', 'Name: %s %s'%(first_name, last_name))
            msg = 'Added successfully!'
            flash(msg, 'success')
            return redirect(url_for('dashboard'))
        
        return render_template('create_admin.html')
    msg = 'Session Timeout'
    flash(msg, 'warning')
    return redirect(url_for('admin'))

    
# Admin Dashboard
@app.route('/admin/')
@roles_required(['superadmin', 'tutor', 'content_manager'])
def dashboard():
    if 'loggedin' in session:
        sql_select = "SELECT * FROM Admins WHERE email = '%s' and password_ = '%s'"%(session['email'],session['password'] )
        cursor.execute(sql_select)
        name = cursor.fetchall()
        sql_select = "select count(*) from Students;"
        cursor.execute(sql_select)
        students = cursor.fetchall()
        sql_select = "select count(*) from Admins"
        cursor.execute(sql_select)
        admins = cursor.fetchall()
        sql_select = "select count(*) from Blog"
        cursor.execute(sql_select)
        blogs = cursor.fetchall()
        sql_select = "select count(*) from Videos"
        cursor.execute(sql_select)
        videos = cursor.fetchall()
        return render_template("dashboard.html", name = name, students = students, admins = admins, blogs = blogs, videos = videos)

    return redirect(url_for('admin_login', next= "url_for('dashboard')"))

# Add Blog Post
@app.route("/admin/blog/add/", methods=["GET", "POST"])
@roles_required(['superadmin', 'content_manager'])
def add_blog():
    if 'loggedin' in session:
        
        sql = "select first_name, last_name from Admins where email = '%s'" % session['email']
        cursor.execute(sql)
        names = cursor.fetchall()
        publish_date = datetime.now()

        if request.method == 'POST' and 'title' in request.form and 'body' in request.form and 'category' in request.form and 'author' in request.form:
            title = request.form['title']
            blog_link = title.lower().replace(' ', '-')
            body = request.form['body']
            category = request.form['category'].title()
            author = request.form['author']

            # Handle image upload with Cloudinary
            image = request.files.get('image')
            image_url = None

            if image:
                # Validate image file
                valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
                file_extension = os.path.splitext(image.filename)[1].lower()
                if file_extension not in valid_extensions:
                    flash('Invalid image type! Only JPG, JPEG, PNG, and GIF are allowed.', 'error')
                    return render_template('add_blog.html', names=names, publish_date=publish_date)

                # Upload the image to Cloudinary
                try:
                    upload_result = upload(image)
                    image_url = upload_result.get('secure_url')  # Get the uploaded image URL
                except Exception as e:
                    flash(f'Image upload failed: {str(e)}', 'error')
                    return render_template('add_blog.html', names=names, publish_date=publish_date)

            # Check if blog already exists
            sql_select = "SELECT * FROM Blog WHERE blog_link = '%s'" % blog_link
            cursor.execute(sql_select)
            new_blog = cursor.fetchone()

            if new_blog:
                msg = 'Blog already Posted !!!'
                flash(msg, 'error')
                return render_template('add_blog.html', msg=msg, names=names)

            else:
                # Insert into Blog
                sql = """INSERT INTO Blog (Title, Body, Category, Author, Publish_Date, blog_link, image_url) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s)"""
                vals = (title, body, category, author, publish_date, blog_link, image_url)
                cursor.execute(sql, vals)
                connection.commit()
                log_admin_action(session['email'], 'Added a new Blog', f'Blog Title: {title}')
                msg = 'Posted successfully !!'
                flash(msg, 'success')
            return redirect(url_for('read_blog', blog_link=blog_link))

        return render_template('add_blog.html', names=names, publish_date=publish_date)
        
    msg = 'Session Timeout'
    flash(msg, 'warning')
    return redirect(url_for('admin_login', next="url_for('add_blog')"))

# Edit and Save Blog Post
@app.route("/admin/blog/<blog_link>/edit/", methods=['GET', 'POST'])
@roles_required(['superadmin', 'content_manager'])
def edit_blog(blog_link):
    if 'loggedin' in session:
        # Fetch the blog post details
        sql_select = "SELECT * FROM Blog WHERE blog_link = %s"
        cursor.execute(sql_select, (blog_link,))
        record = cursor.fetchone()
        author = record['author']
        
        # If the form is submitted (POST method), update the blog post
        if request.method == 'POST':
            if 'title' in request.form and 'body' in request.form and 'category' in request.form and 'image' in request.form:
                title = request.form['title']
                updated_blog_link = title.lower().replace(' ', '-')  # Create new blog link from title
                body = request.form['body']
                category = request.form['category'].title()
                
                # Handle image upload with Cloudinary
                image = request.files.get('image')
                image_url = None

                if image:
                    # Validate image file
                    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
                    file_extension = os.path.splitext(image.filename)[1].lower()
                    if file_extension not in valid_extensions:
                        flash('Invalid image type! Only JPG, JPEG, PNG, and GIF are allowed.', 'error')
                        return render_template('edit_blog.html', record=record)

                    # Upload the image to Cloudinary
                    try:
                        upload_result = upload(image)
                        image_url = upload_result.get('secure_url')  # Get the uploaded image URL
                    except Exception as e:
                        flash(f'Image upload failed: {str(e)}', 'error')
                        return render_template('edit_blog.html', record=record)
                else:
                    image_url = None
                
                    # Update Blog
                    sql_update = """UPDATE Blog SET Title = %s, Body = %s, Category = %s, Author = %s, image_url = %s, Blog_Link = %s WHERE Blog_Link = %s"""
                    vals = (title, body, category, author, image_url, updated_blog_link, blog_link)
                    cursor.execute(sql_update, vals)
                    connection.commit()
                    log_admin_action(session['email'], 'Edit Blog', f'Blog Title: {title}')
                    flash('Blog post updated successfully!', 'success')
                return redirect(url_for('blog_view'))  # Redirect to blog view or dashboard

        # If it's a GET request, render the edit form with the existing blog post data
        return render_template('edit_blog.html', record=record)
    return redirect(url_for('admin_login'))
           
        

# View blog in Admin Panel
@app.route("/admin/blog/<blog_link>/", methods=['GET', 'POST'])
@roles_required(['superadmin', 'content_manager'])      
def read_blog(blog_link):
    if 'loggedin' in session:
        sql = "SELECT * FROM Blog WHERE blog_link = %s"
        cursor.execute(sql, (blog_link,))
        blog = cursor.fetchone()
        return render_template('read_blog.html', blog=blog)
        
    return redirect(url_for('admin_login'))


# View All Blogs
@app.route("/admin/blog/all/", methods = ["GET", "POST"])
@roles_required(['superadmin', 'content_manager'])
def blog_view():
    if 'loggedin' in session:
        sql_select = "SELECT * FROM Blog"
        cursor.execute(sql_select)
        record = cursor.fetchall()
        return render_template("blog_view.html", record = record)
        
    return redirect(url_for('admin_login', next="url_for('blog_view')"))

# Delete Blog
@app.route('/admin/blog/<blog_link>/delete/', methods = ['GET', 'POST'])
@roles_required(['superadmin', 'content_manager'])
def delete_blog(blog_link):
    if 'loggedin' in session:
        if request.method == 'POST' and 'confirm' in request.form:
            confirm = request.form['confirm']
            if confirm == 'YES':
                # sql_ = "select image_url from Blog where blog_link = '%s'" %blog_link
                #cursor.execute(sql_)
                #image_url = cursor.fetchone()
                #  public_id = "/".join(image_url.split('/')[-2:])[:-4]
                # result = cloudinary.uploader.destroy(public_id)
                sql = "DELETE from Blog WHERE blog_link = '%s'" %blog_link
                cursor.execute(sql)
                connection.commit()
                log_admin_action(session['email'], 'Beleted Blog', f'Blog Title: {blog_link}')
                msg = 'You have successfully deleted Blog Post'
                flash(msg, 'success')
                return redirect(url_for('blog_view'))
        return render_template('delete_blog.html', blog_link = blog_link)
        
    return redirect(url_for('admin_login'))

# Add videos site
# Add Video Post
@app.route("/admin/video/add/", methods = ["GET", "POST"])
@roles_required(['superadmin', 'content_manager'])
def add_video():
    if 'loggedin' in session:
            upload_date = datetime.now()
            if request.method == 'POST' and 'title' in request.form and 'link' in request.form:
                title = request.form['title']
                link = request.form['link']
                sql_select = "select * from Videos where Link = '%s'"%link
                cursor.execute(sql_select)
                new_video = cursor.fetchone()
                if new_video:
                    msg = 'Video already Posted !!!'
                    flash(msg, 'error')
                    return render_template('add_video.html', msg = msg)
                else:
                    sql = """insert into Videos (Title, Link, upload_date) values(%s, %s, %s)"""
                    vals = (title, link, upload_date)
                    cursor.execute(sql, vals)
                    connection.commit()
                    log_admin_action(session['email'], 'Added a new Video', f'Title: {title}')
                    msg = 'Video Posted successfully !!'
                    flash(msg, 'success')
                return redirect(url_for('video_view'))
            return render_template('add_video.html',upload_date = upload_date)
        
    msg = 'Session TimeOut'
    flash(msg, 'warning')
    return redirect(url_for('admin_login', next="url_for('add_video')") )

# All Videos
@app.route("/admin/video/all/", methods = ["GET", "POST"])
@roles_required(['superadmin', 'content_manager'])
def video_view():
    if 'loggedin' in session:
            sql_select = 'SELECT * FROM Videos' 
            cursor.execute(sql_select)
            record = cursor.fetchall()
            return render_template("all_videos.html", record = record)
        
    return redirect(url_for('admin_login', next="url_for('video_view')"))

# Delete Video
@app.route('/admin/video/<video_link>/delete/', methods = ['GET', 'POST'])
@roles_required(['superadmin', 'content_manager'])
def delete_video(video_link):
    if 'loggedin' in session:
        if request.method == 'POST' and 'confirm' in request.form:
            confirm = request.form['confirm']
            if confirm == 'YES':
                sql = "DELETE FROM Videos WHERE Link = %s"%video_link
                cursor.execute(sql)
                connection.commit()
                log_admin_action(session['email'], 'Delete Video', f'Link: {video_link}')
                msg = 'You have successfully deleted Blog Post'
                flash(msg, 'success')
                return redirect(url_for('video_view'))
        return render_template('delete_video.html', video_link = video_link)
        
    return redirect(url_for('admin_login'))
        
            

@app.route("/admin/student/create/", methods = ["GET", "POST"])
@roles_required(['superadmin'])
def create_student():
    if 'loggedin' in session:
            sql ="select * from Courses"
            cursor.execute(sql)
            courses = cursor.fetchall()
            date_registered = datetime.now()
            if request.method == 'POST' and 'first_name'in request.form and 'last_name' in request.form and 'email'  in request.form:# and courses in request.form:
                first_name = request.form['first_name'].upper()
                last_name = request.form['last_name'].upper()
                email = request.form['email']
                course_code = request.form.get('courses')
                STUDENT_ID = str(course_code)+'/'+ str(datetime.now().year) + '/'+ str(random.randint(1, 100))
                password = 0000
                cursor.execute("SELECT * from Courses WHERE course_code = '%s'"%course_code)
                course_title = cursor.fetchone()
                cursor.execute("SELECT * from Students WHERE Student_ID = '%s'"%STUDENT_ID)
                new_user = cursor.fetchone()
                if new_user:
                    msg = 'Student already exists !'
                    flash(msg, 'error')
                    return render_template('create_student.html', msg = msg)
                else:
                    sql = """INSERT INTO Students(FIRST_NAME, LAST_NAME, EMAIL, PASSWORD_, Student_ID, Date_Registered, COURSE) VALUES(%s, %s, %s, %s, %s, %s, %s)"""
                    vals = (first_name, last_name, email, password, STUDENT_ID, date_registered, course_title['course_title'])
                    cursor.execute(sql, vals)
                    connection.commit()
                    log_admin_action(session['email'], 'Added a new Student', f'Student ID: {STUDENT_ID}')
                    msg = 'Added successfully !!'
                    flash(msg, 'success')
                    
                return redirect(url_for('all_students'))
            return render_template('create_student.html', courses = courses)
        
    msg = 'Session TimeOut'
    flash(msg, 'warning')
    return redirect(url_for('admin_login', next="url_for('create_student')"))

# View All Students
@app.route("/admin/student/all/", methods = ["GET", "POST"])
@roles_required(['superadmin', 'tutor'])
def all_students():
    if 'loggedin' in session:
        sql_select = "SELECT * FROM Students;"
        cursor.execute(sql_select)
        record = cursor.fetchall()
        return render_template("all_students.html", record = record)
        
    return redirect(url_for('admin_login', next="url_for('all_students')"))

# To add courses
@app.route('/admin/course/add/', methods=["GET", "POST"])
@roles_required(['superadmin'])
def add_course():
    if 'loggedin' in session:
        if request.method == 'POST' and 'course_code' in request.form and 'course_title' in request.form:
            course_code = request.form['course_code']
            course_title = request.form['course_title']
            course_description = request.form['course_description']
            
            # Check if course already exists
            sql_select = "SELECT * FROM Courses WHERE course_code = %s"
            cursor.execute(sql_select, (course_code,))
            new_course = cursor.fetchone()
            
            if new_course:
                msg = 'Course already added !!!'
                flash(msg, 'error')
                return render_template('add_course.html', msg=msg)
            else:
                # Insert new course with description and curriculum
                sql = """INSERT INTO Courses (course_title, course_code, course_description) 
                            VALUES (%s, %s, %s, %s)"""
                vals = (course_title, course_code, course_description)
                cursor.execute(sql, vals)
                connection.commit()
                log_admin_action(session['email'], 'Added a new course', f'Course Name: {course_title}')
                msg = 'Course added successfully !!'
                flash(msg, 'success')
                return redirect(url_for('courses'))
        return render_template('add_course.html')
        
    msg = 'Session TimeOut'
    flash(msg, 'warning')
    return redirect(url_for('admin_login', next="url_for('add_course')"))

@app.route('/admin/course/all/', methods = ["GET", "POST"])
@roles_required(['superadmin'])
def courses():
    if 'loggedin' in session:
        sql_select = 'SELECT * FROM Courses' 
        cursor.execute(sql_select)
        record = cursor.fetchall()
        return render_template("courses.html", record = record)
        
    return redirect(url_for('admin_login', next="url_for('courses')"))

# Courses All
@app.route('/courses/', methods=["GET"])
def all_courses():
    try:
        sql = "SELECT * FROM Courses"
        cursor.execute(sql)
        courses = cursor.fetchall()
        return render_template('all_courses.html', courses=courses)
    except Exception as e:
        flash('Error fetching courses: {}'.format(str(e)), 'error')
        return redirect(url_for('index'))
            
# Courses Individually
@app.route('/courses/<course_code>/', methods=["GET"])
def course_detail(course_code):
    try:
        sql = "SELECT * FROM Courses WHERE course_code = %s"
        cursor.execute(sql, (course_code,))
        course = cursor.fetchone()
        
        if course:
            # Log the course details for debugging
            print(f"Course found: {course}")  # or use logging.debug() if using logging
            return render_template('course_detail.html', course=course)
        else:
            print("Course not found.")  # Log if no course is found
            return render_template('404.html')  # Render a 404 page if course not found
    except Exception as e:
        print(f'Error fetching course details: {str(e)}')  # Log the error
        flash('Error fetching course details: {}'.format(str(e)), 'error')
        return redirect(url_for('index'))


@app.route('/sitemap.xml/', methods = ["GET"])
def sitemap():
    urls = [
        url_for('blog'),
        url_for('about'),
        url_for('videos'),
        url_for('contact')
    ]
    return Response(render_template('sitemap.xml', urls=urls), mimetype='application/xml')

# Student Register (Prospective)
@app.route('/sign_up/', methods=["GET", "POST"])
def student_register():
    # Check if user is not logged in or is not an admin
    sql = "SELECT * FROM Courses"
    cursor.execute(sql)
    courses = cursor.fetchall()
    
    if request.method == "POST" and 'fullName' in request.form and 'email' in request.form and 'countryCode' in request.form and 'phone' in request.form and 'course' in request.form and 'state' in request.form:
        full_name = request.form['fullName']
        email = request.form['email']
        country_code = request.form['countryCode']
        phone = request.form['phone']
        
        # Combine country code and phone number
        full_phone = f"{country_code}{phone}"
        
        preferred_course = request.form['course']
        state = request.form['state']
        other_state = request.form.get('otherState', 'NONE')  # Default to 'NONE' if not provided

        sql_select = "SELECT * FROM prospective_students WHERE email = %s"
        cursor.execute(sql_select, (email,))
        student = cursor.fetchone()
        
        if student:
            msg = 'Student already Registered !!!'
            flash(msg, 'error')
            return render_template('student_register.html', msg=msg, courses=courses)
        else:
            sql = """INSERT INTO prospective_students (full_name, email, phone_number, preferred_course, state, other_state)
                        VALUES (%s, %s, %s, %s, %s, %s)"""
            vals = (full_name, email, full_phone, preferred_course, state, other_state)
            cursor.execute(sql, vals)
            connection.commit()
            flash('Registration submitted successfully!', 'success')
            return redirect(url_for('index'))

    return render_template('student_register.html', courses=courses)


@app.route('/admin/students/new/', methods=["GET"])
@roles_required(['superadmin'])
def prospective_students():
    if 'loggedin' in session:
        sql = "SELECT * FROM prospective_students"
        cursor.execute(sql)
        students = cursor.fetchall()
        return render_template('prospective_students.html', students=students)
    else:
        return redirect(url_for('admin_login', next="url_for('prospective_students')"))


# Student Login
@app.route('/student/login/', methods=["GET", "POST"])
def login():
    msg = ''
    if request.method == 'POST' and 'STUDENT_ID' in request.form and 'password' in request.form:
        STUDENT_ID = str(request.form['STUDENT_ID'])
        _password = str(request.form['password'])
        # password = hashlib.sha256(_password.encode()).hexdigest()
        sql_select = "SELECT * FROM Students WHERE STUDENT_ID = '%s' or EMAIL = '%s' AND PASSWORD_ = '%s'"%(STUDENT_ID, STUDENT_ID, _password)
        cursor.execute(sql_select)
        verify = cursor.fetchone()
        if verify:
            session['loggedin'] = True
            session['STUDENT_ID'] = verify['STUDENT_ID']
            session['password'] = verify['PASSWORD_']
            
            return redirect(url_for('student_dashboard'))
        else:
            msg = 'Invalid Email Address / Password!!'
            flash(msg, 'error')
    return render_template('student_login.html')

# Student Dashboard
@app.route('/dashboard/', methods=["GET", "POST"])
def student_dashboard():
    if 'loggedin' in session:
        sql_select = "SELECT * FROM Students WHERE STUDENT_ID = '%s' and password_ = '%s'"%(session['STUDENT_ID'],session['password'] )
        cursor.execute(sql_select)
        student = cursor.fetchone()
        
        return render_template("student_dashboard.html", student = student)

    return redirect(url_for('login', next= "url_for('student_dashboard')"))


# Superadmin Assign Course to Tutors
@app.route('/admin/tutor/assign', methods=['GET', 'POST'])
@roles_required(['superadmin'])
def assign_tutor():
    if request.method == 'POST':
        tutor_email = request.form.get('tutor_email')
        course_code = request.form.get('course_code')
        # Insert into the TutorCourse table
        sql = """
            INSERT INTO TutorCourse (tutor_email, course_code)
            VALUES (%s, %s)
        """
        vals = (tutor_email, course_code)

        try:
            cursor.execute(sql, vals)
            connection.commit()  
            log_admin_action(session['email'], 'Assigned Course to %s'%tutor_email, f'Course Code: {course_code}')
            flash('Tutor assigned to course successfully!', 'success')
        except Exception as e:
            connection.rollback()  # Rollback in case of an error
            flash(f'Error assigning tutor to course: {str(e)}', 'danger')

        return redirect(url_for('dashboard'))

    # Load available tutors and courses for the dropdowns
    try:
        # Fetch tutors with the role 'tutor'
        sql_select_tutors = """SELECT email, FIRST_NAME, LAST_NAME FROM Admins WHERE role = 'tutor'"""
        cursor.execute(sql_select_tutors)
        tutors = cursor.fetchall()  # No need to commit after SELECT

        # Fetch courses
        sql_select_courses = """SELECT course_code, course_title FROM Courses"""
        cursor.execute(sql_select_courses)
        courses = cursor.fetchall()  # No need to commit after SELECT
    except Exception as e:
        flash(f'Error loading data: {str(e)}', 'danger')
        tutors, courses = [], []

    return render_template('assign_tutor.html', tutors=tutors, courses=courses)

# Tutors and Assigned Courses
@app.route('/admin/tutors/',methods=['GET'])
@roles_required(['superadmin'])
def view_tutors():
    sql_select = """
        SELECT Admins.first_name, Admins.last_name, Admins.email, Courses.course_title
        FROM Admins
        JOIN TutorCourse ON Admins.email = TutorCourse.tutor_email
        JOIN Courses ON TutorCourse.course_code = Courses.course_code
        WHERE Admins.role = 'tutor';
    """
    cursor.execute(sql_select)
    tutors_with_courses = cursor.fetchall()

    return render_template('tutors.html', tutors_with_courses=tutors_with_courses)

# Tutors add Assignment
@app.route('/tutor/assignment/add', methods=['GET', 'POST'])
@roles_required(['tutor', 'superadmin'])
def add_assignment():
    tutor_email = session['email']  # Assuming the tutor's email is stored in the session
    if not tutor_email:
        flash('You need to be logged in to add an assignment.', 'error')
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        course_code = request.form['course']
        content = request.form['content']

        # Insert the new post into the database
        sql_insert = """
            INSERT INTO Posts (course_code, tutor_email, content) VALUES (%s, %s, %s)
        """
        cursor.execute(sql_insert, (course_code, tutor_email, content))
        connection.commit()
        log_admin_action(session['email'], 'Gave Assignment', f'Course Code: {course_code}')

        flash('Assignment added successfully!', 'success')

        return redirect(url_for('dashboard'))

    # Fetch available courses for the tutor
    sql_courses = """
    SELECT c.course_code, c.course_title 
    FROM TutorCourse tc
    JOIN Courses c ON tc.course_code = c.course_code
    WHERE tc.tutor_email = %s;
    """
    cursor.execute(sql_courses, (tutor_email,))
    courses = cursor.fetchall()

   
    return render_template('add_assignment.html', courses=courses)

# Students See Course Content
@app.route('/student/assignments/', methods=['GET'])
def view_posts():
    if 'loggedin' in session:
        student_id = session['STUDENT_ID']

        # Fetch the student's enrolled course (only one)
        sql_course = """
        SELECT COURSE FROM Students WHERE STUDENT_ID = %s;
        """
        cursor.execute(sql_course, (student_id,))
        course = cursor.fetchone()
        course = course['COURSE']
        course_code_sql = '''SELECT course_code from Courses where course_title = %s'''
        cursor.execute(course_code_sql, (course,))
        course_code = cursor.fetchone()
        course_code = course_code['course_code']
        

        # Fetch posts related to the enrolled course
        sql_posts = """
            SELECT Posts.content, Posts.date_posted, Admins.FIRST_NAME, Admins.LAST_NAME
            FROM Posts
            JOIN Admins ON Posts.tutor_email = Admins.EMAIL
            WHERE Posts.course_code = %s
            ORDER BY Posts.date_posted DESC
        """
        cursor.execute(sql_posts, (course_code,))
        posts = cursor.fetchall()
        
        return render_template('course_content.html', posts=posts)

    return redirect(url_for('login'))  # Redirect to login if not logged in


# Student Submit Assignment
@app.route('/student/submit_assignment/', methods=['POST', 'GET'])
def submit_assignment():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        student_id = session['STUDENT_ID']
        course_sql = """select course_code from Courses where course_title in 
        (SELECT COURSE FROM Students WHERE STUDENT_ID = %s)"""
        cursor.execute(course_sql, (student_id,))
        course = cursor.fetchone()
        # Check if an assignment file is part of the request
        if 'assignment_file' not in request.files:
            flash('No file part', 'danger')
            return redirect(url_for('submit_assignment'))

        file = request.files['assignment_file']

        # Ensure a file was selected
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(url_for('submit_assignment'))

        # Ensure the file is a PDF
        if file:
            file_name = file.filename
            file_data = file.read()

            # Get the course code from the form
            course_code = course['course_code']

            # Insert assignment into the database
            sql_insert_assignment = """
            INSERT INTO Assignments (student_id, course_code, file_name, file_data)
            VALUES (%s, %s, %s, %s);
            """
            cursor.execute(sql_insert_assignment, (student_id, course_code, file_name, file_data))
            connection.commit()

            flash('Assignment submitted successfully!', 'success')
            return redirect(url_for('view_posts'))
        else:
            flash('Only PDF files are allowed', 'danger')
            return redirect(url_for('submit_assignment'))
    
    # Render the assignment submission form when the method is GET
    return render_template('submit_assignment.html')

    
# Tutors View Assignment Submitted
@roles_required(['tutor', 'superadmin'])
@app.route('/tutor/submissions/', methods=['GET'])
def view_submissions():
    if 'loggedin' in session:
        tutor_email = session['email']

        # Fetch all submissions for the courses the tutor teaches
        sql_get_submissions = """
        SELECT Assignments.id, Students.FIRST_NAME, Students.LAST_NAME, Assignments.file_name, Assignments.date_submitted
        FROM Assignments
        JOIN Students ON Assignments.student_id = Students.STUDENT_ID
        JOIN Posts ON Assignments.course_code = Posts.course_code
        WHERE Posts.tutor_email = %s
        ORDER BY Assignments.date_submitted DESC
        """
        cursor.execute(sql_get_submissions, (tutor_email,))
        submissions = cursor.fetchall()

        return render_template('tutor_assignment.html', submissions=submissions)

    return redirect(url_for('admin_login'))

# Tutor Download Assignment
@roles_required(['tutor', 'superadmin'])
@app.route('/download_assignment/<int:assignment_id>', methods=['GET'])
def download_assignment(assignment_id):
    if 'loggedin' in session:
        # Fetch the file from the database
        sql_get_assignment = """
        SELECT file_name, file_data FROM Assignments WHERE id = %s;
        """
        cursor.execute(sql_get_assignment, (assignment_id,))
        assignment = cursor.fetchone()

        if assignment:
            file_name = assignment['file_name']
            file_data = assignment['file_data']

            # Send the file as a download response
            response = make_response(file_data)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename="{file_name}"'
            return response

    return redirect(url_for('admin_login'))

# Library
@app.route('/library/')
def library():
    # Check if user is logged in
    if 'loggedin' not in session:
        flash('You must be logged in to access the library.', 'danger')
        return redirect(url_for('login'))  # Redirect to login page if not authenticated

    # Retrieve library items from the database
    
    cursor.execute("SELECT * FROM Library")
    items = cursor.fetchall()

    return render_template('library.html', items=items)

@app.route('/admin/upload/library/', methods=['POST', 'GET'])
@roles_required('superadmin')
def upload_library_item():
    if 'loggedin' in session:
        if request.method == 'POST':
            # Handle form data
            title = request.form['title']
            description = request.form['description']
            google_drive_link = request.form['google_drive_link']
            
            if google_drive_link:
                uploaded_by = session['role'] 
                # Insert the Google Drive link instead of blob data
                cursor.execute("INSERT INTO Library (title, description, google_drive_link, uploaded_by) VALUES (%s, %s, %s, %s)",
                            (title, description, google_drive_link, uploaded_by))
                connection.commit()
                log_admin_action(session['email'], 'Added Book to Library', f'Book Title: {title}')

                flash('Library item uploaded successfully!', 'success')
            else:
                flash('Failed to upload library item. No link provided.', 'danger')

            return redirect(url_for('library'))

        # GET request: Render the upload form
        return render_template('upload_library.html')
    return redirect(url_for('admin_login'))

# Nt yet efffective
@app.route('/contact/message/', methods=['POST'])
def contact_form():
    if request.method == 'POST':
        email = request.form['email']
        message = request.form['message']

        msg = Message('New Contact Form Submission', recipients=['support@tequant.ng'])
        msg.body = f'From: {email}\n\nMessage: {message}'

        try:
            mail.send(msg)
            flash('Your message has been sent successfully!', 'success')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')

        return redirect(url_for('index'))


@app.route('/admin/logs', methods=['GET','POST'])
@roles_required('superadmin')  
def view_logs():
    if 'loggedin' in session:
        # Fetch filter values from request arguments
        admin_name = request.args.get('admin_name')
        action_type = request.args.get('action_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Pagination settings
        page = request.args.get('page', 1, type=int)  # Default page is 1
        per_page = 10  # Number of logs per page
        offset = (page - 1) * per_page

        # Start building the SQL query
        sql = """
            SELECT admin_logs.*, CONCAT(Admins.first_name, ' ', Admins.last_name) AS admin_name
            FROM admin_logs
            JOIN Admins ON admin_logs.admin_email = Admins.email
            WHERE 1=1
        """

        # Store query parameters
        params = []

        # Filter by admin name
        if admin_name:
            sql += " AND CONCAT(admins.first_name, ' ', admins.last_name) LIKE %s"
            params.append(f'%{admin_name}%')

        # Filter by action type
        if action_type:
            sql += " AND admin_logs.action LIKE %s"
            params.append(f'%{action_type}%')

        # Filter by date range
        if start_date and end_date:
            sql += " AND admin_logs.timestamp BETWEEN %s AND %s"
            params.append(start_date)
            params.append(end_date)

        # Order by the latest logs and apply pagination
        sql += " ORDER BY admin_logs.timestamp DESC LIMIT %s OFFSET %s"
        params.append(per_page)
        params.append(offset)

        # Execute the SQL query
        cursor.execute(sql, tuple(params))
        logs = cursor.fetchall()

        # Get the total number of logs for pagination purposes
        cursor.execute("SELECT COUNT(*) AS total FROM admin_logs")
        total_logs = cursor.fetchone()['total']
        total_pages = (total_logs + per_page - 1) // per_page  # Calculate total pages

    

        # Render the logs with pagination
        return render_template(
            'admin_logs.html', logs=logs, admin_name=admin_name, 
            action_type=action_type, start_date=start_date, end_date=end_date, 
            page=page, total_pages=total_pages
        )
    return redirect(url_for('admin_login'))


#Logout
@app.route('/logout/')
def logout():
   session.pop('loggedin', None)
   session.pop('email', None)
   session.pop('role', None)
   session.pop('student_ID', None)
   return redirect(url_for('index'))
   

@app.errorhandler(403)
def forbidden(error):
    return render_template("403.html")
        


@app.errorhandler(404)
def page_not_found(error):
    try:
        # Fix to have separATE error page for admin
        if session['role'] == 'admin':
            return render_template("404.html"), 404
        else:
            # To correct to general error
            return render_template("403.html"), 404
    except KeyError:
        return render_template("404.html"), 404












































































if __name__ == "__main__":
   app.run(host="0.0.0.0", port=5000, debug = True)
