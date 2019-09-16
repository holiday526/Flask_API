from flask import Flask
from flask import json
from flask import jsonify
from flask import Response

app = Flask(__name__)


@app.route('/')
def home():
    return 'hello world'


@app.route('/bookmarking/users', methods=['GET'])
def users_index():
    # response body
    # All users(ID, name) in JSON(Sorted by ascending user ID(s))
    users = [{'abc': 'test'}]
    response = app.response_class(
        response=json.dumps(users),
        status=200,
        mimetype='application/json'
    )
    return response


@app.route('/bookmarking/<user_id>', methods=['POST'])
def users_create(user_id):
    """
    Request Body
    new user/user's id and name in JSON format
    """
    """
    Response Body
    new user's id and name id in JSON format (if the operation is successful)
    Reason for the error (when operation is not successful)
    """
    """
    Response Code
    201 (Created)
    400 (Bad Request): One/more of the user(s)
    500 (Internal Server Error): When the input is malformed or request that may raise exceptions
    """
    #
    return


if __name__ == '__main__':
    app.run()
