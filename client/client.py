
import socket
import json


wordle_server_port =  12347
wordle_server_ip = "127.0.0.1"

word_length = 5
guesses_limit = 6

def print_guess_info(guess, guess_info):
    guess = guess.upper()
    for letter, info in zip(guess, guess_info):
        if info == "INCORRECT":
            print(f" {letter} ", end=" ")
        elif info == "CORRECT_LETTER":
            print(f"({letter})", end=" ")
        elif info == "CORRECT_LETTER_POSITION":
            print(f"[{letter}]", end=" ")
    print("")

def print_instructions():
    print("Welcome to Wordle!")
    print(f"The word is {word_length} letters long.")
    print(f"You have {word_length} guesses.")
    print("For each guess, you will receive feedback:")
    print("  - A letter in the correct position will be surrounded by square brackets: [A]")
    print("  - A correct letter in the wrong position will be surrounded by parentheses: (A)")
    print("  - An incorrect letter will be surrounded by spaces:  A  ")
    print("Good luck!")
    print("")


def send_ack(server_socket):
    ack = json.dumps({"packet_type": "ack"})
    server_socket.send(ack.encode())


def play_wordle(server_socket, token):

    server_socket.send(json.dumps({"packet_type": "play", "token": token}).encode())

    guess = None
    guesses_history = []
    print_instructions()
    while True:
        print("Waiting for game response...")
        response_json = server_socket.recv(4096).decode()
        #print(response_json)
        response = json.loads(response_json)

        packet_type = response["packet_type"]
        if packet_type == "waiting_for_guess":
            guess = enter_guess(response, server_socket)
        elif packet_type == "wordle_result":
            guess_info = response["response"]
            guesses_history.append((guess, guess_info))
            print_current_game(guesses_history)
            send_ack(server_socket)
        elif packet_type == "message":
            print(response["message"])
            send_ack(server_socket)
        elif packet_type == "error":
            print(response["response"])
            send_ack(server_socket)
        elif packet_type == "game_over":
            print(response["game_over_message"])
            print("The word was: ", response["word"].upper())
            send_ack(server_socket)
            break
        else:
            print("Invalid packet type: ", packet_type)
            send_ack(server_socket)


def enter_guess(response, server_socket):
    guess_number = response["guess_number"]
    guess = input(f"enter your #{guess_number} guess: ")
    guess_json = json.dumps({"packet_type": "guess", "guess": guess})
    server_socket.send(guess_json.encode())
    return guess


def get_stats(history):
    total_games = len(history)
    total_wins = 0
    for game in history:
        if game['game_data']['win']:
            total_wins += 1
    total_losses = total_games - total_wins

    return {"total_games": total_games, "wins": total_wins, "losses": total_losses, "win_rate": (total_wins / total_games if total_games > 0 else 0)}
def print_stats(server_socket, token):

    server_socket.send(json.dumps({"packet_type": "history", "token": token}).encode())
    print("Getting stats...")
    response_json = server_socket.recv(4096).decode()
    response = json.loads(response_json)
    #print(response)
    if response["packet_type"] == "error":
        print("Could not get stats")
        return
    print("Game history:", response["history"])

    stats = get_stats(response["history"])
    print("Stats:", stats)

def print_current_game(guesses_history):
    for i, (word, guess_info) in enumerate(guesses_history):
        print(f"Guess #{i+1}:", end=" ")
        print_guess_info(word, guess_info)
    print("")


def clear_history(server_socket, token):
    server_socket.send(json.dumps({"packet_type": "clear_history", "token": token}).encode())
    print("Clearing history...")
    response_json = server_socket.recv(4096).decode()
    response = json.loads(response_json)
    if response["response"] == "success":
        print("History cleared")
    else:
        print("Could not clear history")


def change_password(server_socket, token):
    new_password = input("Enter new password: ")
    confirm_password = input("Confirm new password: ")
    if new_password != confirm_password:
        print("Passwords do not match")
        return

    server_socket.send(json.dumps({"packet_type": "change_password", "token": token, "new_password": new_password}).encode())
    response_json = server_socket.recv(4096).decode()
    response = json.loads(response_json)
    if response["response"] == "success":
        print("Password changed")
    else:
        print("Could not change password")


def main():
    token = None

    server_socket = None
    while True:
        try:
            packet_type = input("register or login:")
            if packet_type not in ["register", "login"]:
                print("Invalid choice")
                continue
            username = input("Username: ")
            password = input("Password: ")
            if packet_type == "register":
                confirm_password = input("Confirm Password: ")
                if password != confirm_password:
                    print("Passwords do not match, try again")
                    continue

            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect((wordle_server_ip, wordle_server_port))
            server_socket.settimeout(5.0)

            user_info = json.dumps({"packet_type": packet_type, "username": username, "password": password})
            server_socket.send(user_info.encode())
            response_json = server_socket.recv(4096).decode()
            #print(response_json)
            response = json.loads(response_json)
            if response["packet_type"] == "response" and response["response"] == "success":
                token = response["token"]
                break
            else: #error
                print("Try again, ", response["response"])
                server_socket.close()
        except (socket.timeout, ConnectionRefusedError) as e:
            print("Could not connect to server:", e)

    while True:
        try:
            choice = input("what would you like to do? (play, quit, stats, clear_history, change_password): ")

            if choice == "stats":
                print_stats(server_socket, token)
            elif choice == "clear_history":
                clear_history(server_socket, token)
            elif choice == "play":
                play_wordle(server_socket, token)
            elif choice == "change_password":
                change_password(server_socket, token)
            elif choice == "quit":
                server_socket.send(json.dumps({"packet_type": "logout"}).encode())
                break
            else:
                print("Invalid choice")

        except (socket.timeout, ConnectionRefusedError) as e:
            print("Could not connect to server:", e)
        except json.decoder.JSONDecodeError as e:
            print("Invalid json: ", e)

    server_socket.close()



if __name__ == '__main__':
    main()