from server.bot_player import BotBrain, DIFFICULTY_STRATEGIES


def test_bot_rearms_split_choice_after_redeal_message():
    bot = BotBrain(name="TestBot", send_fn=lambda _payload: "")
    bot.deal_choice_needed = False
    bot.hand = ["AH", "KD"]
    bot.trump = "H"
    bot.last_declared_suits = "H"
    bot.current_trick = [(2, "7C")]

    bot._handle_update("No player declared trump. Redealing.")

    assert bot.deal_choice_needed is True
    assert bot.hand == []
    assert bot.current_trick == []
    assert bot.trump is None
    assert bot.last_declared_suits == ""


def test_medium_strategy_dumps_points_when_partner_has_qc():
    bot = BotBrain(
        name="TestBot",
        send_fn=lambda _payload: "",
        difficulty="medium",
        strategy_names=DIFFICULTY_STRATEGIES["medium"],
    )
    bot.player_id = 1
    bot.trump = "S"
    bot.hand = ["AH", "TH", "7H"]
    bot.current_trick = [(2, "7H"), (3, "QC")]

    choice = bot._choose_card(["AH", "TH", "7H"])

    assert choice == "AH"


def test_hard_strategy_wins_with_weakest_winning_card():
    bot = BotBrain(
        name="TestBot",
        send_fn=lambda _payload: "",
        difficulty="hard",
        strategy_names=DIFFICULTY_STRATEGIES["hard"],
    )
    bot.player_id = 1
    bot.trump = "H"
    bot.hand = ["8H", "AH", "QC"]
    bot.current_trick = [(2, "7H")]

    choice = bot._choose_card(["8H", "AH", "QC"])

    assert choice == "8H"


def test_medium_strategy_leads_unseen_ace_early():
    bot = BotBrain(
        name="TestBot",
        send_fn=lambda _payload: "",
        difficulty="medium",
        strategy_names=DIFFICULTY_STRATEGIES["medium"],
    )
    bot.player_id = 1
    bot.trump = "S"
    bot.hand = ["AH", "AS", "KD"]
    bot.seen_suits_played = {"D"}
    bot.trick_winners = [2]

    choice = bot._choose_card(["AH", "AS", "KD"])

    assert choice == "AH"


def test_medium_strategy_does_not_lead_trump_ace_as_unseen_ace():
    bot = BotBrain(
        name="TestBot",
        send_fn=lambda _payload: "",
        difficulty="medium",
        strategy_names=DIFFICULTY_STRATEGIES["medium"],
    )
    bot.player_id = 1
    bot.trump = "S"
    bot.hand = ["AS", "KD", "7H"]
    bot.seen_suits_played = set()
    bot.trick_winners = []

    assert bot._strategy_lead_unseen_ace(["AS", "KD", "7H"]) is None


def test_medium_strategy_discards_filler_when_opponents_are_winning():
    bot = BotBrain(
        name="TestBot",
        send_fn=lambda _payload: "",
        difficulty="medium",
        strategy_names=DIFFICULTY_STRATEGIES["medium"],
    )
    bot.player_id = 1
    bot.trump = "H"
    bot.hand = ["AD", "7D", "8D"]
    bot.current_trick = [(2, "AH"), (3, "KD")]

    choice = bot._choose_card(["AD", "7D", "8D"])

    assert choice == "7D"


def test_hard_strategy_stingas_with_low_trump():
    bot = BotBrain(
        name="TestBot",
        send_fn=lambda _payload: "",
        difficulty="hard",
        strategy_names=DIFFICULTY_STRATEGIES["hard"],
    )
    bot.player_id = 1
    bot.trump = "H"
    bot.hand = ["7H", "9H", "AD"]
    bot.current_trick = [(2, "KC"), (3, "AC")]

    choice = bot._choose_card(["7H", "9H", "AD"])

    assert choice == "7H"


def test_hard_strategy_does_not_stinga_when_partner_is_winning():
    bot = BotBrain(
        name="TestBot",
        send_fn=lambda _payload: "",
        difficulty="hard",
        strategy_names=DIFFICULTY_STRATEGIES["hard"],
    )
    bot.player_id = 1
    bot.trump = "H"
    bot.hand = ["7H", "9H", "AD"]
    bot.current_trick = [(2, "KC"), (3, "AH")]

    choice = bot._choose_card(["7H", "9H", "AD"])

    assert choice == "7H"


def test_medium_strategy_does_not_overtake_partner():
    bot = BotBrain(
        name="TestBot",
        send_fn=lambda _payload: "",
        difficulty="medium",
        strategy_names=DIFFICULTY_STRATEGIES["medium"],
    )
    bot.player_id = 1
    bot.trump = "S"
    bot.hand = ["AD", "7D", "KD"]
    bot.current_trick = [(2, "8D"), (3, "KD")]

    choice = bot._choose_card(["AD", "7D", "KD"])

    assert choice == "7D"


def test_hard_strategy_saves_high_trumps():
    bot = BotBrain(
        name="TestBot",
        send_fn=lambda _payload: "",
        difficulty="hard",
        strategy_names=DIFFICULTY_STRATEGIES["hard"],
    )
    bot.player_id = 1
    bot.trump = "H"
    bot.hand = ["QC", "8H", "AH"]
    bot.current_trick = [(2, "7H")]

    choice = bot._choose_card(["QC", "8H", "AH"])

    assert choice == "8H"
