from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash,Response
from datetime import timedelta
# from flask_mail import *
import hashlib    #To change to one for flask hashing
import random
import re
from mysql.connector import OperationalError
import datetime
from datetime import datetime
import pymysql
import requests
from flask_caching import Cache
from config import Config
import os
# Cloudinary to store the uploaded blog images
from cloudinary.uploader import upload
from cloudinary.utils import cloudinary_url

app = Flask(__name__)

app.config.from_object(Config)


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
            session['role'] = 'admin'
            return redirect(url_for('dashboard'))
        else:
            msg = 'Invalid Email Address / Password!!'
            flash(msg, 'error')
    return render_template('login.html')

# Create Admin 
@app.route("/admin/create/", methods = ["GET", "POST"])
def create_admin():
    if 'loggedin' in session:
        if session['role'] == 'admin':
            if request.method == 'POST' and 'first_name'in request.form and 'last_name' in request.form and 'password' in request.form and 'email'  in request.form :
                first_name = request.form['first_name'].upper()
                last_name = request.form['last_name'].upper()
                email = request.form['email']
                _password = request.form['password']
                _password = str(_password)
                password = hashlib.sha256(_password.encode()).hexdigest()
                cursor.execute("SELECT * from Admins WHERE EMAIL = '%s'"%email)
                new_user = cursor.fetchone()
                if new_user:
                    msg = 'Account already exists !'
                    flash(msg, 'error')
                    return render_template('create_admin.html', msg = msg)
                    
                # elif not re.match( r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.tequant\.ng$', email):
                #     msg = 'Invalid email address !'
                else:
                    sql = """INSERT INTO Admins(FIRST_NAME, LAST_NAME, EMAIL, PASSWORD_) VALUES(%s, %s, %s, %s)"""
                    vals = (first_name, last_name, email, password)
                    cursor.execute(sql, vals)
                    connection.commit()
                    # connection.close()
                    msg = 'Posted successfully !!'
                    flash(msg, 'success')
                return redirect(url_for('dashboard'))
            return render_template('create_admin.html')
        else:
            return render_template('403.html')
    msg = 'Session TimeOut'
    flash(msg, 'warning')
    return redirect(url_for('admin_login', next = '/admin/create/' ))
    
# Admin Dashboard
@app.route('/admin/')
def dashboard():
    if 'loggedin' in session:
        if session['role'] == 'admin':
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
        else:
            return render_template('403.html')
    return redirect(url_for('admin_login', next= "url_for('dashboard')"))

# Add Blog Post
@app.route("/admin/blog/add/", methods=["GET", "POST"])
def add_blog():
    if 'loggedin' in session:
        if session['role'] == 'admin':
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
        else:
            return render_template('403.html')

    msg = 'Session Timeout'
    flash(msg, 'warning')
    return redirect(url_for('admin_login', next='/admin/blog/add/'))

# Edit Blog Post
@app.route("/admin/blog/<blog_link>/edit/", methods =['GET', 'POST'])
def edit_blog(blog_link):
    if 'loggedin' in session:
        if session['role'] == 'admin':
            sql_select = "select * from Blog where blog_link = '%s'"%blog_link
            cursor.execute(sql_select)
            record = cursor.fetchall()
            return render_template('edit_blog.html', record = record)
        else:
            return render_template('403.html')
    return redirect(url_for('admin_login'))

# Save Changes to Blog Post
@app.route('/admin/blog/update/', methods = ['GET', 'POST'])
def save_blog():
    if 'loggedin' in session:
        if session['role'] == 'admin':
            if request.method == 'POST' and 'title' in request.form and 'body' in request.form and 'category' in request.form:
                title = request.form['title']
                blog_link = title.lower().replace(' ', '-')
                body = request.form['body']
                category = request.form['category'].title()
                author = request.form['author']
                sql = """UPDATE Blog SET Title = %s, Body = %s, Category = %s, Author = %s WHERE Blog_Link = %s"""
                vals = (title, body, category, author, blog_link)
                cursor.execute(sql, vals)
                connection.commit()
                # connection.close()
                msg = 'You have successfully updated Blog Post'
                flash(msg, 'success')
            return redirect(url_for('blog_view'))
        else:
            return render_template('403.html')
    return redirect(url_for('admin_login'))

