import os
import uuid
import http
import logging
import json
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from exceptions import ValidationException, EntityNotFoundException
from errors import http_response, api_exception_handler

app = Flask(__name__)
basedir = 'C:\\Users\\velin\\Desktop\\Projects\\Python\\newfolder'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'users.db')
app.config['SQLALCHEMY_BINDS'] = {'items': 'sqlite:///' + os.path.join(basedir, 'items.db')}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

#------------------------------------------------------------------------------
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.String(64), nullable=False)
    token = db.Column(db.String(64), nullable=True)
    titles = db.relationship('Items', backref='user')

    def __repr__(self):
        return "<User {}>".format(self.user)

#------------------------------------------------------------------------------
class Items(db.Model):
    __bind_key__= 'items'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return "<Items {}>".format(id, self.data)

#------------------------------------------------------------------------------
def token_required(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        token = request.args.get('token')
        # debug for very detailed output (for diagnostic purposes)
        logging.debug(f'Input token:{token}')
        if not token:
            raise ValidationException('Token is missing')
        user = Users.query.filter_by(token=str(token)).one_or_none()
        if not user:
            raise ValidationException('Invalid token or token expired')
        return func(*args, user_id=user.id, **kwargs)
    return decorated

#------------------------------------------------------------------------------
@app.route('/registration', methods=['POST'])
@api_exception_handler
def registration():

    payload = request.json

    # get user and password from input
    user = payload.get('user', None)
    password = payload.get('password', None)

    # validate input
    if not user or not password:
        raise ValidationException('User and/or password not specified')

    # validate input user doesn't exist already
    if Users.query.filter_by(user=user).one_or_none():
        raise ValidationException('Such user already exists')

    db.session.add(Users(user=str(user), password=str(password)))
    db.session.commit()

    return http_response(http.HTTPStatus.ACCEPTED)

#------------------------------------------------------------------------------
@app.route('/login', methods=['POST'])
@api_exception_handler
def login():

    payload = request.json

    # get user and password from input
    user = payload.get('user', None)
    password = payload.get('password', None)

    # validate input
    if not user or not password:
        raise ValidationException('User and/or password not specified')

    user = Users.query.filter_by(user=str(user)).one_or_none()
    if not user:
        raise ValidationException('Such user doesn\'t exists')

    if password != user.password:
        raise ValidationException('Password is incorrect')

    user.token = str(uuid.uuid4())
    db.session.commit()

    return http_response(http.HTTPStatus.OK, {'token': user.token})

#------------------------------------------------------------------------------
@app.route('/items', methods=['GET'])
@api_exception_handler
@token_required
def items(**kwargs):

    # page_number offset parameter is set to 0 by default
    offset = request.args.get('offset', 0)
    # page_size limit parameter is set to 10 by default
    limit = request.args.get('limit', 10)

    user_id = kwargs.get('user_id', 0)

    items = Items.query.filter_by(user_id=user_id).offset(offset).limit(limit).all()
    result = [{'id': k.id, 'data': k.data} for k in items]
    return http_response(http.HTTPStatus.OK, {'items': json.dumps(result)})

#------------------------------------------------------------------------------
@app.route('/items/<int:id>', methods=['GET', 'DELETE'])
@api_exception_handler
@token_required
def item(**kwargs):

    user_id = kwargs.get('user_id', 0)
    id = kwargs.get('id', 0)

    item = Items.query.filter_by(user_id=user_id, id=id).one_or_none()
    if not item:
        raise EntityNotFoundException('Item', id)

    if request.method == 'DELETE':
        Items.query.filter_by(user_id=user_id, id=id).delete()
        db.session.commit()
        return http_response(http.HTTPStatus.ACCEPTED)
    else:
        return http_response(http.HTTPStatus.OK, {'id':item.id, 'data': json.dumps(item.data)})

#------------------------------------------------------------------------------
@app.route('/items/new', methods=['POST'])
@api_exception_handler
@token_required
def item_new(**kwargs):

    user_id = kwargs.get('user_id', 0)
    payload = request.json

    # validate input
    data = payload.get('data', None)
    
    if not data:
        raise ValidationException('Data not specified')
    
    item = Items(user_id=str(user_id), data=json.dumps(payload))
    db.session.add(item)
    db.session.commit()

    return http_response(http.HTTPStatus.OK, {'id':item.id, 'data': json.dumps(item.data)})

#------------------------------------------------------------------------------
@app.route('/items/<int:id>/send', methods=['POST'])
@api_exception_handler
@token_required
def send_item(**kwargs):
    
    payload = request.json
    
    # validate input
    user = payload.get('user', None)
    id = payload.get('id', 0)
    
    if not user or not id:
        raise ValidationException('Receiver and/or item id not specified')
    
    receiver = Users.query.filter_by(user=user).one_or_none()
    if not receiver:
        raise EntityNotFoundException('Receiver ', user)
    
    item_id = Items.query.filter_by(id=id).one_or_none()
    if not item_id:
        raise EntityNotFoundException('Item', id)

    link = os.path.join('localhost:5000/', str(uuid.uuid4()))
    return http_response(http.HTTPStatus.OK, {'id': id, 'link': link})

#------------------------------------------------------------------------------
@app.route('/<string:token>', methods=['GET'])
@api_exception_handler
@token_required
def receive_item(**kwargs):
    
    payload = request.json
    
    id = payload.get('id', 0)
    link = payload.get('link', None)
    
    # validate input
    if not id or not link:
        raise ValidationException('Item id and/or link not specified')
    
    item_id = Items.query.filter_by(id=id).one_or_none()
    ex_owner = item_id.user_id
    
    new_owner = Users.query.filter_by(token=token).one_or_none()
    if not new_owner:
        raise ValidationException('Invalid token or token expired')
    new_owner_id = new_owner.id

    update_ownership = Items(user_id=new_owner_id )
    db.session.add(update_ownership)
    db.session.commit()
    
    return http_response(http.HTTPStatus.ACCEPTED, {'message': 'Item successfuly received'})

#------------------------------------------------------------------------------
if __name__ == '__main__':
    db.create_all()
    app.run(debug=False)