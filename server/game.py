from utils import Deck, Card, Player
class Game:
    def __init__(self):
        self.deck = Deck()
        self.nPlayers = 0
        self.game_over = True
        self.players = {}
        self.updatesForPlayers = {}
        self.dealer_position = 1
        self.current_turn = 1  # Start with player 1's turn
        self.deal_method = "fours"
        self.trump_length = 0  # Length of the longest trump suit declared
        self.trump_suit = None  # Suit of the declared trump
        self.trump_owner = None
        self.declaration_count = 1

    def handle_trump_declaration(self, command, player_id):

        parts = command.split()
        declaration = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        if player_id != self.current_turn:
            return "Not your turn"

        current_player = self.players[player_id]
        maxmeld = self.players[player_id].find_highest_trump_declaration()
        print(maxmeld)
        print('Clubs' in maxmeld)
        if declaration == 0:
            response = f"{current_player.name} passes."
            self.declaration_count += 1
        elif (declaration > self.trump_length) or ((declaration == self.trump_length) and ('Clubs' in maxmeld)) and int(maxmeld.split(' ')[0]) == declaration:
            response = f"{current_player.name} declares {declaration}"
            if (declaration == self.trump_length) and ('Clubs' in maxmeld):
                response += ' Better'
                self.trump_suit = 'Clubs'
            self.trump_length = declaration
            self.trump_owner = current_player
            self.declaration_count += 1
        else:
            return "Invalid declaration"

        # Update all players
        for id in self.players:
            self.updatesForPlayers[id].append(response)



        # Move to the next player
        self.current_turn = (self.current_turn % self.nPlayers) + 1

        if self.declaration_count > self.nPlayers:
            self.current_turn = 0
            for id in self.players:
                self.updatesForPlayers[id].append(f"Declarations complete. {self.trump_owner.name} has the highest declaration.")
            self.updatesForPlayers[self.trump_owner.id].append("What suit is your declaration?")
            return " "
        self.updatesForPlayers[self.current_turn].append(f"{self.players[self.current_turn].name}'s turn to declare.")

        return " "
        
    def setup_game(self):
        self.deck.shuffle()
        if self.dealer_position == 1:
            self.ask_for_split_or_banka(4)
        else:
            self.ask_for_split_or_banka(self.dealer_position - 1)
        self.current_turn = 1
        self.game_over = False


    def deal_cards(self):
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
        for player_id in self.players:
            self.updatesForPlayers[player_id].append(f"Received {cards_per_player} cards.")

    def ask_for_split_or_banka(self, player_id):
        self.updatesForPlayers[player_id].append("Choose 'split <position>' or 'banka'")

    def process_command(self, command):
        '''
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
        '''
        # Example command processing logic
        print(command)
        if command.startswith('Hallo'):
            if self.nPlayers >= 4:
                return "full"
            else:
                self.nPlayers += 1
                self.players[self.nPlayers] = Player(command[14:], self.nPlayers)   # Add the player to the dictionary
                self.updatesForPlayers[self.nPlayers] = []  # Initialize player's update list
                if self.nPlayers == 4:
                    self.setup_game()
                return f"P{self.nPlayers}"
        elif command.startswith('P'):
            player_id = int(command[1:command.find(' ')])
            command = command[command.find(' ') + 1:]

            if command.startswith("list players"):
                player_list = ''.join(f"ID {id}: {player.name}, Last Update: {player.time_since_last_update():.2f}s ago\n"
                    for id, player in self.players.items())
                return f"Turn: {self.players[self.current_turn].name}\nCurrent Players:\n{player_list}"
            elif command == "maxmeld":
                return str(self.players[player_id].find_highest_trump_declaration())
            elif command.startswith("M "):  # Trump declaration starts with 'M '
                return self.handle_trump_declaration(command, player_id)
            elif command.startswith("S "):
                suit = command.split(' ')[1]
                if (suit in self.players[player_id].find_highest_trump_declaration()) and (suit in ["Hearts", "Clubs", "Diamonds", "Spades"]):
                    self.trump_suit = suit
                    for id in self.players:
                        self.updatesForPlayers[id].append(f"The current trump is {suit}")
                    return " "
                else:
                    return "Invalid suit"
            elif command.startswith("split"):
                # Here, the deck is split and dealt in fours
                split_position = int(command.split()[-1])
                response = ""
                if 10 <= split_position <= 22:
                    self.deck.cut(split_position)
                    self.deal_method = "fours"
                    self.deal_cards()
                    response += "Deck split and cards dealt in fours"
                else:
                    return "Invalid split position, try again"
                self.updatesForPlayers[self.current_turn].append(f"{self.players[self.current_turn].name} hvat meldar tú?")
                for id in self.players:
                    self.updatesForPlayers[id].append(response)
                return " "
            elif command.startswith("banka"):
                # If 'banka', the deck remains unchanged and dealt in eights
                self.deal_method = "eights"
                self.deal_cards()
                for id in self.players:
                    self.updatesForPlayers[id].append(f"Deck unchanged and cards dealt in eights. ")
                self.updatesForPlayers[self.current_turn].append(f"{ self.players[self.current_turn].name} hvat meldar tú?")
                return " "
            elif command.startswith("Say"):
                for id in self.players:
                    self.updatesForPlayers[id].append(f"{self.players[player_id].name} says:{command[3:]}")
                return " "

            elif command.startswith("GU"):
                player_id = int(command[2:])
                player = self.players.get(player_id)
                if player:
                    player.update_last_time()  # Update the player's last interaction time
                    updates = self.updatesForPlayers.get(player_id, [])
                    if updates:
                        response = '\n'.join(updates)
                        self.updatesForPlayers[player_id] = []  # Clear updates after sending
                        return response
                    return "No new updates."
                return "Player not found."
            elif command.startswith("show"):

                return self.players.get(player_id).show_hand()

            elif command.startswith('deal'):
                num_cards = int(command.split(' ')[-1])
                for player_id, player in self.players.items():
                    player.draw(self.deck, num_cards)  # Assuming draw method can handle the deck directly
                    self.updatesForPlayers[player_id].append(f"{num_cards} cards dealt to {player.name}")
                return "Dealt cards to each player."

            elif command == 'quit':
                self.game_over = True
                return "Game over."

            elif command == 'start game':
                if self.nPlayers == 2:

                    return " "
            return "Unknown command."
