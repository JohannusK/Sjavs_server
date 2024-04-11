import socket
from threading import Thread
from game import Game

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)


def client_thread(conn, addr, game):
    """
    Handle communication with a connected client.
    """
    try:
        while True:
            data = conn.recv(1024)  # Buffer size is 1024 bytes
            if not data:
                break

            # Process received data and update game state
            response = game.process_command(data.decode())

            # Send response back to client
            conn.sendall(response.encode())

    finally:
        conn.close()

def start_server(host='127.0.0.1', port=65432):
    """
    Initialize the server, bind it to a host and port, and listen for incoming connections.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen()

    print(f"Server started on {host}:{port} waiting for connections...")

    # Initialize game logic
    game = Game()

    try:
        while True:
            # Accept new connections
            conn, addr = server_socket.accept()
            # Start a new thread to handle the connection
            t = Thread(target=client_thread, args=(conn, addr, game))
            t.start()
    finally:
        server_socket.close()


if __name__ == '__main__':
    start_server()
