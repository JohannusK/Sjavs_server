from itertools import product
from itertools import chain
from random import shuffle as r_shuffle
import socket
import selectors
import time

HOST = "127.0.0.1"
PORT = 3141

_CARDS = [str(val) + kol for val, kol in product(chain(range(7, 10), "TJQKA"), "DHSK")]


class Deck:
    def __init__(self):
        self.cards = _CARDS.copy()

    def shuffle(self) -> None:
        r_shuffle(self.cards)

    def pop(self, index: int = -1) -> str:
        return self.cards.pop(index)

    def cut(self, index: int) -> None:
        self.cards = self.cards[index:] + self.cards[:index]

    def reset(self) -> None:
        self.cards = _CARDS


class Coms:
    def __init__(self):
        self.sel = selectors.DefaultSelector()
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lsock.bind((HOST, PORT))
        self.seats = [False, False, False, False]
        self.STATUS = "NotStarted"

    def play(self):
        while True:
            events = self.sel.select(1)
            print('hello')
            for key, mask in events:
                callback = key.data[0]
                callback(key, mask)

    def accept(self, key, mask):
        sock = key.fileobj
        conn, addr = sock.accept()  # Should be ready
        print("accepted", conn, "from", addr)
        conn.setblocking(False)
        self.sel.register(
            conn, selectors.EVENT_READ | selectors.EVENT_WRITE, self.sel_player
        )

    def sel_player(self, key, mask):
        sock = key.fileobj
        close_me = True
        if mask & selectors.EVENT_READ and self.STATUS == "NotStarted":
            recv_data = sock.recv(1024)
            if recv_data:
                data = recv_data.decode()
                if len(data) == 7 and data.startswith("player") and data[6].isdigit():
                    if 0 < (p := int(data[6])) <= 4:
                        if self.seats[p - 1]:
                            sock.send(b"taken")
                        else:
                            player = Player(p, sock)
                            self.seats[p - 1] = player
                            print(f"spalari {p} er valdur")
                            sock.send(b"ok")
                            key.data[self.player_action, player]
                        if all(self.seats):
                            self.startgame()

        if close_me:
            self.sel.unregister(sock)
            sock.close()

    def player_action(self, key, mask):
        raise NotImplementedError

    def startgame(self):
        raise NotImplementedError

    def open(self):
        self.lsock.listen()
        print(f"lurtar á {(HOST, PORT)})")
        self.lsock.setblocking(False)
        self.sel.register(self.lsock, selectors.EVENT_READ, data=[self.accept, None])

    def close(self):
        self.sel.close()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class Player:
    def __init__(self, nr: int, sock):
        self.nr = nr
        self.sock = sock

    def __bool__(self):
        return True


class Dealer:
    def __init__(self, players: list[Player]):
        self.players = players
        self.deck = Deck()


if __name__ == "__main__":
    with Coms() as coms:
        coms.play()
