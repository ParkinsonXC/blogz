from flask import Flask, request, redirect, render_template, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import desc
from hashutils import make_pw_hash, check_pw_hash



app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://blogz:blogz@localhost:3306/blogz'
app.config['SQLALCHEMY_ECHO'] = True
#The database
db = SQLAlchemy(app)
app.secret_key = 'y337kGcys&zP3B'

class Blog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120))
    body = db.Column(db.String(250))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    pub_date = db.Column(db.DateTime)


    def __init__(self, title, body, author, pub_date=None):
        self.title = title
        self.body = body
        self.author = author
        if pub_date is None:
            # pub_date = datetime.utcnow()
            pub_date = datetime.now()
        self.pub_date = pub_date

#Create user cass
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True)
    pw_hash = db.Column(db.String(120))
    blogs = db.relationship('Blog', backref='author')

    def __init__(self, username, password):
        self.username = username
        self.pw_hash = make_pw_hash(password)


#AFTER we have created the above items, we need to use a python shell to initalize our database.
#db.drop_all()
#db.create_all()

#Filter all incoming requests here:
@app.before_request
def require_login():
    allowed_routes = ['login', 'signup', 'list_blogs', 'index']
    if request.endpoint not in allowed_routes and 'username' not in session:
        #flash('You need to be logged in to do that', 'error')
        return redirect('/login')

#Login handler function
@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        #if 'user' exists and their password matches what we have on file.....
        if user and check_pw_hash(password, user.pw_hash):
            #'remember' that the user is signed in
            session['username'] = username #Session is a dictionary so that means key/value
            flash('Logged in', 'no_error')
            return redirect('/newpost')

        elif user and user.password != password:
            flash('Password is incorrect', 'error')
            return redirect('/login')
        
        elif not user:
            flash('User does not exist', 'error')
            return redirect('/login')

    else:
        return render_template('login.html')


#Signup handler function
@app.route('/signup', methods = ['GET', 'POST'])
def signup():
    if session:
        flash('You are already logged in', 'no_error')
        return redirect('/blog')

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        verify = request.form['verify']

        username_error = ''
        password_error = ''
        verify_error = ''
        duplicate_user_error = ''

        #USERNAME CHECK
        if len(username) <= 3:
            username == ''
            username_error = "Username too short"

        elif len(username) > 20:
            username == ''
            username_error = "Username too long"
        
        elif ' ' in username:
            username == ''
            username_error = "Username cannot have a space"

        #PASSWORD CHECK
        if len(password) <= 3:
            #password = ''
            #verify = ''
            password_error = 'This password is too short'
        
        elif len(password) > 20:
            #password = ''
            #verify = ''
            password_error = 'This password is too long'
        
        elif ' ' in password:
            password_error = 'Your password cannot have a space'

        #VERIFY CHECK
        if password != verify:
            verify_error = 'Your passwords do not match'

        #EXISTING USER CHECK
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            duplicate_user_error = 'This user already exists'
        
        #SHOULD NO ERROR OCCUR:
        if not username_error and not password_error and not verify_error and not existing_user:
            new_user = User(username, password)
            db.session.add(new_user)
            db.session.commit()
            session['username'] = username
            return redirect('/newpost')
        
        #IF AN ERROR DOES OCCUR....
        else:
            return render_template('signup.html',
            username=username,
            username_error=username_error,
            password_error=password_error,
            verify_error=verify_error,
            duplicate_user_error=duplicate_user_error)



    return render_template('signup.html')


#'Home' handler. Should post views of all the authors
@app.route('/', methods = ['GET'])
def index():
    users = User.query.order_by(User.username)
    blogs = Blog.query.order_by(desc(Blog.pub_date)).all()
    last_active = {}
    for user in users:
        for blog in blogs:
            if user.id == blog.user_id:
                last_active[user.id] = blog.pub_date
                break
    return render_template('index.html', users=users, last_active=last_active)


@app.route('/blog', methods = ['GET'])
def list_blogs():
    #CHECK for query param. If not present, move onto the main blog page where they are all displayed.
    blog_id = request.args.get('id')
    user_id = request.args.get('user')

    if blog_id: #Displays a single post by a user
        blog = Blog.query.get(blog_id)
        users = User.query.all()
        return render_template('displaypost.html', blog=blog, users=users)

    elif user_id: #Displays all posts by a given user
        user = User.query.get(user_id)
        user_blogs = Blog.query.filter_by(user_id = user.id).all()
        return render_template('singleUser.html', blogs=user_blogs, user=user)

    else:
        blogs = Blog.query.order_by(desc(Blog.pub_date)).all()
        users = User.query.all()
        return render_template('blogs.html', blogs=blogs, users=users)


@app.route('/newpost', methods = ['GET'])
def display_newpost_form():
    return render_template('newpost.html')

@app.route('/newpost', methods = ['POST'])
def add_blog():
    #Grab specific owner to add this blog post to...
    author = User.query.filter_by(username=session['username']).first()

    blog_title = request.form['title']
    blog_body = request.form['blog-body']
    #BLOG AUTHOR? THIRD PARAMETER HERE
    #SET CONDITIONALS TO CHECK IF EITHER THE TITLE OR THE POST IS LEFT EMPTY

    title_error = ""
    body_error = ""

    if len(blog_title) == 0:
        title_error = "Your blog needs a title!"

    if len(blog_body) == 0:
        body_error = "Type a post! There's nothing here yet!"

    #If not, we are good to go. Initialize the new post into the class/database, add it, then commit it.
    #After it has been committed, it will have an ID. Use that to redirect to the post itself.
    if not title_error and not body_error:
        new_post = Blog(blog_title, blog_body, author)
        db.session.add(new_post)
        db.session.commit()
        return redirect('/blog?id={}'.format(new_post.id))
               
    else:
        return render_template('newpost.html',
        title_error=title_error,
        body_error=body_error)



@app.route("/logout")
def logout():
    del session['username'] 
    #flash('Logged out', 'no_error') This doesn't work, not sure why.
    return redirect('/blog')


if __name__ == "__main__":
    app.run()