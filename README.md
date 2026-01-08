## A Personal Portfolio Web Application for Data Journalism and Multimedia Storytelling

Student Number: c25072445Module: CMT120 – Fundamentals of Programming

## Project Overview
This project is a personal portfolio web application developed to showcase my work as a data journalist and multimedia storyteller. It has been created as part of the CMT120 coursework and demonstrates the practical application of web development techniques for publishing written journalism, data-driven stories, and multimedia content.
The application is built using Flask and SQLite and focuses on dynamic content management, editorial usability, and responsive presentation, reflecting common practices in digital journalism.

## Project Aims
The main aims of this project are to:
* Develop a professional digital portfolio suitable for journalism and multimedia work
* Implement a database-driven approach to content management
* Support multiple storytelling formats, including written and multimedia content
* Apply backend and frontend programming concepts in a real-world context

## Functionality
The application includes an administrative interface that allows content to be created, edited, and removed without directly modifying the source code. Written content is organised within a searchable archive that can be filtered by year and category. These filters are implemented using AJAX, allowing content to update dynamically without reloading the page.
Multimedia entries support external platforms such as YouTube, with thumbnails automatically generated using pattern-matching logic. The administrative forms adapt based on content type, simplifying content entry and reducing user error.
A contact form is implemented using asynchronous requests, providing real-time feedback to users and persisting submissions to the database. Access to administrative routes is protected using session-based authentication.

## Technologies Used
* Backend: Python 3, Flask
* Database: SQLite3
* Frontend: HTML5, CSS3, JavaScript (ES6)
* Deployment: Gunicorn with container support

## Project Structure

.
├── main.py                # Application logic, routing, and database handling
├── templates/             # Jinja2 templates for page rendering
├── static/
│   ├── css/style.css      # Editorial styling and responsive layout
│   └── js/main.js         # Client-side logic and AJAX functionality
├── content.db             # SQLite database (development use)

## Deployment Notes
The application is configured for deployment on Platform-as-a-Service and container-based environments. Dependencies are managed using requirements.txt, the Python version is pinned via runtime.txt, and the application listens on the environment-provided PORT variable to ensure compatibility with OpenShift.
Gunicorn is used as the production WSGI server:

gunicorn main:app

## Limitations
For production use, the local SQLite database and uploaded assets should not be committed to version control. A managed database and persistent storage solution would be more appropriate for larger-scale deployment.
This project demonstrates the use of database-driven web development, asynchronous client-server communication, authentication, and deployment configuration in support of data journalism and multimedia storytelling. It was developed to meet the requirements of the CMT120 coursework while reflecting practical workflows used in digital media production.
