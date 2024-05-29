import json
import socket
import uuid

import bcrypt #pip install bcrypt
from pymongo import MongoClient, errors #pip install pymongo


endpoints = {
  "dictionary": {
    "ip": 'dictionary_container',
    "port": 12122
  },
  "mongo_db": {
    "ip": 'mongo_wordle',
    "port": 27017
  },
  "mongo_api": {
    "ip": 'mongo_client_container',
    "port": 12345
  },
  "wordle": {
    "ip": 'wordle_container',
    "port": 12347
  }
}
db_endpoint = endpoints["mongo_db"]
mongo_db_port = db_endpoint["port"]
mongo_db_ip = db_endpoint["ip"]
print(f"MongoDB: {mongo_db_ip}:{mongo_db_port}")

mongo_api_endpoint = endpoints["mongo_api"]
mongo_api_port = mongo_api_endpoint["port"]
mongo_api_ip = mongo_api_endpoint["ip"]
print(f"Mongo API: {mongo_api_ip}:{mongo_api_port}")


sessions = {} # token: username

users = None

def hash_password(password):
    try:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except Exception as e:
        print(f"Error hashing password: {e}")
        return None
def check_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception as e:
        print("Error checking password: ", e)
        return False

def clear_history(user_info, client):
    token = user_info["token"]
    users.update_one({"username": sessions[token]}, {"$set": {"game_history": []}})
    print("History cleared")
    client.send(json.dumps({"packet_type": "response", "response": "success"}).encode())

def print_db(client):
    for db in client.list_databases():
        print(db)

def add_user(username, password) -> bool:
    # Check if the username already exists
    if users.find_one({"username": username}):
        print("Username already exists")
        return False  # Username already exists
    response = users.insert_one({"username": username, "password": hash_password(password), "game_history": []})
    print("User added to database")
    return response.acknowledged  # returns true if the operation was successful


def register(user_info, client):
    username = user_info["username"]
    password = user_info["password"]
    print("request data: ", username, password)
    if add_user(username, password) == True:
        login(user_info, client)

    else:
        response_json = json.dumps({"packet_type": "error", "response": "could not add user to database"})
        client.send(response_json.encode())
        print("Register failed")

def is_user_logged_in(username):
    return username in sessions.values()
def login(user_info, client):
    username = user_info["username"]
    password = user_info["password"]
    print("request data: ", username, password)
    #if is_user_logged_in(username):
    #    response_json = json.dumps({"packet_type": "response", "response": "user is already logged in"})
    #    client.send(response_json.encode())
    #    print("Login failed: User is already logged in")
    #    return

    found_user = users.find_one({"username": username})


    if found_user is not None:
        password_hash = found_user["password"]
        if check_password(password, password_hash):
            token = str(uuid.uuid4())
            sessions[token] = username
            response_json = json.dumps({"packet_type": "response", "response": "success", "token": token})
            client.send(response_json.encode())
            print("Login success")
            return

    response_json = json.dumps({"packet_type": "response", "response": "user does not exist, or password is wrong"})
    client.send(response_json.encode())
    print("Login failed")

def get_history(user_info, client):
    try:
        token = user_info["token"]
        username = sessions[token]
        user = users.find_one({"username": username})
        if user is None:
            response_json = json.dumps({"packet_type": "error", "response": "invalid token"})
            client.send(response_json.encode())
            print("Get stats failed: Invalid token")
            return
        history = user["game_history"]
        response_json = json.dumps({"packet_type": "history", "response": "success", "history": history})
        client.send(response_json.encode())
    except KeyError as e:
        print("Get stats failed: ", e)
        response_json = json.dumps({"packet_type": "error", "response": "json error"})
        client.send(response_json.encode())




def add_history(request, client):
    token = request["token"]
    game_data = request["data"]

    try:
        if token is not None:
            try:
                username = sessions[token]
            except KeyError:
                raise ValueError("Could not authenticate user")
            users.update_one({"username": username}, {"$push": {"game_history": game_data}})

            response_json = json.dumps({"packet_type": "response", "response": "success"})
            client.send(response_json.encode())
            print("Game stats added")
        else:
            response_json = json.dumps({"packet_type": "error", "response": "invalid token"})
            client.send(response_json.encode())
            print("Add stats failed: Invalid token")
    except ValueError as e:
        print("Add history failed: ", e)
        response_json = json.dumps({"packet_type": "error", "response": str(e)})
        client.send(response_json.encode())


def change_password(user_info, client):
    token = user_info["token"]
    username = sessions[token]
    new_password = user_info["new_password"]
    result = users.update_one({"username": username}, {"$set": {"password": hash_password(new_password)}})
    print("Password changed, result: ", result)
    if result.acknowledged:
        response_json = json.dumps({"packet_type": "response", "response": "success"})
        client.send(response_json.encode())



def main():
    while True:
        try:
            print("connecting to mongo")
            client = MongoClient(mongo_db_ip, port=mongo_db_port, username='mongoadmin', password='hunter2', connectTimeoutMS=5000, socketTimeoutMS=5000, authSource="admin")

            wordle_db = client.wordle_db
            print(wordle_db)

            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind(("0.0.0.0", mongo_api_port))
            server.listen()

            test_connection = client.server_info()
            print("Connected to mongo: ", test_connection)
            global users
            users = wordle_db.users
            break

        except errors.ServerSelectionTimeoutError as e:
            print("Could not connect to mongo: ", e)


    while True:
        try:
            print("Database client is waiting for connections...")

            client, addr = server.accept()
            print("Connection from: ", addr)

            request_json = client.recv(4096).decode()
            data = json.loads(request_json)
            packet_type = data["packet_type"]

            print(f"Request type: \"{packet_type}\"")

            if packet_type == "login":
                login(data, client)
            elif packet_type == "register":
                register(data, client)
            elif packet_type == "add_history":
                add_history(data, client)
            elif packet_type == "get_history":
                get_history(data, client)
            elif packet_type == "clear_history":
                clear_history(data, client,)
            elif packet_type == "change_password":
                change_password(data, client)
            else:
                print("invalid request")
                client.send(json.dumps({"packet_type": "error", "response": "invalid request"}).encode())
        except (socket.timeout, errors.ServerSelectionTimeoutError) as e:
            print("Could not connect to mongo: ", e)





if __name__ == '__main__':
    main()