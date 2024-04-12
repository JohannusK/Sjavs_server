import random
import time
class Card:
    def __init__(self, suit, value):
        self.suit = suit
        self.value = value

    def __str__(self):
        value_names = {1: "Ace", 11: "Jack", 12: "Queen", 13: "King"}
        # Using a dictionary to map values for readability and compactness
        val = value_names.get(self.value, self.value)
        return f"{val} of {self.suit}"

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

class Player:
    def __init__(self, name):
        self.name = name
        self.hand = []
        self.last_update_time = time.time()

    def find_highest_trump_declaration(self):
        high_trumps_count = 0
        normal_cards = []
        for card in self.hand:
            print(card.value)
            print(card.suit)
            if (card.value == 12 and card.suit in ['Clubs', 'Spades']) or (card.value == 11):
                high_trumps_count += 1
                print('Trump ' + str(card.value) + ' ' + card.suit)
            else:
                normal_cards.append(card)
        suit_counts = {'Hearts': 0, 'Clubs': 0, 'Diamonds': 0, 'Spades': 0}
        for card in normal_cards:
            suit_counts[card.suit] += 1

        print(suit_counts)
        for suit in suit_counts:
            suit_counts[suit] += high_trumps_count
        print(suit_counts)
        longest_length = max(suit_counts.values())
        print(longest_length)
        if longest_length < 5:
            return "Pass"  # If no suit has 5 or more cards including high trumps
        longest_suits = [suit for suit, count in suit_counts.items() if count == longest_length]
        if len(longest_suits) > 1:
            return f"{longest_length} in {' and '.join(longest_suits)}"
        else:
            return f"{longest_length} in {longest_suits[0]}"

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
