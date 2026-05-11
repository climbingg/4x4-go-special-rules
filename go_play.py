import pickle
from colorama import Fore, Back, Style


BOARD_SIZE = 4
BOARD_CELLS = BOARD_SIZE * BOARD_SIZE

EMPTY = 0
BLACK = 1
WHITE = 2

BLACK_WIN = 1
WHITE_WIN = 2
DRAW = 3
UNKNOWN = 4

NEIGHBORS = []
for i in range(BOARD_CELLS):
    r, c = divmod(i, BOARD_SIZE)
    adj = []
    if r > 0:
        adj.append(i - BOARD_SIZE)
    if r < BOARD_SIZE - 1:
        adj.append(i + BOARD_SIZE)
    if c > 0:
        adj.append(i - 1)
    if c < BOARD_SIZE - 1:
        adj.append(i + 1)
    NEIGHBORS.append(tuple(adj))
NEIGHBORS = tuple(NEIGHBORS)

# 最終產出結果
save_table = {}
# Transposition Table
table = {}
chess = [f"{Fore.YELLOW}{Back.YELLOW}  {Style.RESET_ALL}", f"{Fore.BLACK}{Back.YELLOW}黑{Style.RESET_ALL}", f"{Fore.WHITE}{Back.YELLOW}白{Style.RESET_ALL}"]


def opponent(player: int) -> int:
    return WHITE if player == BLACK else BLACK


def print_board(board: tuple[int, ...], passed: bool, player_to_move: int, hot: int) -> None:
    """打印棋盤"""
    print("----------\n----------")
    for row in range(0, 13, 4):
        print("".join(list(map(lambda x: chess[x], board[row: row + 4]))))
    if hot != -1:
        print(f"{hot - 1}是熱子!!")
    if not passed:
        print("白方還可以pass!!")
    else:
        print("白方不能pass了!!")
    if player_to_move == 1:
        print("輪黑!!")
    else:
        print("輪白!!")
    print("----------\n----------")

def result_to_string(result: int) -> str:
    if result == BLACK_WIN:
        return "BLACK_WIN"
    if result == WHITE_WIN:
        return "WHITE_WIN"
    if result == DRAW:
        return "DRAW"
    if result == UNKNOWN:
        return "UNKNOWN"
    return f"INVALID({result})"


def get_group(board: tuple[int, ...], start: int) -> set[int]:
    color = board[start]
    assert color != EMPTY

    group = {start}
    stack = [start]

    while stack:
        x = stack.pop()
        for nb in NEIGHBORS[x]:
            if nb not in group and board[nb] == color:
                group.add(nb)
                stack.append(nb)

    return group


def count_liberties(board: tuple[int, ...], group: set[int]) -> int:
    liberties = set()
    for stone in group:
        for nb in NEIGHBORS[stone]:
            if board[nb] == EMPTY:
                liberties.add(nb)
    return len(liberties)


def remove_group(board_list: list[int], group: set[int]) -> None:
    for pos in group:
        board_list[pos] = EMPTY


def has_any_stone(board: tuple[int, ...], player: int) -> bool:
    return player in board


def play_move(
    board: tuple[int, ...],
    player: int,
    move: int | str,
    ko_point: int,
    white_pass_used: bool,
):
    """
    合法則回傳:
    (
        new_board,
        next_player,
        new_ko_point,
        new_white_pass_used,
        captured_count
    )
    非法則回傳 None
    """

    if move == "PASS":
        if player != WHITE:
            return None
        if white_pass_used:
            return None
        return (board, BLACK, -1, True, 0)

    pos = move

    if not (0 <= pos < BOARD_CELLS):
        return None
    if board[pos] != EMPTY:
        return None
    if pos == ko_point:
        return None

    enemy = opponent(player)
    board_list = list(board)
    board_list[pos] = player

    captured_groups = []
    seen_enemy = set()

    for nb in NEIGHBORS[pos]:
        if board_list[nb] != enemy:
            continue
        if nb in seen_enemy:
            continue

        enemy_group = get_group(tuple(board_list), nb)
        seen_enemy |= enemy_group

        if count_liberties(tuple(board_list), enemy_group) == 0:
            captured_groups.append(enemy_group)

    captured_count = 0
    captured_pos = -1

    for group in captured_groups:
        captured_count += len(group)
        for x in group:
            captured_pos = x
        remove_group(board_list, group)

    my_group = get_group(tuple(board_list), pos)
    if count_liberties(tuple(board_list), my_group) == 0:
        return None

    # simple ko
    new_ko_point = -1
    if captured_count == 1:
        my_group_after = get_group(tuple(board_list), pos)
        if len(my_group_after) == 1 and count_liberties(tuple(board_list), my_group_after) == 1:
            new_ko_point = captured_pos

    return (tuple(board_list), enemy, new_ko_point, white_pass_used, captured_count)


