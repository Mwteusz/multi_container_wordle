import json
import socket
import requests

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

dictionary_endpoint = endpoints["dictionary"]
dictionary_server_port = dictionary_endpoint["port"]
dictionary_server_ip = dictionary_endpoint["ip"]
print(f"Dictionary server: {dictionary_server_ip}:{dictionary_server_port}")

def get_random_word(length=5):
    url = f"https://random-word-api.herokuapp.com/word?length={length}"
    while True:
        result_json = requests.get(url,timeout=5).json()
        print(result_json)
        word = result_json[0]
        if is_word_valid(word):
            print("returning word: ", word)
            return word

def is_word_valid(word):
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    response = requests.get(url,timeout=5).json()
    print(response)
    if type(response) == list: #get the first element of the list if multiple definitions are found
        response = response[0]
    if "title" in response and response["title"] == "No Definitions Found":
        print(f"word \"{word}\" is invalid")
        return False
    print(f"word \"{word}\" is valid")
    return True



def validate_word_service(client, request):
    word = request["word"]
    result = is_word_valid(word)
    response = json.dumps({"response": result})
    message = "valid" if result else "invalid"
    print(f"word \"{word}\" is {message}")
    client.send(response.encode())


def random_word_service(client, request):
    length = request["length"]
    word = get_random_word(length)
    response = json.dumps({"response": word})
    print("returning word: ", word)
    client.send(response.encode())

def main():
    print("Starting dictionary server...")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", dictionary_server_port))
    server.listen()


    while True:
        client = None
        try:
            print("dictionary waiting for connections...")
            client, addr = server.accept()
            print("user connected from: ", addr)

            request_json = client.recv(4096).decode()

            data = json.loads(request_json)
            packet_type = data["packet_type"]
            print("Request type: ", packet_type)

            if packet_type == "get_random_word":
                random_word_service(client, data)
            elif packet_type == "validate_word":
                validate_word_service(client, data)
            else:
                print("Invalid packet type: ", packet_type)
                raise ValueError("Invalid packet type")

        except Exception as e:
            client.send(json.dumps({"packet_type": "error", "response": str(e)}).encode())
            continue
        finally:
            client.close()


if __name__ == '__main__':
    main()


