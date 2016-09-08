from flask import Flask, render_template, request, make_response, redirect, \
        url_for, flash, jsonify, send_from_directory
from flask_babel import Babel
from werkzeug.utils import secure_filename
from functools import wraps
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker, relationship
from database_series import Series, Volume, Base, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import os
import requests
app = Flask(__name__, static_folder='static')

# Connect to Database and create database session
engine = create_engine('sqlite:///bookcatalogue2.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

# Directory for the uploaded file
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# client_id for the connection through Google
CLIENT_ID = json.loads(open(
    'client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = 'CatalogueApp'

# DECORATORS
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' in login_session:
            return f(*args, **kwargs)
        else:
            flash('You are not allowed to access this page')
            return redirect(url_for('showLogin', next=request.url))
    return decorated_function
# TUTOR suggestion #######################
# def owner_required(f):
#     """Function decorator.
#     Requires to be the owner of an item before modyfing it.
#     """
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         # Since I'm using this decorator both for styles and models, I need
#         # to differentiate between both.
#         style_id = kwargs['style_id']
#         if 'model_id' in kwargs:
#             model_id = kwargs['model_id']
#             target = session.query(Model).filter_by(id=model_id).one()
#             return_target = url_for('showModels', style_id=style_id)
#         else:
#             target = session.query(Style).filter_by(id=style_id).one()
#             return_target = url_for('showStyles')

#         if target.user_id != login_session['user_id']:
#             flash(
#                 "You are not allowed to perform this operation because " +
#                 "you don't own the item",
#                 'alert-danger')
#             return redirect(return_target)
#             url_for('showModels', style_id=style_id)
#         else:
#             return f(*args, **kwargs)
#     return decorated_function


# L O G I N
@app.route('/login')
def showLogin():
    '''
    Create a state token that will be later used in connecting through g+ e fb
    '''
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    '''
    Connect a user to the app using Facebook login details
    '''
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print("access token received %s ") % access_token

    app_id = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.4/me"
    # strip expire tag from access token
    token = result.split("&")[0]

    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly
    # logout, let's strip out the information before the equals sign
    # in our token
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    picture = requests.get(login_session['picture'])
    with open('static/' + str(login_session['user_id']) +
              '_image.jpg', 'wb') as f:
        f.write(picture.content)

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 200px; height: 200px; border-radius: 50%;-webkit-border-radius: 50%;-moz-border-radius: 50%;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    '''
    Disconnect a facebook user. Revoke a current user's token and reset
    their login_session
    '''
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s'\
          % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    # login_session.clear()
    return "you have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    '''
    Connect a user to the app using Google+ login details
    '''
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    # request.get_data()
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    response = h.request(url, 'GET')[1]
    str_response = response.decode('utf-8')
    result = json.loads(str_response)
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print ("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
            'Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token
    # login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()
    login_session['provider'] = 'google'

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # user_id = getUserID(login_session['email'])
    user_id = getUserID(data["email"])  
    if not user_id:
        user_id = createUser(login_session)
    #login_session['user_id']
    login_session['user_id'] = user_id
    picture = requests.get(login_session['picture'])
    with open('static/' + str(login_session['user_id']) + '_image.jpg', 'wb') as f:
        f.write(picture.content)
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 200px; height: 200px; border-radius: 50%;-webkit-border-radius: 50%;-moz-border-radius: 50%;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print ("done!")
    return output


@app.route('/gdisconnect')
def gdisconnect():
    '''
    Revoke a current google user's token and reset their login_session
    '''
    #access_token = login_session['access_token']
    access_token = login_session['credentials']
    print ('In gdisconnect access token is %s', access_token)
    print ('User name is: ' )
    print (login_session['username'])
    if access_token is None:
        print ('Access Token is None')
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print ('result is ')
    print (result)
    if result['status'] == '200':
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/disconnect')
def disconnect():
    '''
    Disconnect based on provider and clear the session in case a user
    restart the browser and the cookies are still there
    '''
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
        if login_session['provider'] == 'facebook':
            fbdisconnect()
        login_session.clear()
        flash("You have successfully been logged out.")
        return redirect(url_for('showSeries'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showSeries'))


# JSON endpoints
@app.route('/series/JSON')
@login_required
def showSeriesJSON():
    '''
    List all series in JSON format
    '''
    items = session.query(Series).order_by(Series.name).all()
    return jsonify(series= [i.serialize for i in items])

@app.route('/series/<int:series_id>/titles/JSON')
@login_required
def showTitlesJSON(series_id):
    '''
    List all titles of a certain series in JSON format
    '''
    series = session.query(Series).filter_by(id=series_id).one()
    items = session.query(Volume).filter_by(series_id=series.id).all()
    return jsonify(titles=[i.serialize for i in items])

@app.route('/series/<int:series_id>/titles/<int:title_id>/JSON')
@login_required
def showTitleJSON(series_id, title_id):
    '''
    Show the details of a single title in JSON format
    '''
    item = session.query(Volume).filter_by(id=title_id).one()
    return jsonify(item.serialize)

# CRUD functions

@app.route('/')
@app.route('/series/')
def showSeries():
    '''
    Render the templates with all series
    '''
    items = session.query(Series).order_by(Series.name).all()
    if 'username' not in login_session:
        return render_template("publicseries.html", series = items)
    else:
        return render_template("series.html", series = items)

@app.route('/series/new/', methods = ['GET', 'POST'])
@login_required
def newSeries():
    '''
    If you are logged in you can add a new series to the catalogue
    '''
    creator = getUserInfo(login_session['user_id'])
    if request.method == 'POST':
        newItem = Series(name=request.form['name'], 
            director=request.form['director'], 
            description=request.form['description'], 
            user_id = login_session['user_id'])
        session.add(newItem)
        session.commit()
        flash("new series added!")
        return redirect(url_for('showSeries'))
    else:
        return render_template("newseries.html", creator=creator)
    

@app.route('/series/<int:series_id>/edit/', methods = ['GET', 'POST'])
@login_required
def editSeries(series_id):
    '''
    If you are the owner of a series you can edit the details
    '''
    editedItem = session.query(Series).filter_by(id=series_id).one()
    if editedItem.user_id != login_session['user_id']:
        flash("You are not authorized to edit this series")
        return redirect(url_for('showSeries'))
    creator = getUserInfo(editedItem.user_id)
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['director']:
            editedItem.director = request.form['director']
        session.add(editedItem)
        session.commit()
        flash("A series has been edited!")
        return redirect(url_for('showSeries'))
    else:
        return render_template('editseries.html', creator=creator, 
            series_id=editedItem.id, item = editedItem)


@app.route('/series/<int:series_id>/delete/', methods = ['GET', 'POST'])
@login_required
def deleteSeries(series_id):
    '''
    If you are the owner of a series you can delete it
    '''
    # if 'username' not in login_session:
    #     return redirect(url_for('showLogin'))
    items = session.query(Series).order_by(Series.name).all()
    itemToDelete = session.query(Series).filter_by(id=series_id).one()
    if itemToDelete.user_id != login_session['user_id']:
        flash("You are not authorized to delete this series")
        return redirect(url_for('showSeries'))
    creator = getUserInfo(itemToDelete.user_id)
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash("A series has been deleted!")
        return redirect(url_for('showSeries'))
    else:
        return render_template("deleteseries.html", 
            creator=creator, series_id = itemToDelete.id, series=itemToDelete)


@app.route('/series/<int:series_id>/')
@app.route('/series/<int:series_id>/titles/')
def showTitles(series_id):
    '''
    Show all the titles of a series.
    If you are the owner of the series you can proceed to edit or delete the titles
    '''
    series = session.query(Series).filter_by(id=series_id).one()
    creator = getUserInfo(series.user_id)
    items = session.query(Volume).filter_by(series_id=series.id).all()
    if 'username' not in login_session:
        return render_template('publictitles.html', items=items, 
            series_id=series.id, series=series, creator=creator)
    else:
        return render_template('titles.html', series_id=series.id, items=items, 
            series = series, creator=creator)


@app.route('/series/<int:series_id>/titles/')
@app.route('/series/<int:series_id>/titles/<int:title_id>/')
def viewTitle(series_id, title_id):
    '''
    Show all the details of a title
    '''
    series = session.query(Series).filter_by(id=series_id).one()
    item = session.query(Volume).filter_by(id=title_id).one()
    creator = getUserInfo(item.user_id)
    
    return render_template('viewtitle.html', title_id = item.id,  
        item = item, series_id=series.id, series = series, creator=creator)


@app.route('/series/<int:series_id>/titles/new/', methods=['GET', 'POST'])
@login_required
def newTitle(series_id):
    '''
    If you are the owner of the series you can add a new title
    '''
    series = session.query(Series).filter_by(id=series_id).one()
    items = session.query(Volume).filter_by(series_id=series.id).all()
    creator = getUserInfo(series.user_id)
    if creator.id != login_session['user_id']:
        flash("You are not authorized to add a new title to this series")
        return render_template('publictitles.html', items=items,
                               series_id=series.id, series=series, creator=creator)
    if request.method == 'POST':
        newItem = Volume(title=request.form['title'], 
            author=request.form['author'], 
            description=request.form['description'], 
            price=request.form['price'], 
            topic = request.form['topic'], 
            series_id=series_id, 
            user_id=login_session['user_id'])
        if request.files['picture_file']:
            filename = upload_file(series_id)
            savedFile = str(filename)
            newItem.cover = savedFile
        session.add(newItem)
        session.commit()
        flash("New volume added!")
        return redirect(url_for('showTitles', series_id=newItem.series_id, 
            creator=creator))
    else:
        return render_template("newtitle.html", series = series, 
            series_id= series.id, creator=creator)
    

@app.route('/series/<int:series_id>/titles/<int:title_id>/edit/', 
            methods = ['GET', 'POST'])
@login_required
def editTitle(series_id, title_id):
    '''
    If you are the owner of the series you can edit a title
    '''
    editedItem = session.query(Volume).filter_by(id=title_id).one()
    series = session.query(Series).filter_by(id=series_id).one()
    creator = getUserInfo(editedItem.user_id)
    if creator.id != login_session['user_id']:
        flash("You are not authorized to edit this title")
        return render_template('viewtitle.html', title_id = editedItem.id,  
            item = editedItem, series_id=series.id, series = series, 
            creator=creator)
    if request.method == 'POST':
        if request.form['title']:
            editedItem.title = request.form['title']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['author']:
            editedItem.author = request.form['author']
        if request.form['price']:
            editedItem.price = request.form['price']
        if request.form['topic']:
            editedItem.course = request.form['topic']
        if request.files['picture_file']:
            filename = upload_file(series_id)
            savedFile = str(filename)
            editedItem.cover = savedFile
        session.add(editedItem)
        session.commit()
        flash("A volume has been edited!")
        return redirect(url_for('showTitles', series_id=editedItem.series_id))
    else:
        return render_template("edittitle.html", series_id = series_id, 
            title_id = title_id, item=editedItem, creator=creator)
    

@app.route('/series/<int:series_id>/titles/<int:title_id>/delete/', 
            methods = ['GET', 'POST'])
@login_required
def deleteTitle(series_id, title_id):
    '''
    If you are the owner of the series you can delete a title
    '''
    # if 'username' not in login_session:
    #     return redirect(url_for('showLogin'))
    itemToDelete = session.query(Volume).filter_by(id=title_id).one()
    creator = getUserInfo(itemToDelete.user_id)
    if creator.id != login_session['user_id']:
        flash("You are not authorized to delete this title")
        return redirect(url_for('showTitles', series_id=series_id, creator=creator))
    if request.method == 'POST':
        deleteCover = itemToDelete.cover
        session.delete(itemToDelete)
        session.commit()
        if deleteCover:
            f = os.path.join(app.config['UPLOAD_FOLDER'],
                             str(series_id), deleteCover)
            if os.path.exists(f):
                os.remove(f)
        flash("A volume has been deleted")
        return redirect(url_for('showTitles', 
            series_id=series_id, creator=creator))
    else:
        return render_template('deletetitle.html', 
            item=itemToDelete, series_id=itemToDelete.series_id,
                               title_id=itemToDelete.id, creator=creator)


# HELPER functions 
def getUserID(email):
    try:
        user = session.query(User).filter_by(email = email).one()
        return user.id
    except:
        return None


def getUserInfo(user_id):
    user = session.query(User).filter_by(id = user_id).one()
    return user


def createUser(login_session):
    newUser = User(name = login_session['username'], 
        email = login_session['email'], 
        picture = login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email = login_session['email']).one()
    return user.id

# UPLOADING functions
def allowed_file(filename):
    '''
    Return true if filename contains one of the file extensions
    listed in ALLOWED_EXTENSIONS
    '''
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def upload_file(series_id):
    '''
    Save the file uploaded in a subdirectory of UPLOAD_FOLDER, called after 
    the id of the series to which the volume belongs.
    The function returns then the name of the file.  
    '''
    f = request.files['picture_file']
    if f and allowed_file(f.filename):
        filename = secure_filename(f.filename)
        directory_path = os.path.join(app.config['UPLOAD_FOLDER'], str(series_id))
        if not os.path.exists(directory_path):
            # this will check if directory_path exists and will create 
            # the path to be able to store the file.
            os.makedirs(directory_path)
        f.save(os.path.join(directory_path, filename))
    return filename


@app.route('/uploads/<int:series_id>/<path:filename>')
def uploaded_file(series_id, filename):
    if filename is not None:
        return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'],
                                                str(series_id)), filename)
    else:
        return send_from_directory(app.config['UPLOAD_FOLDER'],
               "clueb_logo1.png")

@app.route('/robots.txt')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])



# APPLICATION

#if __name__ == '__main__':
#    app.secret_key = '\xef\xc4\xe26m4\xa1;-b\x19\xad\xe2o\xac"p|\x1d:\x13\x0c\xaf\x11'
#    app.debug = True
#    app.run(host='0.0.0.0', port=5000)
