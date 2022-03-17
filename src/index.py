from flask import Flask, request, jsonify, abort
from models import *
from auth import create_user, user_login, validate_access_token
from predict import predict_s, getSkinClasses, predict_l, getLungClasses
import os
import base64

# Config
app = Flask('SDD API')
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
init_db(app)
getSkinClasses(app)
getLungClasses(app)

with app.app_context():
    FIELDS = list(
        map(lambda x: {'name': x.name, 'id': x.id}, Field.query.all()))

# check the access token


def authenticate():
    if 'Authorization' not in request.headers:
        return abort(400, 'Missing the Authorization header')

    sp = request.headers['Authorization'].split(' ')
    if len(sp) != 2:
        return abort(401, 'Invalid Authorization header')

    token = sp[1]
    payload = validate_access_token(token)

    if not payload:
        return abort(401, 'Invalid access token')

    return payload

# Endpoints
# skin


@app.post('/predict')
def predict_skin():
    authenticate()

    img = request.files.get('img')
    tp = request.form.get('type')

    if img is None:
        return abort(400, 'img is missing')
    if tp is None:
        return abort(400, 'type is missing')

    try:
        tp = int(tp)
    except Exception:
        return abort(400, f'invalid type ({tp})')

    result = None
    if tp == 0:  # skin
        result = predict_s(img)
        result = list(filter(lambda x: round(x['confidence']) > 0, result))

    if tp == 1:  # lung
        result = predict_l(img)
        result = list(filter(lambda x: round(x['confidence']) > 0, result))

    if result is None:
        return abort(400, f"type ({tp}) doesn't exist")

    response = {
        'status': True,
        'data': {
            'result': result,
        },
    }

    return jsonify(response)


@app.get('/info')
def info():
    authenticate()
    id = request.form.get('id')
    tp = request.form.get('type')

    if None in [id, tp]:
        return abort(400, 'fields missing')

    try:
        id = int(id)
        tp = int(tp)
    except Exception as e:
        print(e)
        return abort(400, 'Invalid id or type.')

    result = None
    if tp == 0:  # skin
        try:
            result = SkinDisease.query.get(id).text
        except Exception as e:
            print(e)
            return abort(500, "couldn't get the disease info")

    if tp == 1:  # lung
        try:
            result = LungDisease.query.get(id).text
        except Exception as e:
            print(e)
            return abort(500, "couldn't get the disease info")

    if result is None:
        return abort(400, f"type {tp} does't exist")

    response = {
        'status': True,
        'data': {
            'result': result,
        }
    }

    return jsonify(response)

## SIGNUP AND LOGIN START ##
# signup


@app.post('/signup')
def signup():
    email = request.form.get('email', None)
    password = request.form.get('password', None)
    full_name = request.form.get('full_name', None)

    is_doctor = request.form.get('is_doctor', 0)
    is_doctor = is_doctor == '1'  # 1 == true, 0 == false

    field_id = request.form.get('field_id', None)

    if None in [email, password, full_name]:
        return abort(400, "fields missing")

    if is_doctor and field_id is None:
        return abort(400, 'A doctor without a field')

    if is_doctor:
        try:
            field_id = int(field_id)
        except Exception:
            return abort(400, 'Invalid field id')

    if len(password) < 8:
        return abort(400, 'A password can not be shorter than 8 characters')

    if is_doctor:
        success, token, user = create_user({
            'email': email,
            'password': password,
            'full_name': full_name,
            'is_doctor': is_doctor,
            "field_id": field_id
        })
    else:
        success, token, user = create_user({
            'email': email,
            'password': password,
            'full_name': full_name
        })

    if not success:
        return abort(409, 'Failed to add the user. Make sure the email has not been used before')

    return jsonify({
        'status': True,
        'email': email,
        'token': token,
        'user': user
    })

# login


@app.post('/login')
def login():
    email = request.form.get('email', None)
    password = request.form.get('password', None)

    if None in [email, password]:
        return avort(400, "fields missing")

    success, token, user = user_login(email, password)
    if not success:
        return abort(401, 'Invalid Credentials')

    return jsonify({
        'status': True,
        'email': email,
        'token': token,
        'user': user
    })
## SIGNUP AND LOGIN END ##

# get fields


@app.get('/fields')
def get_fields():
    authenticate()
    return {
        'status': True,
        'data': {
            'fields': FIELDS
        }
    }


## POSTS AREA START ##
# create a post
@app.post('/posts')
def create_post():
    payload = authenticate()
    user_id = payload['user_id']

    title = request.form.get('title')
    desc = request.form.get('desc')
    field_id = request.form.get('field_id')
    img = request.files.get('img')

    if None in [title, desc, field_id]:
        abort(400, 'fields missing')

    try:
        field_id = int(field_id)
    except Exception:
        abort(400, 'field_id must be an integer')

    if field_id < 1 or field_id > 29:
        abort(400, 'field_id must be between 1 and 29')

    img_string = None
    if img:
        img_string = base64.b64encode(img.read()).decode()

    try:
        post = Post(
            title=title,
            desc=desc,
            field_id=field_id,
            user_id=user_id,
            img=img_string
        )
        db.session.add(post)
        db.session.commit()
    except Exception as e:
        print(str(e))
        db.session.rollback()
        abort(500, 'failed to create the post')

    return {
        'status': True,
        'post_id': post.id
    }


# get posts


@app.get('/posts')
def get_posts():
    payload = authenticate()
    is_doctor = payload['is_doctor']
    field_id = payload['field_id']

    limit = request.form.get('limit', 10)
    page = request.form.get('page', 1)

    posts = Post.query.filter(Post.field_id == field_id).limit(limit)

    pass

# get a single post


@app.get('/posts/<post_id>')
def get_post(post_id):
    pass

# create a comment


@app.post('/posts/<post_id>/comments')
def create_comment(post_id):
    pass

# get the comments of a post


@app.get('/posts/<post_id>/comments')
def get_comments(post_id):
    pass

# close a post (got an answer)


@app.post('/posts/<post_id>/end')
def end_post(post_id):
    pass
## POSTS AREA END ##


# root
@app.get('/')
def index():
    return 'The API is running'


# error handelers
@app.errorhandler(400)
def bad_request_handeler(error):
    return jsonify({
        'status': False,
        'error': error.description
    }), 200


@app.errorhandler(401)
def forbidden_handeler(error):
    return jsonify({
        'status': False,
        'error': error.description
    }), 200


@app.errorhandler(409)
def forbidden_handeler(error):
    return jsonify({
        'status': False,
        'error': error.description
    }), 200


@app.errorhandler(422)
def unprocessable_handeler(error):
    return jsonify({
        'status': False,
        'error': error.description
    }), 200


@app.errorhandler(500)
def server_error_handeler(error):
    return jsonify({
        'status': False,
        'error': error.description
    }), 200