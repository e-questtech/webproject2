from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash,Response
from datetime import timedelta
from flask_mail import *
import hashlib    #To change to one for flask hashing
import random
import re
# from mysql.connector import OperationalError
import datetime
from datetime import datetime
import pymysql
import requests
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
            if 'role' not in session or session['role'] not in allowed_roles:
                # Modify a custom error template for admin roles
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('admin_login'))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

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
    return render_template('all_blogs.html', blogs = blogs)

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
    if 'loggedin' in session and session['role'] == 'superadmin':
        if request.method == 'POST' and all(key in request.form for key in ['first_name', 'last_name', 'email', 'password', 'role']):
            first_name = request.form['first_name'].strip().upper()
            last_name = request.form['last_name'].strip().upper()
            email = request.form['email'].strip()
            role = request.form['role'].strip()

            # Validate the email format
            if not re.match(r'^[a-zA-Z]+\.[a-zA-Z]+@tequant\.ng$', email):
                flash('Invalid email address!', 'error')
                return render_template('create_admin.html')

            _password = request.form['password']
            password = hashlib.sha256(_password.encode()).hexdigest()

            # Check if email already exists in the database
            cursor.execute("SELECT * FROM Admins WHERE EMAIL = %s", (email,))
            if cursor.fetchone():
                flash('Account already exists!', 'error')
                return render_template('create_admin.html')

            # Insert the new admin with role
            sql = """INSERT INTO Admins(FIRST_NAME, LAST_NAME, EMAIL, PASSWORD_, ROLE) VALUES(%s, %s, %s, %s, %s)"""
            vals = (first_name, last_name, email, password, role)
            cursor.execute(sql, vals)
            connection.commit()
            flash('Posted successfully!', 'success')
            return redirect(url_for('dashboard'))
        
        return render_template('create_admin.html')
    
    flash('Session Timeout', 'warning')
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
        
        # If the form is submitted (POST method), update the blog post
        if request.method == 'POST':
            if 'title' in request.form and 'body' in request.form and 'category' in request.form and 'image' in request.form:
                title = request.form['title']
                updated_blog_link = title.lower().replace(' ', '-')  # Create new blog link from title
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
                        return render_template('edit_blog.html', record=record)

                    # Upload the image to Cloudinary
                    try:
                        upload_result = upload(image)
                        image_url = upload_result.get('secure_url')  # Get the uploaded image URL
                    except Exception as e:
                        flash(f'Image upload failed: {str(e)}', 'error')
                        return render_template('edit_blog.html', record=record)

                
                    # Update Blog
                    sql_update = """UPDATE Blog SET Title = %s, Body = %s, Category = %s, Author = %s, image_url = %s, Blog_Link = %s WHERE Blog_Link = %s"""
                    vals = (title, body, category, author, image_url, updated_blog_link, blog_link)
                    cursor.execute(sql_update, vals)
                    connection.commit()
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
                    # connection.close()
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
                    msg = 'Added successfully !!'
                    # flash(msg, 'success')
                    # msg = Message('Your Student Account at TE Quant', recipients=[email])
                    # msg.body = f"""
                    # Dear Student,

                    # Your account has been created at TE Quant.
                    
                    # Student ID: {STUDENT_ID}
                    # Password: {password}

                    # Please log in and change your password as soon as possible.

                    # Best regards,
                    # TE Quant Team
                    # """
                    # mail.send(msg)
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
        url_for('videos')
        #url_for('')
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
            connection.commit()  # Commit only after modifying data
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
@app.route('/admin/tutors')
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

    # Debugging: Check if courses were retrieved
    print(courses)  # Add this line to see if courses are being retrieved correctly

    return render_template('add_assignment.html', courses=courses)
# Students See Course Content
@app.route('/student/posts/', methods=['GET'])
def view_posts():
    if 'loggedin' in session:
        student_id = session['STUDENT_ID']  

        # Fetch the student's enrolled courses
        sql_courses = """
        SELECT course_code FROM Courses 
        WHERE course_code = (SELECT course FROM Students WHERE STUDENT_ID = %s);
        """
        cursor.execute(sql_courses, (student_id,))
        courses = cursor.fetchall()

        # Prepare a list of course codes for the IN clause
        course_codes = tuple(course['course_code'] for course in courses)

        if not course_codes:
            # Handle the case where the student is not enrolled in any courses
            return render_template('course_content.html', posts=[], message="No courses found.")

        # Fetch posts related to the enrolled courses
        sql_posts = """
            SELECT Posts.content, Posts.date_posted, Admins.FIRST_NAME, Admins.LAST_NAME
            FROM Posts
            JOIN Admins ON Posts.tutor_email = Admins.EMAIL
            WHERE Posts.course_code IN %s
            ORDER BY Posts.date_posted DESC
        """
        cursor.execute(sql_posts, (course_codes,))
        posts = cursor.fetchall()
        
        return render_template('course_content.html', posts=posts)

    return redirect(url_for('login'))  # Redirect to login if not logged in






















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
