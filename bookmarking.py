from flask import Flask
from flask import json
from flask import request
import sqlite3

app = Flask(__name__)

ok_code, created_code, no_content_code, bad_request_code, not_found_code, internal_server_error_code = 200, 201, 204, 400, 404, 500

msg_user_already_exists = 'User already exists'
msg_malfunction_attri_exists = 'Malfunction key exists'
msg_user_not_found = 'User not found'

db_file = 'bookmarks.db'


class BadRequestException(Exception):
    """Bad Request"""
    pass


class MalfunctionException(Exception):
    """Malfunction Exception"""
    pass


def response(data, status_code):
    r = app.response_class(
        response=json.dumps(data, sort_keys=False),
        status=int(status_code),
        mimetype='application/json'
    )
    return r


def create_connection(db_filename):
    conn = None
    try:
        conn = sqlite3.connect(db_filename)
    except sqlite3.Error as e:
        print(e)
    return conn


@app.errorhandler(500)
def internal_server_error(e):
    return "<h1>500</h1><p>Internal server error</p>", 500


# show all users
@app.route('/bookmarking/users', methods=['GET'])
def users_index():
    # response body
    # All users(ID, name) in JSON(Sorted by ascending user ID(s))
    conn = create_connection(db_file)

    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute('SELECT * FROM users;')
    rows = cur.fetchall()

    all_users = []
    for row in rows:
        all_users.append(dict(row))

    users_count = len(rows)

    return response({'count': users_count, 'users': all_users}, created_code)


# create user
@app.route('/bookmarking/<user_id>', methods=['POST'])
def users_create(user_id):
    # TODO: cross out the user_id
    if request.method == 'POST':
        try:
            # If more than two attr
            if len(request.get_json()) is not 2:
                raise MalfunctionException

            uid = request.json['user_id']

            # If the user_id in URI does not match with the user_id in json
            if str(uid) != str(user_id):
                raise MalfunctionException

            user_name = request.json['user_name']

        except MalfunctionException as err:
            # malfunction key attr
            # msg = [{'message': msg_user_already_exists}]
            # return response({'reason': msg}, internal_server_error_code)
            return internal_server_error(internal_server_error_code)

        conn = create_connection(db_file)
        cur = conn.cursor()

        try:
            cur.execute('INSERT INTO users VALUES (?, ?);', (uid, user_name))
        except sqlite3.IntegrityError:
            msg = [{'message': msg_user_already_exists}]
            return response({'reason': msg}, bad_request_code)

        conn.commit()
        conn.close()

        return response({'status': created_code}, created_code)


# delete user
@app.route('/bookmarking/<user_id>', methods=['DELETE'])
def users_delete(user_id):
    conn = create_connection(db_file)
    cur = conn.cursor()

    cur.execute('DELETE FROM users WHERE user_id=?', (user_id,))

    conn.commit()
    conn.close()

    if cur.rowcount is 1:
        return response({'status': no_content_code}, no_content_code)
    elif cur.rowcount is 0:
        msg = [{'message': msg_user_not_found}]
        return response({'reason': msg}, not_found_code)


