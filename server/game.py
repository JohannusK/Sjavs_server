
class Game:
    def __init__(self):
        self.deck = 1
        self.nPlayers = 0
        self.game_over = False
        self.players = []
        self.updatesForPlayers = {}

    def process_command(self, command):
        """ Process a command sent by a client. """
        # Example command processing logic
        print(command)
        if command[0:5] == 'Hallo':
            player_id = len(self.players) + 1  # Unique player ID
            player_name = command[14:]
            self.nPlayers += 1
            self.players.append(player_name)
            self.updatesForPlayers[player_id] = []  # Initialize player's updates list
            return f"P{player_id}"

        if command == 'shuffle':
            self.deck += 1
            for player_id in self.updatesForPlayers:
                self.updatesForPlayers[player_id].append("Deck Shuffled")
            return "Deck shuffled."
        elif command.startswith('deal'):
            return "Dealt cards to each player."
        elif command == 'quit':
            self.game_over = True
            return "Game over."
        elif command[0:2] == "GU":
            player_id = int(command[2:])
            updates = self.updatesForPlayers.get(player_id, [])
            if updates:
                response = '\n'.join(updates)
                self.updatesForPlayers[player_id] = []  # Clear updates after sending
                return response
            return "W"
        elif command == 'start game':
            if self.nPlayers == 2:
                return
        return "Unknown command."