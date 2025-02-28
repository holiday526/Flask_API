from flask import Flask
from flask import json
from flask import request
import sqlite3

app = Flask(__name__)

ok_code, created_code, no_content_code, bad_request_code, not_found_code, internal_server_error_code = 200, 201, 204, 400, 404, 500

msg_user_already_exists = 'User already exists'
msg_malfunction_attri_exists = 'Malfunction key exists'
msg_user_not_found = 'User not found'
msg_bookmark_already_exists = "Bookmark already exists"
msg_bookmark_not_found = "Bookmark not found"

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
        conn = sqlite3.connect(db_filename, timeout=1)
    except sqlite3.Error as e:
        print(e)
    return conn


def check_key(accept_key, dictionary):
    error_msg = {}
    for temp in dictionary:
        for key, value in dict(temp).items():
            if key not in accept_key:
                error_msg[key] = value
    return error_msg


def get_users():
    conn = create_connection(db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute('SELECT * FROM users ORDER BY user_id;')
    rows = cur.fetchall()

    all_users = []
    for row in rows:
        all_users.append(dict(row))

    users_count = len(rows)

    return {'count': users_count, 'users': all_users}


def get_bookmarks(user_id=None):
    conn = create_connection(db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    sql = "SELECT * FROM bookmarks"

    if user_id:
        sql = sql + " WHERE user_id = ?"

    cur.execute(sql, (user_id,))
    rows = cur.fetchall()

    conn.close()

    result = []

    for row in rows:
        result.append(dict(row))

    return {"count": len(rows), "bookmarks": result}

@app.errorhandler(500)
def internal_server_error(e):
    return "<h1>500</h1><p>Internal server error</p>", 500


# show all users
@app.route('/bookmarking/users', methods=['GET'])
def users_index():
    return response(get_users(), ok_code)


# create user
@app.route('/bookmarking', methods=['POST'])
def users_create():
    if request.method == 'POST':
        accept_key = ['user_id', 'user_name']
        try:
            if (len(request.get_json())) is not 2:
                raise MalfunctionException

            count = int(request.json['count'])

            if count == 0:
                raise MalfunctionException

            users = request.json['users']

        except MalfunctionException as err:
            return internal_server_error(internal_server_error_code)
        except Exception as err:
            return internal_server_error(internal_server_error_code)

        error_msg = []

        conn = create_connection(db_file)
        cur = conn.cursor()

        if check_key(accept_key, users):
            return internal_server_error(internal_server_error_code)

        if len(users) is not count:
            return internal_server_error(internal_server_error_code)

        added_users = []

        for user in users:
            try:
                user_id = user[accept_key[0]]  # get the user_id
                user_name = user[accept_key[1]]  # get the user_name
                same_uid = cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchall()
                if same_uid:
                    raise MalfunctionException()
                cur.execute("INSERT INTO users VALUES (?, ?);", (user_id, user_name))
                added_users.append({"user_id": user_id, "user_name": user_name})
            except MalfunctionException:
                error_msg.append({'message': msg_user_already_exists})

        if not error_msg:
            conn.commit()

        conn.close()

        if error_msg:
            if len(users) == len(error_msg):
                return internal_server_error(internal_server_error_code)
            return response({'reasons': error_msg}, bad_request_code)
        else:
            return response({"count": count, "users": added_users}, created_code)


# delete user
@app.route('/bookmarking/<user_id>', methods=['DELETE'])
def users_delete(user_id):
    conn = create_connection(db_file)
    cur = conn.cursor()

    cur.execute('DELETE FROM users WHERE user_id=?', (user_id,))

    if cur.rowcount is 1:
        # return response({'status': no_content_code}, no_content_code)
        cur.execute('DELETE FROM bookmarks WHERE user_id = ?', (user_id,))

        conn.commit()
        conn.close()

        return response(get_users(), no_content_code)
    elif cur.rowcount is 0:
        msg = [{'message': msg_user_not_found}]
        conn.commit()
        conn.close()
        return response({'reasons': msg}, not_found_code)


# bookmark crud
# bookmark index
@app.route('/bookmarking/bookmarks', methods=['GET'])
def bookmarks_index():
    accepted_key = ['tags', 'count', 'offset']

    tags = request.args.get('tags')
    count = request.args.get('count')
    offset = request.args.get('offset')

    if offset:
        offset = int(offset) - 1

    try:
        for temp_key in list(request.args):
            if temp_key not in accepted_key:
                raise MalfunctionException
    except MalfunctionException as err:
        return internal_server_error(internal_server_error_code)

    conn = create_connection(db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    sql = "SELECT * FROM bookmarks"

    tuple_value = ()

    if tags:
        tags = [tag.strip() for tag in str(tags).split(",")]
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
    elif offset:
        # return internal_server_error(internal_server_error_code)
        tuple_value = tuple_value + (offset,)
        sql = sql + ' LIMIT -1 OFFSET ?'


    cur.execute(sql, tuple_value)
    rows = cur.fetchall()

    conn.close()

    result = []

    for row in rows:
        result.append(dict(row))

    row_count = len(rows)

    return response({'count': row_count, 'bookmarks': result}, ok_code)


@app.route('/bookmarking/bookmarks/<user_id>', methods=['GET'])
def bookmarks_show_user(user_id):
    conn = create_connection(db_file)
    cur = conn.cursor()

    cur.execute('SELECT * FROM users WHERE user_id=?', (user_id,))

    conn.commit()
    conn.close()

    if cur.rowcount is 0:
        msg = [{'message': msg_user_not_found}]
        return response({'reasons': msg}, not_found_code)

    accepted_key = ['tags', 'count', 'offset']

    tags = request.args.get('tags')
    count = request.args.get('count')
    offset = request.args.get('offset')

    if offset:
        offset = int(offset) - 1

    try:
        for x in list(request.args):
            if x not in accepted_key:
                raise MalfunctionException
    except MalfunctionException as err:
        return internal_server_error(internal_server_error_code)

    conn = create_connection(db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    sql = "SELECT * FROM bookmarks"

    tuple_value = ()

    tuple_value = tuple_value + (str(user_id),)
    sql = sql + " WHERE user_id = ?"

    if tags:
        tags = [tag.strip() for tag in str(tags).split(",")]
        for x in tags:
            tuple_value = tuple_value + ("%" + str(x).strip() + "%",)
            sql = sql + "AND tags LIKE ?"

    sql = sql + " ORDER BY url ASC"

    if count:
        tuple_value = tuple_value + (count,)
        sql = sql + ' LIMIT ?'
        if offset:
            tuple_value = tuple_value + (offset,)
            sql = sql + ' OFFSET ?'
    elif offset:
        return internal_server_error(internal_server_error_code)

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
        msg = [{'message': msg_user_not_found}]
        return response({'reasons': msg}, not_found_code)


@app.route('/bookmarking/bookmarks/<user_id>/<path:bookmark_url>', methods=['GET'])
def bookmarks_show_url(user_id, bookmark_url):
    error_msg = []

    conn = create_connection(db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    sql = "SELECT * FROM users WHERE user_id = ?"
    cur.execute(sql, (user_id,))
    rows = cur.fetchall()
    conn.commit()

    if len(rows) == 0:
        error_msg.append({"message": msg_user_not_found})
        return response({"reasons": error_msg}, not_found_code)

    tuple_value = (user_id, bookmark_url)

    sql = "SELECT * FROM bookmarks" \
          " WHERE user_id = ?" \
          " AND url = ?"

    cur.execute(sql, tuple_value)
    rows = cur.fetchall()

    result = []

    for row in rows:
        result.append(dict(row))

    row_count = len(rows)

    if row_count:
        return response({'count': row_count, 'bookmarks': result}, ok_code)
    else:
        error_msg.append({"message": msg_bookmark_not_found})
        return response({'reasons': error_msg}, not_found_code)


@app.route('/bookmarking/<user_id>/bookmarks', methods=['POST'])
def bookmarks_create(user_id):
    error_message = []

    count = request.json['count']
    bookmarks = request.json['bookmarks']

    conn = create_connection(db_file)
    cur = conn.cursor()

    added_bookmarks = []

    if int(count) > 0:
        for bookmark in bookmarks:
            url = bookmark['url']
            tags = str(bookmark['tags']).strip()
            text = str(bookmark['text']).strip()
            uid = str(bookmark['user_id']).strip()

            if str(uid) != user_id:
                return internal_server_error(internal_server_error_code)

            sql = "SELECT * FROM users WHERE user_id = ?"
            cur.execute(sql, (uid,))
            rows = cur.fetchall()

            if (len(rows)) == 0:
                error_message.append({"message": msg_user_not_found})
                return response({"reasons": error_message}, not_found_code)
            else:
                sql = "SELECT * FROM bookmarks" \
                      " WHERE user_id = ?" \
                      " AND url = ?"

                cur.execute(sql, (uid, url))

                rows = cur.fetchall()

                if len(rows) == 0:
                    sql = "INSERT INTO Bookmarks VALUES (?, ?, ?, ?)"
                    cur.execute(sql, (url, tags, text, uid))
                    conn.commit()
                    added_bookmarks.append({'tags': tags, 'text': text, 'url': url, 'uid': uid})
                else:
                    error_message.append({"message": msg_bookmark_already_exists})
    elif int(count) == 0:
        conn.close()
        return internal_server_error(internal_server_error_code)
    else:
        conn.close()
        return internal_server_error(internal_server_error_code)

    conn.close()

    if error_message:
        return response({"reasons": error_message}, bad_request_code)
    else:
        # return response('', created_code)
        return response({"count": count, "bookmarks": added_bookmarks}, created_code)
        # return response(get_bookmarks(user_id), created_code)


@app.route('/bookmarking/<user_id>/bookmarks/<path:bookmark_url>', methods=['PUT'])
def bookmarks_update(user_id, bookmark_url):
    error_message = []

    count = request.json['count']
    bookmarks = request.json['bookmarks']

    conn = create_connection(db_file)
    cur = conn.cursor()

    accept_key = ['url', 'tags', 'text', 'user_id']
    updated_bookmarks = []

    if check_key(accept_key, bookmarks):
        return internal_server_error(internal_server_error_code)

    if int(count) > 0:
        for bookmark in bookmarks:
            url = bookmark['url']
            tags = str(bookmark['tags']).strip()
            text = str(bookmark['text']).strip()
            uid = str(bookmark['user_id']).strip()

            if str(uid) != user_id:
                return internal_server_error(internal_server_error_code)

            sql = "SELECT * FROM users WHERE user_id = ?"
            cur.execute(sql, (uid,))
            user_exist = cur.fetchall()

            if (len(user_exist)) == 0:
                error_message.append({"message": msg_user_not_found})
                error_message.append({"message": msg_bookmark_not_found})
            else:
                sql = "SELECT * FROM bookmarks" \
                      " WHERE user_id = ?" \
                      " AND url = ?"

                cur.execute(sql, (uid, bookmark_url))

                rows = cur.fetchall()

                if len(rows) > 0:
                    tuple_value = ()
                    sql = "UPDATE bookmarks" \
                          " SET url = ?"
                    tuple_value = tuple_value + (url,)
                    if tags:
                        sql = sql + ", tags = ?"
                        tuple_value = tuple_value + (tags,)
                    if text:
                        sql = sql + ", text = ?"
                        tuple_value = tuple_value + (text,)
                    sql = sql + " WHERE user_id = ?"
                    sql = sql + " AND url = ?"
                    tuple_value = tuple_value + (user_id, bookmark_url,)
                    cur.execute(sql, tuple_value)
                    updated_bookmarks.append({'tags': tags, 'text': text, 'url': url, 'uid': uid})

                    conn.commit()
                else:
                    error_message.append({"message": msg_bookmark_not_found})

    elif int(count) == 0:
        conn.close()
        return internal_server_error(internal_server_error_code)
    else:
        conn.close()
        return internal_server_error(internal_server_error_code)

    conn.close()

    if not error_message:
        # return response("", created_code)
        return response({"count": count, "bookmarks": updated_bookmarks}, created_code)
    else:
        return response({"reasons": error_message}, not_found_code)


@app.route('/bookmarking/<user_id>/bookmarks/<path:bookmark_url>', methods=['DELETE'])
def bookmarks_delete(user_id, bookmark_url):
    error_msg = []

    if request.args:
        return internal_server_error

    conn = create_connection(db_file)
    cur = conn.cursor()

    sql = "SELECT * FROM bookmarks WHERE user_id = ?;"
    cur.execute(sql, (user_id,))
    user_exist = cur.fetchall()
    conn.commit()

    if user_exist:
        sql = "DELETE FROM bookmarks WHERE user_id = ? AND url = ?;"
        cur.execute(sql, (user_id, bookmark_url))
        conn.commit()
        if cur.rowcount == 0:
            error_msg.append({"message": msg_bookmark_not_found})
    else:
        error_msg.append({"message": msg_user_not_found})
        # error_msg.append({"message": msg_bookmark_not_found})

    conn.close()

    if not error_msg:
        # using no_content_code do not have any response body
        return response('', no_content_code)
    else:
        return response({"reasons": error_msg}, not_found_code)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