# bookmark crud
# bookmark index
@app.route('/bookmarking/bookmarks', methods=['GET'])
def bookmarks_index():
    data_key = {}
    accepted_key = ['tags', 'count', 'offset']

    # TODO: check to see if the offset can be started from 1
    tags = request.args.get('tags')
    count = request.args.get('count')
    offset = request.args.get('offset')

    try:
        for temp_key in list(request.args):
            if temp_key not in accepted_key:
                raise MalfunctionException
    except MalfunctionException as err:
        # return response({'status': bad_request_code}, bad_request_code)
        return internal_server_error(internal_server_error_code)

    conn = create_connection(db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    sql = "SELECT * FROM bookmarks"

    tuple_value = ()

    if tags:
        tags = str(tags).split(",")
        if len(tags) > 1:
            first = True
            for temp_tag in tags:
                if first:
                    tuple_value = tuple_value + ("%" + str(temp_tag) + "%",)
                    sql = sql + " WHERE tags LIKE ?"
                    first = False
                else:
                    tuple_value = tuple_value + ("%" + str(temp_tag) + "%",)
                    sql = sql + " AND tags LIKE ?"
        else:
            tuple_value = tuple_value + ("%" + str(tags[0]) + "%",)
            sql = sql + " WHERE tags LIKE ?"

    sql = sql + " ORDER BY url ASC, user_id ASC"

    if count:
        tuple_value = tuple_value + (count,)
        sql = sql + ' LIMIT ?'

    if offset:
        tuple_value = tuple_value + (offset,)
        sql = sql + ' OFFSET ?'

    print(sql)

    cur.execute(sql, tuple_value)
    rows = cur.fetchall()

    conn.close()

    result = []

    for row in rows:
        result.append(dict(row))

    row_count = len(rows)

    return response({'count': row_count, 'bookmarks': result}, ok_code)


@app.route('/bookmarking/bookmarks/<user_id>', methods=['GET'])
def bookmarks_show(user_id):
    # TODO: check the user_id first, if there is no user_id return 404
    conn = create_connection(db_file)
    cur = conn.cursor()

    cur.execute('SELECT * FROM users WHERE user_id=?', (user_id,))

    conn.commit()
    conn.close()

    if cur.rowcount is 0:
        msg = [{'message': msg_user_not_found}]
        return response({'reason': msg}, not_found_code)

    accepted_key = ['tag', 'count', 'offset']

    # TODO: check to see if the offset can be started from 1
    tag = request.args.get('tag')
    count = request.args.get('count')
    offset = int(request.args.get('offset')) - 1

    try:
        for x in list(request.args):
            if x not in accepted_key:
                raise MalfunctionException
    except MalfunctionException as err:
        # return response({'status': bad_request_code}, bad_request_code)
        return internal_server_error(internal_server_error_code)

    conn = create_connection(db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    sql = "SELECT * FROM bookmarks"

    tuple_value = ()

    tuple_value = tuple_value + ("'" + str(user_id) + "'",)
    sql = sql + "WHERE user_id = ?"

    if tag:
        tags = str(tag).split(",")
        for x in tags:
            tuple_value = tuple_value + ("%" + str(x) + "%",)
            sql = sql + "AND tags LIKE ?"

    sql = sql + " ORDER BY url ASC"

    if count:
        tuple_value = tuple_value + (count,)
        sql = sql + ' LIMIT ?'

    if offset:
        tuple_value = tuple_value + (offset,)
        sql = sql + ' OFFSET ?'

    if tag:
        tuple_value = tuple_value + ("%" + str(tag) + "%",)

    cur.execute(sql, tuple_value)
    rows = cur.fetchall()

    conn.close()

    result = []

    for row in rows:
        result.append(dict(row))

    row_count = len(rows)

    if row_count:
        return response({'count': row_count, 'bookmarks': result}, ok_code)
    else:
        return response({}, )


@app.route('/bookmarking/bookmarks/<user_id>/<bookmark_url>', methods=['GET'])
def bookmarks_show_url(user_id, bookmark_url):
    # TODO: show the bookmarks by the user_id and the bookmark_urls function
    pass


@app.route('/bookmarking/<user_id>/bookmarks', methods=['POST'])
def bookmarks_create(user_id):
    # TODO: create bookmarks by user_id function
    pass


@app.route('/bookmarking/<user_id>/bookmarks/<bookmark_url>', methods=['PUT'])
def bookmarks_update(user_id, bookmark_url):
    # TODO: update bookmark by user_id and url function
    pass


@app.route('/bookmarking/<user_id>/bookmarks/<bookmark_url>', methods=['DELETE'])
def bookmarks_delete(user_id, bookmark_url):
    # TODO: delete bookmark by user_id and url function
    pass


if __name__ == '__main__':
    app.run(debug=True)
