from utils import Deck, Card, Player


class Game:
    def __init__(self) -> None:
        self.deck: Deck = Deck()
        self.nPlayers: int = 0
        self.teamp: dict[int, list[int]] = {1: [1, 3], 2: [2, 4]}
        self.STATES: list[str] = [
            "init",
            "deal",
            "declaration",
            "first_card",
            "play",
            "end",
        ]
        self.state: str = "init"
        self.game_over: bool = True
        self.players: dict[int, Player] = {}
        self.updatesForPlayers: dict[int, list[str]] = {}
        self.dealer_position: int = 1
        self.current_turn: int = (
            0  # init to so sanity checks unter game_init don't freak out
        )
        self.deal_method: str = "fours"
        self.trump_length: int = 0  # Length of the longest trump suit declared
        self.trump_suit: str | None = None  # Suit of the declared trump
        self.trump_owner: Player | None = None
        self.declaration_count: int = 1

    def handle_trump_declaration(self, command: str, player_id: int) -> str:
        parts = command.split()
        declaration = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        if player_id != self.current_turn:
            return "Not your turn"

        current_player = self.players[player_id]
        maxmeld = self.players[player_id].find_highest_trump_declaration()
        print(maxmeld)
        print("Clubs" in maxmeld)
        if declaration == 0:
            response = f"{current_player.name} passes."
            self.declaration_count += 1
        elif (
            (declaration > self.trump_length)
            or ((declaration == self.trump_length) and ("Clubs" in maxmeld))
            and int(maxmeld.split(" ")[0]) == declaration
        ):
            response = f"{current_player.name} declares {declaration}"
            if (declaration == self.trump_length) and ("Clubs" in maxmeld):
                response += " Better"
                self.trump_suit = "Clubs"
            self.trump_length = declaration
            self.trump_owner = current_player
            self.declaration_count += 1
        else:
            return "Invalid declaration"

        # Update all players
        self.broadcast_players(response)

        # Move to the next player
        self.current_turn = (self.current_turn % self.nPlayers) + 1

        if self.declaration_count > self.nPlayers:
            self.current_turn = 0
            self.broadcast_players(
                f"Declarations complete. {self.trump_owner.name} has the highest declaration."
            )
            self.updatesForPlayers[self.trump_owner.id].append(
                "What suit is your declaration?"
            )
            return " "
        self.updatesForPlayers[self.current_turn].append(
            f"{self.players[self.current_turn].name}'s turn to declare."
        )

        return " "

    def get_state(self, info: bool) -> str:
        if not info:
            return self.state
        return (
            self.state
            + "\n"
            + {"init": f"{self.nPlayers} have joined"}.get(
                self.state, "Not Implemented"
            )
        )

    def setup_game(self) -> None:
        self.deck.shuffle()
        self.state = "deal"
        if self.dealer_position == 1:
            self.ask_for_split_or_banka(4)
        else:
            self.ask_for_split_or_banka(self.dealer_position - 1)
        self.game_over = False

    def deal_cards(self, player_id: int, _type: str, split_position: int = 0) -> None:
        """
        split or banka and deal the cards acordingly
        params:
            _type: split or banka
            split_position: only applyes to split and is the amound of cards to split
        """

        if self.state != "deal":
            return f"vit eru í {self.stage=}"

        if self.current_turn != player_id:
            print(self.current_turn)
            return "tad er ikki tín túrur"

        if (_type == "split") and (10 <= split_position <= 22):
            self.deck.cut(split_position)
            self.deal_method = "fours"
            self.broadcast_players("Deck split and cards dealt in fours")
        elif _type == "banka":
            self.deal_method = "eights"
            self.broadcast_players(f"Deck unchanged and cards dealt in eights. ")
        else:
            return "Invalid split position, try again"

        cards_per_player = 8
        deal_rounds = 2 if self.deal_method == "fours" else 1

        for round in range(deal_rounds):
            for player_id in range(1, self.nPlayers + 1):
                player = self.players[player_id]
                cards_to_deal = cards_per_player // deal_rounds
                for _ in range(cards_to_deal):
                    try:
                        player.draw(self.deck)
                    except ValueError as e:
                        print(e)  # Handle the case where the deck runs out of cards
                        return
        # Notify all players that cards have been dealt
        self.broadcast_players(f"Received {cards_per_player} cards.")

        self.current_turn = (self.dealer_position + 1) % 4 or 4
        self.state = "declaration"
        self.updatesForPlayers[self.current_turn].append(
            f"{self.players[self.current_turn].name} hvat meldar tú?"
        )
        return " "

    def ask_for_split_or_banka(self, player_id: int) -> None:
        self.current_turn = player_id
        self.updatesForPlayers[player_id].append("Choose 'split <position>' or 'banka'")

    def broadcast_players(self, msg: str) -> None:
        for player_id in self.players:
            self.updatesForPlayers[player_id].append(msg)

    def process_command(self, command: str) -> str:
        """
        ```init
        `Hallo, Eg eri {myname}`
            docs:
                registrer a new player with name {myname}
            return:
                full: there is no empty space for you
                P{player_id}: you are registrerd as player number {player_id}
        ```

        #Player commands
        all player commands start `P{player_id}`
        example:
            `P1 list players`

        ##subcommands:

        `list players`:
            lists all the players

        `state [info]`:
            get the state of the game
            if info more verbose

        ### init state
        `maxmeld`:
            finds your longest suits
            returns f"{longest_length} in {' and '.join(longest_suits)}"

        `M {n}`:
            declare a trump lenght of {n}
            return:
                " ": all good
                "Not your turn": Not your turn
                "Invalid declaration": Invalid declaration
        `S {sute}`:
            declaration of suit
            return:
                " ": all good
                "Invalid suit"

        `split {n}`
            split the deck and start dealing
            return:
                " ": all good
                "Invalid split position, try again"

        `banka`:
            deale the cards
            return:
                " ": all good

        `say ? ? {message}`:
            brodcast a message to all players
            return:
                " ": all good

        `GU`:
            heart beat, sends updates to player
            return:
                "No new updates."
                "Player not found."
        `show`:
            get the hand of the player
            return:
                the hand

        `deal`:
            deales cards
            TODO WTF is this
            return:
                " ": all good

        `quit`:
            sets a boolinan to True
            return:
                "Game over."

        `start game`:
            I dont even

        default:
            return:
                 "Unknown command."
        """
        # Example command processing logic
        print(command)
        if command.startswith("Hallo"):
            if self.nPlayers >= 4:
                return "full"
            else:
                self.nPlayers += 1
                self.players[self.nPlayers] = Player(
                    command[14:], self.nPlayers
                )  # Add the player to the dictionary
                self.updatesForPlayers[
                    self.nPlayers
                ] = []  # Initialize player's update list
                if self.nPlayers == 4:
                    self.setup_game()
                return f"P{self.nPlayers}"

        elif command.startswith("P"):
            player_id = int(command[1 : command.find(" ")])
            command = command[command.find(" ") + 1 :]

            if command.startswith("list players"):
                player_list = "".join(
                    f"ID {id}: {player.name}, Last Update: {player.time_since_last_update():.2f}s ago\n"
                    for id, player in self.players.items()
                )
                return f"Turn: {self.players[self.current_turn].name}\nCurrent Players:\n{player_list}"

            elif command.startswith("state"):
                # TODO implement
                return "Not Implemented"
            elif command == "maxmeld":
                return str(self.players[player_id].find_highest_trump_declaration())
            elif command.startswith("M "):  # Trump declaration starts with 'M '
                return self.handle_trump_declaration(command, player_id)
            elif command.startswith("S "):
                suit = command.split(" ")[1]
                if (
                    suit in self.players[player_id].find_highest_trump_declaration()
                ) and (suit in ["Hearts", "Clubs", "Diamonds", "Spades"]):
                    self.trump_suit = suit
                    self.broadcast_players(f"The current trump is {suit}")
                    return " "
                else:
                    return "Invalid suit"
            elif command.startswith("split"):
                # Here, the deck is split and dealt in fours
                try:
                    split_position = int(command.split()[-1])
                except:
                    split_position = -1
                return self.deal_cards(player_id, "split", split_position)
            elif command.startswith("banka"):
                # If 'banka', the deck remains unchanged and dealt in eights
                return self.deal_cards(player_id, "banka")
            elif command.startswith("Say"):
                self.broadcast_players(
                    f"{self.players[player_id].name} says:{command[3:]}"
                )
                return " "

            elif command.startswith("GU"):
                player_id = int(command[2:])
                player = self.players.get(player_id)
                if player:
                    player.update_last_time()  # Update the player's last interaction time
                    updates = self.updatesForPlayers.get(player_id, [])
                    if updates:
                        response = "\n".join(updates)
                        self.updatesForPlayers[
                            player_id
                        ] = []  # Clear updates after sending
                        return response
                    return "No new updates."
                return "Player not found."
            elif command.startswith("show"):
                return self.players.get(player_id).show_hand()

            elif command.startswith("deal"):
                num_cards = int(command.split(" ")[-1])
                for player_id, player in self.players.items():
                    player.draw(
                        self.deck, num_cards
                    )  # Assuming draw method can handle the deck directly
                    self.updatesForPlayers[player_id].append(
                        f"{num_cards} cards dealt to {player.name}"
                    )
                return "Dealt cards to each player."

            elif command == "quit":
                self.game_over = True
                return "Game over."

            elif command == "start game":
                if self.nPlayers == 2:
                    return " "
            return "Unknown command."