def legal_moves(
    board: tuple[int, ...],
    player: int,
    ko_point: int,
    white_pass_used: bool,
) -> list[int | str]:
    moves = []

    for pos in range(BOARD_CELLS):
        if play_move(board, player, pos, ko_point, white_pass_used) is not None:
            moves.append(pos)

    if player == WHITE and not white_pass_used:
        moves.append("PASS")

    return moves

def terminal_result(
    board: tuple[int, ...],
    player_to_move: int,
    ko_point: int,
    white_pass_used: bool,
    black_ever_placed: bool,
    white_ever_placed: bool,
):
    """
    若終局則回傳 BLACK_WIN / WHITE_WIN / DRAW
    否則回傳 None
    """

    # 某方曾經下過，但後來被提光
    if black_ever_placed and not has_any_stone(board, BLACK):
        return WHITE_WIN
    if white_ever_placed and not has_any_stone(board, WHITE):
        return BLACK_WIN

    # 當前玩家無合法步 => 當前玩家輸
    moves = legal_moves(board, player_to_move, ko_point, white_pass_used)
    if not moves:
        return WHITE_WIN if player_to_move == BLACK else BLACK_WIN

    return None


if __name__ == "__main__":
    with open("data.pkl", "rb") as f:
        data: dict = pickle.load(f)

    print("初始棋盤：")
    board = tuple([0] * 16)
    pass_ok = False
    black_ever_placed = False
    white_ever_placed = False
    white_pass_used = False
    ko_point = -1
    player = BLACK
    while True:
        print_board(board, white_pass_used, player, ko_point)
        if terminal_result(board, player, ko_point, white_pass_used, black_ever_placed, white_ever_placed):
            print(f"{["白", "黑"][player - 1]}贏了")
            break
        moves = legal_moves(board, player, ko_point, white_pass_used)
        moves_res = [None] * 16
        for i, j in enumerate(board):
            moves_res[i] = "沒" if j == 0 else "已"
        for i in moves:
            if i == "PASS":
                continue
            new_board, next_player, new_ko_point, new_white_pass_used, _ = play_move(board, player, i, ko_point, white_pass_used)
            if next_player == 1:
                if (new_board, next_player, new_ko_point, new_white_pass_used, black_ever_placed, True) in data:
                    moves_res[i] = ["輸", "贏", "平"][data[(new_board, next_player, new_ko_point, new_white_pass_used, black_ever_placed, True)] - 1]
            elif (new_board, next_player, new_ko_point, new_white_pass_used, True, white_ever_placed) in data:
                moves_res[i] = ["贏", "輸", "平"][data[(new_board, next_player, new_ko_point, new_white_pass_used, True, white_ever_placed)] - 1]
        for i in range(0, 16, 4):
            print(*moves_res[i:i+4], "  |  ", " ".join(map(str, range(i, i + 4))), sep="")
        if "PASS" in moves:
            new_board, next_player, new_ko_point, new_white_pass_used, _ = play_move(board, player, "PASS", ko_point, white_pass_used)
            if (new_board, next_player, new_ko_point, new_white_pass_used, black_ever_placed, white_ever_placed) in data:
                pass_ok = True
                print(f"pass的結局是{["輸", "贏", "平"][data[(new_board, next_player, new_ko_point, new_white_pass_used, black_ever_placed, white_ever_placed)] - 1]}")
            else:
                pass_ok = False
                print("沒算pass的結局")
        else:
            print("無法pass")
        moves = list(map(str, moves))
        while True:
            input_move = input("輸入走法(0~15):")
            while input_move not in moves:
                input_move = input("輸入走法(你輸入錯誤):")
            if input_move != "PASS":
                input_move = int(input_move)
                if moves_res[input_move] in ["輸", "贏", "平"]:
                    break
            else:
                if pass_ok:
                    break
            print("因為沒有算到，所以重新再問")
        board, player, ko_point, white_pass_used, _ = play_move(board, player, input_move, ko_point, white_pass_used)
        if player == 2:
            black_ever_placed = True
        if player == 1 and input_move != "PASS":
            white_ever_placed = True


print("finish!!!")
