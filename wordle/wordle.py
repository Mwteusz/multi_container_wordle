import json
import socket
import threading
import time
from enum import Enum

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

wordle_endpoints = endpoints["wordle"]
wordle_ip = wordle_endpoints["ip"]
wordle_port = wordle_endpoints["port"]
#print(f"

mongo_api_endpoints = endpoints["mongo_api"]
mongo_api_ip = mongo_api_endpoints["ip"]
mongo_api_port = mongo_api_endpoints["port"]

dictionary_endpoints = endpoints["dictionary"]
dictionary_server_ip = dictionary_endpoints["ip"]
dictionary_server_port = dictionary_endpoints["port"]

def database_query(json_data):
    #print("sending request: ", json_data["packet_type"])
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((mongo_api_ip, mongo_api_port))
    client.settimeout(5.0)
    client.send(json_data.encode())
    response_json = client.recv(4096).decode()
    print("response: ", response_json)
    return response_json


class GuessInfo(str, Enum):
    INCORRECT = "INCORRECT" #gray
    CORRECT_LETTER = "CORRECT_LETTER" # yellow
    CORRECT_LETTER_POSITION = "CORRECT_LETTER_POSITION" #green

def compare(word, guess) -> list[GuessInfo]:
    info = list(GuessInfo.INCORRECT for _ in range(len(word)))

    print("CHECKING: ", word, guess)


    #check for correct letter in correct position
    for i in range(len(word)):
        if word[i] == guess[i]:
            info[i] = GuessInfo.CORRECT_LETTER_POSITION

    #check for correct letter in wrong position
    for i in range(len(word)):
        if word[i] != guess[i] and guess[i] in word:
            info[i] = GuessInfo.CORRECT_LETTER

    return info


def is_word_valid(word):
    #return True
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((dictionary_server_ip, dictionary_server_port))
    client.settimeout(5.0)
    request_json = json.dumps({"packet_type": "validate_word", "word": word})
    client.send(request_json.encode())
    response_json = client.recv(4096).decode()
    result: bool = json.loads(response_json)["response"]
    message = "valid" if result else "invalid"
    print(f"word \"{word}\" is {message}")
    return result
def get_random_word(length=5):
    #return "hello"
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((dictionary_server_ip, dictionary_server_port))
    client.settimeout(5.0)
    request_json = json.dumps({"packet_type": "get_random_word", "length": length})
    client.send(request_json.encode())
    response_json = client.recv(4096).decode()
    print(json.loads(response_json))
    random_word = json.loads(response_json)["response"]
    return random_word



class Wordle:
    def __init__(self, word_length=5, guesses_number=6):
        self.word = get_random_word(word_length)
        self.guesses = []
        self.word_length = word_length
        self.guesses_number = guesses_number
        print("Wordle word: ", self.word)

    def guess(self, guess):
        """:returns: list of GuessInfo enums"""
        if len(guess) != self.word_length:
            return 0 # "Invalid guess, may try again"
        if is_word_valid(guess) == False:
            return 1
        self.guesses.append(guess)
        return compare(self.word, guess)


def is_winner(result):
    return all([x == GuessInfo.CORRECT_LETTER_POSITION for x in result])


def upload_history(data, token):
    return database_query(json.dumps({"packet_type": "add_history", "data": data, "token": token}))



def play_wordle(client, token):
    #packet_json = json.dumps({"packet_type":"message","message": "guess the word!"})
    #client.send(packet_json.encode())
    word_length = 5
    guesses_number = 6
    wordle = Wordle(word_length=word_length, guesses_number=guesses_number)
    while True:
        packet_json = json.dumps({"packet_type": "waiting_for_guess", "guess_number": len(wordle.guesses)+1 })
        client.send(packet_json.encode())
        request_json = client.recv(4096).decode()
        packet_type = json.loads(request_json)["packet_type"]

        if packet_type == "logout":
            print("Player quit")
            break
        if packet_type == "guess":
            guess = json.loads(request_json)["guess"]
            print("Guess: ", guess)

            if len(guess) != word_length:
                response_json = json.dumps({"packet_type":"error", "response": f"Invalid guess, guess must be {word_length} characters long, try again"})
                client.send(response_json.encode())
                continue


            result = wordle.guess(guess)
            print("Result: ", result)

            if result == 0:
                response_json = json.dumps({"packet_type": "error", "response": f"Word must be {word_length} characters long, try again"})
                client.send(response_json.encode())
                continue
            elif result == 1:
                response_json = json.dumps({"packet_type": "error", "response": "Invalid word, try again"})
                client.send(response_json.encode())
                continue

            response_json = json.dumps({"packet_type": "wordle_result", "response": result})
            client.send(response_json.encode())
            #receive ack
            ack = client.recv(4096).decode()
            print("ack: ", ack)


            if is_winner(result):
                send_gameover(client, token, wordle, win=True)
                break
            elif len(wordle.guesses) == guesses_number:
                send_gameover(client, token, wordle, win=False)
                break



def send_gameover(client, token, wordle, win=False):
    response_json = json.dumps({"packet_type": "game_over",
                                "game_over_message": "You win!" if win else "You lose!",
                                "word": wordle.word})
    client.send(response_json.encode())
    upload_history({"game_data": {"win": win, "word": wordle.word, "guesses": wordle.guesses}}, token=token)


def send_history(client, token):
    print("Getting stats...")
    request_json = json.dumps({"packet_type": "get_history", "token": token})
    history_packet = database_query(request_json)
    history = json.loads(history_packet)
    print("Game history:", history)
    client.send(history_packet.encode())
def client_thread(client):
    try:
        while True:
            try:
                choice_json = client.recv(4096).decode()
                choice = json.loads(choice_json)
                packet_type = choice["packet_type"]
                token = choice["token"]
                if packet_type == "play":
                    print("playing wordle")
                    play_wordle(client, token=token)
                elif packet_type == "history":
                    send_history(client, token=token)
                elif packet_type == "clear_history":
                    print("clearing history")
                    response = database_query(json.dumps({"packet_type": "clear_history", "token": token}))
                    client.send(response.encode())
                elif packet_type == "logout":
                    print("Player quit")
                    break
                elif packet_type == "change_password":
                    print("changing password")
                    response = database_query(choice_json)
                    client.send(response.encode())
                else:
                    response_json = json.dumps({"packet_type": "error", "response": "Invalid choice"})
                    client.send(response_json.encode())
            except (ConnectionRefusedError, socket.timeout) as e:
                print("Could not connect:", e)
                error_json = json.dumps({"packet_type": "error", "response": str(e)})
                client.send(error_json.encode())
    except ConnectionResetError as e:
        print("Connection lost: ", e)
    except json.decoder.JSONDecodeError as e:
        print("Invalid json: ", e, "closing connection")
    finally:
        client.close()

def main():
    print("Starting wordle server... ", time.time())
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", wordle_port))
    server.listen()

    client_threads = []
    while True:
        try:
            print("wordle waiting for connections...")
            client, addr = server.accept()
            print("player connected from: ", addr)

            request_json = client.recv(4096).decode()

            response_json = database_query(request_json)
            client.send(response_json.encode())
            print("sending response: ", response_json)
            if json.loads(response_json)["response"] == "success":
                wordle_thread = threading.Thread(target=client_thread, args=(client,))
                client_threads.append(wordle_thread)
                wordle_thread.start()

        except Exception as e:
            print("Connection lost: ", e)
            continue

if __name__ == '__main__':
    main()

