import random
import time


class Table:
    def __init__(self, trump):
        self.cards: list[Card] = []
        self.cardOwners: list[Player] = []
        self.firstCard: Card = None
        self.trump = trump
        self.team_piles: dict[str, list] = {'vit': [], 'tit': []}

    def clear_and_reset(self) -> int:
        # returns player id (1-4)
        vinnari = max(
            (x1, x2, x3, x4, x5)
            for x1, x2, x3, x4, x5 in zip(
                [-1 if x not in x.TRUMPS else x.TRUMPS.index(x) for x in self.cards],
                [x.is_trump(self.trump) for x in self.cards],
                [x.is_suit(self.firstCard, self.trump) for x in self.cards],
                [14 if x.value==1 else x.value for x in self.cards],
                [x.id for x in self.cardOwners]
            )
        )[-1]
        team = ['tit', 'vit'][vinnari%2]
        self.team_piles[team].extend(self.cards)
        self.cards = []
        self.cardOwners = []
        self.firstCard = None

        return vinnari

    def play_first_card(self, card, player) -> str:
        ok_card = take_card(player, card)
        if ok_card:
            self.cards.append(ok_card)
            self.firstCard = ok_card
            self.cardOwners.append(player)
            return "OK"
        else:
            return "Tú hevur ikki kortið!"

    def play_other_card(self, card, player) -> str:
        ok_card = take_card(player, card)
        if ok_card:
            if (ok_card.is_suit(self.firstCard, self.trump) or
                    (not any([x.is_suit(self.firstCard, self.trump) for x in player.hand]))):
                self.cards.append(ok_card)
                self.cardOwners.append(player)
                return "OK"
            else:
                player.hand.append(ok_card)
                return "Ikki loyvt!"
        else:
            return "Tú hevur ikki kortið"

    def sum_cards_list(self, key):

        values = {1:11, 10:10, 11:2, 12:3, 13:4}
        return sum(values.get(x.value, 0) for x in self.team_piles[key])


class Card:
    short_value = {
        1:"A",
        2:"2",
        3:"3",
        4:"4",
        5:"5",
        6:"6",
        7:"7",
        8:"8",
        9:"9",
        10:'T',
        11:"J",
        12:"Q",
        13:"K"
    }
    short_suites = {
        'Diamonds':'D',
        'Hearts':'H',
        'Spades':'S',
        'Clubs':'C',
    }

    TRUMPS = ['JD', 'JH', 'JS', 'JC', 'QS', 'QC']

    def __init__(self, suit, value):
        self.suit = suit
        self.value = value

    def short_name(self):
        return f"{self.short_value[self.value]}{self.short_suites[self.suit]}"

    def long_name(self):
        value_names = {1: "Ace", 11: "Jack", 12: "Queen", 13: "King"}
        # Using a dictionary to map values for readability and compactness
        val = value_names.get(self.value, self.value)
        return f"{val} of {self.suit}"

    def is_trump(self, trump) -> bool:
        trump = trump[0]
        return (self.short_name()[1]==trump) or (self.short_name() in self.TRUMPS)

    def is_suit(self, first_card, trump:str) -> bool:
        trump = trump[0]
        
        if first_card.is_trump(trump):
            return self.is_trump(trump)
        
        return (self.suit == first_card.suit) and (self.short_name() not in self.TRUMPS)

    def __eq__(self, other):
        if type(other) == Card:
            return (self.value == other.value) and (self.suit == other.suit)
        elif type(other) == str:
            return self.short_name() == other
        return False

    def __str__(self):
        return self.short_name()

    def __repr__(self):
        return self.__str__()

class Deck:
    def __init__(self):
        # Initialize the deck by removing 2s, 3s, 4s, 5s, and 6s
        self.cards = [Card(suit, value) for suit in ['Hearts', 'Clubs', 'Diamonds', 'Spades']
                      for value in range(1, 14) if value not in (2, 3, 4, 5, 6)]

    def show(self):
        # Enhanced display method that joins string representations of each card
        return '\n'.join(str(card) for card in self.cards)

    def shuffle(self):
        # Using the built-in random.shuffle for better performance and readability
        random.shuffle(self.cards)

    def deal(self):
        # Added error handling to avoid exceptions when the deck is empty
        if self.cards:
            return self.cards.pop()
        else:
            raise ValueError("All cards have been dealt")

    def cut(self, cut_index):
        if 0 <= cut_index < len(self.cards):
            self.cards = self.cards[cut_index:] + self.cards[:cut_index]
        else:
            raise ValueError("Invalid cut index")

class Player:
    def __init__(self, name, id=None):
        self.name = name
        self.id = id
        self.hand = []
        self.last_update_time = time.time()

    def find_highest_trump_declaration(self):
        high_trumps_count = 0
        normal_cards = []
        for card in self.hand:
            if (card.value == 12 and card.suit in ['Clubs', 'Spades']) or (card.value == 11):
                high_trumps_count += 1
            else:
                normal_cards.append(card)
        suit_counts = {'Hearts': 0, 'Clubs': 0, 'Diamonds': 0, 'Spades': 0}
        for card in normal_cards:
            suit_counts[card.suit] += 1

        for suit in suit_counts:
            suit_counts[suit] += high_trumps_count
        longest_length = max(suit_counts.values())
        if longest_length < 5:
            return "0"  # If no suit has 5 or more cards including high trumps
        longest_suits = [suit for suit, count in suit_counts.items() if count == longest_length]

        return str(longest_length) + ''.join([x[0] for x in longest_suits])

    def update_last_time(self):
        self.last_update_time = time.time()

    def time_since_last_update(self):
        return time.time() - self.last_update_time

    def say_hello(self):
        print(f"Hi! My name is {self.name}")
        return self

    def draw(self, deck, num=1):
        """Draw num number of cards from a deck.
           Returns True if exactly num cards are drawn, False if fewer than that.
        """
        initial_count = len(self.hand)
        try:
            for _ in range(num):
                card = deck.deal()  # May raise a ValueError if the deck is empty
                self.hand.append(card)
        except ValueError:
            print("Not enough cards in the deck.")
            return False
        return len(self.hand) == initial_count + num

    def show_hand(self):
        """Return a string describing all the cards in the player's hand."""
        hand_description = ', '.join(str(card) for card in self.hand)
        return f"{self.name}'s hand: {hand_description}"

    def discard(self):
        """Discard the last card in hand. Returns the card if successful, None if hand is empty."""
        if self.hand:
            return self.hand.pop()
        print("No cards left to discard.")
        return None


def take_card(player, card) -> Card | int:
    try:
        card_loc = player.hand.index(card)
    except ValueError:
        return 0
    return player.hand.pop(card_loc)