# View blog in Admin Panel
@app.route("/admin/blog/<blog_link>/", methods=['GET', 'POST'])
def read_blog(blog_link):
    if 'loggedin' in session:
        if session['role'] == 'admin':
            sql = "SELECT * FROM Blog WHERE blog_link = %s"
            cursor.execute(sql, (blog_link,))
            blog = cursor.fetchone()
            return render_template('read_blog.html', blog=blog)
        else:
            return render_template('403.html')
    return redirect(url_for('admin_login'))


# View All Blogs
@app.route("/admin/blog/all/", methods = ["GET", "POST"])
def blog_view():
    if 'loggedin' in session:
        if session['role'] == 'admin':
            sql_select = "SELECT * FROM Blog"
            cursor.execute(sql_select)
            record = cursor.fetchall()
            return render_template("blog_view.html", record = record)
        else:
            return render_template('403.html')
    return redirect(url_for('admin_login', next= "/admin/blog/all/"))

# Delete Blog
@app.route('/admin/blog/<blog_link>/delete/', methods = ['GET', 'POST'])
def delete_blog(blog_link):
    if 'loggedin' in session:
        if session['role'] == 'admin':
            if request.method == 'POST' and 'confirm' in request.form:
                confirm = request.form['confirm']
                if confirm == 'YES':
                    sql_ = "select image_url from Blog where blog_link = '%s'" %blog_link
                    cursor.execute(sql_)
                    image_url = cursor.fetchone()
                    public_id = "/".join(image_url.split('/')[-2:])[:-4]
                    result = cloudinary.uploader.destroy(public_id)
                    sql = "DELETE from Blog WHERE blog_link = '%s'" %blog_link
                    cursor.execute(sql)
                    connection.commit()
                    msg = 'You have successfully deleted Blog Post'
                    flash(msg, 'success')
                    return redirect(url_for('blog_view'))
            return render_template('delete_blog.html', blog_link = blog_link)
        else:
            return render_template('403.html')
    return redirect(url_for('admin_login'))

# Add videos site
# Add Video Post
@app.route("/admin/video/add/", methods = ["GET", "POST"])
def add_video():
    if 'loggedin' in session:
        if session['role'] == 'admin':
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
        else:
            return render_template('403.html')
    msg = 'Session TimeOut'
    flash(msg, 'warning')
    return redirect(url_for('admin_login', next = '/admin/video/add/' ))

# All Videos
@app.route("/admin/video/all/", methods = ["GET", "POST"])
def video_view():
    if 'loggedin' in session:
        if session['role'] == 'admin':
            sql_select = 'SELECT * FROM Videos' 
            cursor.execute(sql_select)
            record = cursor.fetchall()
            return render_template("all_videos.html", record = record)
        else:
            return render_template('403.html')
    return redirect(url_for('admin_login', next= "/admin/video/all/"))

# Delete Video
@app.route('/admin/video/<link>/delete/', methods = ['GET', 'POST'])
def delete_video(link):
    if 'loggedin' in session:
        if session['role'] == 'admin':
            if request.method == 'POST' and request.json.get('confirm') == 'YES':
                sql = "DELETE FROM Videos WHERE Link = %s"%link
                cursor.execute(sql)
                connection.commit()
                connection.close()
                return jsonify({'status': 'success', 'message': 'Video deleted successfully'}), 200
            else:
                return jsonify({'status': 'error', 'message': 'Deletion not confirmed'}), 400
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    return jsonify({'status': 'error', 'message': 'Not logged in'}), 401

