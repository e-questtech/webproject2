use defaultdb;
create database defaultdb;
CREATE TABLE Blog (
	blog_link  varchar(200) primary key,
    Title VARCHAR(254) NOT NULL,
    Body longtext CHARSET UTF16 NOT NULL,
    category VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    publish_date DATE NOT NULL
);
insert into Blog values ('tips-for-the-tesh-tipwef-vwfv2342-d', 'Title For the Furst Blog in TeQuant', 'Body l-78.558,52.367v-7.121l81.331-54.216l81.331,54.216v7.121L224.106,278.965z M262.215,123.865v16.799c0,2.761,2.239,5,5,5h0.465
                            ', 'Tech', 'Faith Dan-Elebiga' , '2024-09-25');

SELECT 
    *
FROM
    Blog;

drop table Blog;
    
   CREATE TABLE Admins (
    FIRST_NAME VARCHAR(100) NOT NULL,
    LAST_NAME VARCHAR(100) NOT NULL,
    EMAIL VARCHAR(254) NOT NULL PRIMARY KEY,
    PASSWORD_ VARCHAR(254) NOT NULL
);

insert into Admins values ('Nikson', 'Kejeh', 'nikson.kejeh@tequant.ng', '12r3f2t32tgbv3qfcvnbteugt834t');


create table Videos(
Title varchar (100) not null,
Link varchar(254) not null primary key,
upload_date DATE NOT NULL
);

insert into Videos values('JavaScript Basics',  'https://www.youtube.com/embed/W6NZfCO5SIk', '2021-12-09');
    select * from Videos;
    
create table Students( 
	STUDENT_ID VARCHAR (100) NOT NULL PRIMARY KEY,
    FIRST_NAME VARCHAR(100) NOT NULL,
    LAST_NAME VARCHAR(100) NOT NULL,
    EMAIL VARCHAR(254) NOT NULL ,
    PASSWORD_ VARCHAR(254) NOT NULL,
    Date_Registered date not null
);

insert into Students values('CS/24/011/', 'Johnny', 'Doer', 'johnnydoer@gmail.com', '12456756i5u4352rgbgcbxh63g224gui67n', '2022-12-23');
select * from Students;
-- delete from Students where STUDENT_ID  ='CS/24/001/'
select * from Courses;
-- insert into Courses values('Data Analysis', 'DTA');
insert into Courses values('CyberSecurity', 'CYB');

ALTER TABLE Blog
ADD COLUMN image_url VARCHAR(255);
select * from Courses;
-- select *  from Courses where course_code = 'MSFT';
select * from prospective_students;
alter table prospective_students add column phone_number integer(20);
-- drop database defaultdb;

-- TutorCourse Table (For Assigning Tutors to Courses)
CREATE TABLE TutorCourse (
    id INT PRIMARY KEY AUTO_INCREMENT,
    tutor_email VARCHAR(255),
    course_code VARCHAR(10),
    FOREIGN KEY (tutor_email) REFERENCES Admins(email) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (course_code) REFERENCES Courses(course_code) ON DELETE CASCADE ON UPDATE CASCADE
);

select * from TutorCourse;

CREATE TABLE Posts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    course_code VARCHAR(10),
    tutor_email VARCHAR(255),
    content TEXT,
    date_posted DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_code) REFERENCES Courses(course_code),
    FOREIGN KEY (tutor_email) REFERENCES Admins(email)
);
select * from Posts;

select course_code from Courses where course_title = (select course from Students where STUDENT_ID = 'DTS/2024/50');

CREATE TABLE Library (
       id INT PRIMARY KEY AUTO_INCREMENT,
       title VARCHAR(255),
       author VARCHAR(255),
       description TEXT,
       file_path VARCHAR(255)  -- Path to the book file from google drive
   );
   
   
   SELECT c.course_code, c.course_title 
    FROM TutorCourse tc
    JOIN Courses c ON tc.course_code = c.course_code
    WHERE tc.tutor_email = 'johnny.cage@tequant.ng';
    
    SELECT Posts.content, Posts.date_posted, Admins.FIRST_NAME, Admins.LAST_NAME
            FROM Posts
            JOIN Admins ON Posts.tutor_email = Admins.EMAIL
            WHERE Posts.course_code = 'DTS'
            ORDER BY Posts.date_posted DESC;
            
            select * from Students;
            SELECT COURSE FROM Students WHERE STUDENT_ID = 'DTS/2024/50';
            SELECT course_code from Courses where course_title = 'Data Science';


CREATE TABLE Assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT,
    course_code VARCHAR(10),
    file_name VARCHAR(255),
    file_data LONGBLOB,  -- For storing the PDF file directly
    date_submitted DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES Students(STUDENT_ID),
    FOREIGN KEY (course_code) REFERENCES Courses(course_code)
);