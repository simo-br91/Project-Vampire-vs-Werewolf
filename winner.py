from collections import namedtuple

Cell = namedtuple('Cell', ['humans', 'vampires', 'werewolves'])

GAME_STATE = {
    # Map dimensions
    'rows': 0,
    'cols': 0,

    # Current board state
    'board': {},  # {(x, y): Cell(h, v, w)}

    # Identity
    'our_species': None,  # 'vampires' or 'werewolves'

    # Game progress
    'turn': 0,

    # Cached totals (for fast evaluation)
    'our_total': 0,
    'enemy_total': 0,
    'human_total': 0,

    # Time management
    'turn_start_time': None,
}


def UPDATE_GAME_STATE(message):
    """Update game state from server message"""
    msg_type = message[0]
    data = message[1]

    if msg_type == "set":
        GAME_STATE['rows'] = data[0]
        GAME_STATE['cols'] = data[1]

    elif msg_type == "hum":
        # Not needed - humans are in MAP
        pass

    elif msg_type == "hme":
        # Just store temporarily to determine species
        GAME_STATE['_temp_home'] = tuple(data)

    elif msg_type == "map":
        # Build initial board
        GAME_STATE['board'] = {}
        for x, y, h, v, w in data:
            if h + v + w > 0:
                GAME_STATE['board'][(x, y)] = Cell(h, v, w)

        # Determine our species
        home = GAME_STATE['_temp_home']
        if home in GAME_STATE['board']:
            cell = GAME_STATE['board'][home]
            GAME_STATE['our_species'] = 'vampires' if cell.vampires > 0 else 'werewolves'

        del GAME_STATE['_temp_home']

        # Compute totals
        _update_totals()
        GAME_STATE['turn'] = 0

    elif msg_type == "upd":
        # Update board
        GAME_STATE['board'] = {}
        for x, y, h, v, w in data:
            if h + v + w > 0:
                GAME_STATE['board'][(x, y)] = Cell(h, v, w)

        # Update metadata
        GAME_STATE['turn'] += 1
        _update_totals()

        # Start turn timer (for time management in search)
        from time import time
        GAME_STATE['turn_start_time'] = time()


def _update_totals():
    """Update cached totals for fast evaluation"""
    our_total = 0
    enemy_total = 0
    human_total = 0

    our_idx = 1 if GAME_STATE['our_species'] == 'vampires' else 2
    enemy_idx = 2 if GAME_STATE['our_species'] == 'vampires' else 1

    for cell in GAME_STATE['board'].values():
        human_total += cell.humans
        our_total += cell[our_idx]
        enemy_total += cell[enemy_idx]

    GAME_STATE['our_total'] = our_total
    GAME_STATE['enemy_total'] = enemy_total
    GAME_STATE['human_total'] = human_total
