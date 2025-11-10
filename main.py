import time
from client import ClientSocket, EndException, ByeException
from argparse import ArgumentParser
from collections import namedtuple

# Cell representation
Cell = namedtuple('Cell', ['humans', 'vampires', 'werewolves'])

# Global game state
GAME_STATE = {
    'rows': 0,
    'cols': 0,
    'board': {},  # {(x, y): Cell(h, v, w)}
    'our_species': None,  # 'vampires' or 'werewolves'
    'turn': 0,
}


def UPDATE_GAME_STATE(message):
    """Update game state from server message"""
    if message is None:
        return
    
    msg_type = message[0]
    data = message[1]

    if msg_type == "set":
        GAME_STATE['rows'] = data[0]
        GAME_STATE['cols'] = data[1]
        print(f"[UPDATE] Map: {data[1]}x{data[0]}")

    elif msg_type == "hum":
        # Just log it, we'll get humans from MAP
        print(f"[UPDATE] Received {len(data)} human positions")
    
    elif msg_type == "hme":
        GAME_STATE['_temp_home'] = tuple(data)
        print(f"[UPDATE] Home: {data}")

    elif msg_type == "map":
        GAME_STATE['board'] = {}
        for x, y, h, v, w in data:
            if h + v + w > 0:
                GAME_STATE['board'][(x, y)] = Cell(h, v, w)
        
        print(f"[UPDATE] Board has {len(GAME_STATE['board'])} positions with units")
        
        # Determine our species
        home = GAME_STATE.get('_temp_home')
        print(f"[UPDATE] Checking home position: {home}")
        if home and home in GAME_STATE['board']:
            cell = GAME_STATE['board'][home]
            print(f"[UPDATE] Home cell: humans={cell.humans}, vampires={cell.vampires}, werewolves={cell.werewolves}")
            GAME_STATE['our_species'] = 'vampires' if cell.vampires > 0 else 'werewolves'
            print(f"[UPDATE] We are: {GAME_STATE['our_species'].upper()}")
        else:
            print(f"[UPDATE] ERROR: Home not in board! Board positions: {list(GAME_STATE['board'].keys())[:5]}")
        
        if '_temp_home' in GAME_STATE:
            del GAME_STATE['_temp_home']

    elif msg_type == "upd":
        print(f"[UPDATE] UPD data received: {len(data)} updates")
        print(f"[UPDATE] First few updates: {data[:3] if len(data) > 0 else 'EMPTY'}")
        
        # If UPD is empty (first turn, no changes yet), keep the MAP board
        if len(data) == 0:
            print(f"[UPDATE] UPD is empty, keeping existing board with {len(GAME_STATE['board'])} positions")
        else:
            # UPD has data - replace board (assume it's full state like MAP)
            GAME_STATE['board'] = {}
            for x, y, h, v, w in data:
                if h + v + w > 0:
                    GAME_STATE['board'][(x, y)] = Cell(h, v, w)
        
        GAME_STATE['turn'] += 1
        print(f"[UPDATE] Turn {GAME_STATE['turn']}, Board now has {len(GAME_STATE['board'])} positions")


def COMPUTE_NEXT_MOVE(game_state):
    """Generate a random move"""
    import random
    
    print(f"[AI] Computing move...")
    print(f"[AI] Species: {game_state['our_species']}")
    
    # Check if species is set
    if game_state['our_species'] is None:
        print("[AI] ERROR: Species not set! Returning empty move.")
        return 0, []
    
    # Find all our groups
    our_groups = []
    our_idx = 1 if game_state['our_species'] == 'vampires' else 2
    
    print(f"[AI] Looking for species index {our_idx} (1=vampires, 2=werewolves)")
    print(f"[AI] Board positions to check: {list(game_state['board'].keys())[:5]}...")
    
    for (x, y), cell in game_state['board'].items():
        count = cell[our_idx]
        if count > 0:
            our_groups.append((x, y, count))
            print(f"[AI] Found group: ({x},{y}) with {count} units")
    
    print(f"[AI] Total groups found: {len(our_groups)}")
    
    if not our_groups:
        print("[AI] ERROR: No groups found!")
        return 0, []
    
    # Pick random group
    x, y, count = random.choice(our_groups)
    print(f"[AI] Selected group at ({x},{y}) with {count} units")
    
    # Get neighbors
    neighbors = []
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if 0 <= nx < game_state['cols'] and 0 <= ny < game_state['rows']:
                neighbors.append((nx, ny))
    
    print(f"[AI] Found {len(neighbors)} valid neighbors")
    
    if not neighbors:
        print("[AI] ERROR: No valid neighbors!")
        return 0, []
    
    # Pick random neighbor
    target_x, target_y = random.choice(neighbors)
    
    # Move all units
    move = [x, y, count, target_x, target_y]
    
    print(f"[AI] Move: ({x},{y}) -> ({target_x},{target_y}) with {count} units")
    print(f"[AI] Sending: {move}")
    
    return 1, [move]


def play_game(args):
    try:
        print(f"[MAIN] Connecting to {args.ip}:{args.port}...")
        client_socket = ClientSocket(args.ip, args.port)
        print("[MAIN] Connected!")
        
        print("[MAIN] Sending name...")
        client_socket.send_nme("MY_AI")
        print("[MAIN] Name sent!")
        
        # Receive initial setup
        print("[MAIN] Waiting for SET...")
        message = client_socket.get_message()
        UPDATE_GAME_STATE(message)
        
        print("[MAIN] Waiting for HUM...")
        message = client_socket.get_message()
        UPDATE_GAME_STATE(message)
        
        print("[MAIN] Waiting for HME...")
        message = client_socket.get_message()
        UPDATE_GAME_STATE(message)
        
        print("[MAIN] Waiting for MAP...")
        message = client_socket.get_message()
        UPDATE_GAME_STATE(message)
        
        print("[MAIN] Setup complete! Starting game loop...")
        
        # Main game loop
        while True:
            try:
                message = client_socket.get_message()
                if message is None:
                    print("[MAIN] Connection lost")
                    break
                
                print(f"[MAIN] Received: {message[0]}")
                UPDATE_GAME_STATE(message)
                
                if message[0] == "upd":
                    print("[MAIN] Computing next move...")
                    nb_moves, moves = COMPUTE_NEXT_MOVE(GAME_STATE)
                    print(f"[MAIN] Sending {nb_moves} moves: {moves}")
                    client_socket.send_mov(nb_moves, moves)
                    print("[MAIN] Move sent!")
                # wait for next turn
                time.sleep(1)
                    
            except EndException:
                print("[MAIN] Game ended")
                continue
            except ByeException:
                print("[MAIN] Server says bye")
                break
        
                
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('ip', type=str, help='IP address')
    parser.add_argument('port', type=int, help='Port')
    args = parser.parse_args()
    
    play_game(args)