@app.route("/admin/student/create/", methods = ["GET", "POST"])
def create_student():
    if 'loggedin' in session:
        if session['role'] == 'admin':
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
                cursor.execute("SELECT * from Students WHERE Student_ID = '%s'"%STUDENT_ID)
                new_user = cursor.fetchone()
                if new_user:
                    msg = 'Student already exists !'
                    flash(msg, 'error')
                    return render_template('create_student.html', msg = msg)
                else:
                    sql = """INSERT INTO Students(FIRST_NAME, LAST_NAME, EMAIL, PASSWORD_, Student_ID, Date_Registered) VALUES(%s, %s, %s, %s, %s, %s)"""
                    vals = (first_name, last_name, email, password, STUDENT_ID, date_registered)
                    cursor.execute(sql, vals)
                    connection.commit()
                    msg = 'Added successfully !!'
                    flash(msg, 'success')
                return redirect(url_for('all_students'))
            return render_template('create_student.html', courses = courses)
        else:
            return render_template('403.html')
    msg = 'Session TimeOut'
    flash(msg, 'warning')
    return redirect(url_for('admin_login', next = '/admin/student/create/' ))

# View All Students
@app.route("/admin/student/all/", methods = ["GET", "POST"])
def all_students():
    if 'loggedin' in session:
        if session['role'] == 'admin':
            sql_select = "SELECT * FROM Students;"
            cursor.execute(sql_select)
            record = cursor.fetchall()
            return render_template("all_students.html", record = record)
        else:
            return render_template('403.html')
    return redirect(url_for('admin_login', next= "/admin/student/all/"))

# To add courses
@app.route('/admin/course/add/', methods=["GET", "POST"])
def add_course():
    if 'loggedin' in session:
        if session['role'] == 'admin':
            if request.method == 'POST' and 'course_code' in request.form and 'course_title' in request.form:
                course_code = request.form['course_code']
                course_title = request.form['course_title']
                course_description = request.form['course_description']
                course_curriculum = request.form['course_curriculum']
                
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
                    sql = """INSERT INTO Courses (course_title, course_code, course_description, course_curriculum) 
                             VALUES (%s, %s, %s, %s)"""
                    vals = (course_title, course_code, course_description, course_curriculum)
                    cursor.execute(sql, vals)
                    connection.commit()
                    
                    msg = 'Course added successfully !!'
                    flash(msg, 'success')
                    return redirect(url_for('courses'))
            return render_template('add_course.html')
        else:
            return render_template('403.html')
    
    msg = 'Session TimeOut'
    flash(msg, 'warning')
    return redirect(url_for('admin_login', next='/admin/course/add/'))

@app.route('/admin/course/all/', methods = ["GET", "POST"])
def courses():
    if 'loggedin' in session:
        if session['role'] == 'admin':
            sql_select = 'SELECT * FROM Courses' 
            cursor.execute(sql_select)
            record = cursor.fetchall()
            return render_template("courses.html", record = record)
        else:
            return render_template('403.html')
    return redirect(url_for('admin_login', next= "/admin/course/all/"))

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
        return redirect(url_for('home'))
            
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
        return redirect(url_for('home'))


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
def prospective_students():
    if 'loggedin' in session and session['role'] == 'admin':
        sql = "SELECT * FROM prospective_students"
        cursor.execute(sql)
        students = cursor.fetchall()
        return render_template('prospective_students.html', students=students)
    else:
        return render_template('403.html')







#Logout
@app.route('/logout/')
def logout():
   session.pop('loggedin', None)
   session.pop('email', None)
   session.pop('student_ID', None)
   return redirect(url_for('index'))
   

@app.errorhandler(403)
def forbidden(error):
    return render_template("403.html")
        
@app.errorhandler(500)
def forbidden(error):
    return render_template("403.html")

@app.errorhandler(404)
def page_not_found(error):
    try:
        if session['role'] == 'admin':
            return render_template("404.html"), 404
        else:
            # To correct to general error
            return render_template("403.html"), 404
    except KeyError:
        return render_template("404.html"), 404


@app.errorhandler(OperationalError)
def handle_db_error(e):
    app.logger.error(f"Database OperationalError: {str(e)}")
    return render_template('db_error.html'), 500












































# Student Stuff

# For Student Login
@app.route("/login/", methods = ["GET", "POST"])
def login():
    pass






































if __name__ == "__main__":
   app.run(host="0.0.0.0", port=5000, debug=True)
