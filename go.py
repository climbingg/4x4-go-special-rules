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


def board_to_string(board: tuple[int, ...], passed: bool, player_to_move: int) -> str:
    """打印棋盤"""
    print("----------\n----------")
    for row in range(0, 13, 4):
        print("".join(list(map(lambda x: chess[x], board[row: row + 4]))))
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


def combine_results_for_player(player: int, child_results: list[int]) -> int:
    """
    正確的證明式合併：
    UNKNOWN 不是正式結局，只表示目前無法證明
    """

    if player == BLACK:
        if BLACK_WIN in child_results:
            return BLACK_WIN
        if UNKNOWN in child_results:
            return UNKNOWN
        if DRAW in child_results:
            return DRAW
        return WHITE_WIN
    else:
        if WHITE_WIN in child_results:
            return WHITE_WIN
        if UNKNOWN in child_results:
            return UNKNOWN
        if DRAW in child_results:
            return DRAW
        return BLACK_WIN


def solve_depth(
    board: tuple[int, ...],
    player_to_move: int,
    ko_point: int,
    white_pass_used: bool,
    black_ever_placed: bool,
    white_ever_placed: bool,
    depth: int,
    repeat_guard: frozenset,
) -> int:
    """
    回傳：
    BLACK_WIN / WHITE_WIN / DRAW / UNKNOWN
    """

    state_key = (
        board,
        player_to_move,
        ko_point,
        white_pass_used,
        black_ever_placed,
        white_ever_placed,
    )

    # 防 DFS 路徑循環
    if state_key in repeat_guard:
        return DRAW

    table_key = (
        board,
        player_to_move,
        ko_point,
        white_pass_used,
        black_ever_placed,
        white_ever_placed,
        depth,
    )

    if state_key in save_table:
        return save_table[state_key]
    if table_key in table:
        return table[table_key]

    term = terminal_result(
        board,
        player_to_move,
        ko_point,
        white_pass_used,
        black_ever_placed,
        white_ever_placed,
    )
    if term is not None:
        table[table_key] = term
        save_table[state_key] = term
        return term

    if depth == 0:
        table[table_key] = UNKNOWN
        return UNKNOWN

    moves = legal_moves(board, player_to_move, ko_point, white_pass_used)

    next_guard = set(repeat_guard)
    next_guard.add(state_key)
    next_guard = frozenset(next_guard)

    child_results = []

    for mv in moves:
        result = play_move(board, player_to_move, mv, ko_point, white_pass_used)
        if result is None:
            continue

        new_board, next_player, new_ko, new_white_pass_used, _ = result

        new_black_ever = black_ever_placed or (player_to_move == BLACK and mv != "PASS")
        new_white_ever = white_ever_placed or (player_to_move == WHITE and mv != "PASS")

        child_result = solve_depth(
            new_board,
            next_player,
            new_ko,
            new_white_pass_used,
            new_black_ever,
            new_white_ever,
            depth - 1,
            next_guard,
        )

        child_results.append(child_result)

        # 提前停止：一旦找到當前玩家已證明的必勝分支，就不用繼續
        if player_to_move == BLACK and child_result == BLACK_WIN:
            table[table_key] = BLACK_WIN
            save_table[state_key] = BLACK_WIN
            return BLACK_WIN
        if player_to_move == WHITE and child_result == WHITE_WIN:
            table[table_key] = WHITE_WIN
            save_table[state_key] = WHITE_WIN
            return WHITE_WIN

    if not child_results:
        # 理論上這裡通常不會走到，因為 terminal_result 已先檢查無合法步
        table[table_key] = DRAW
        return DRAW

    best_result = combine_results_for_player(player_to_move, child_results)
    table[table_key] = best_result
    if best_result != 4:
        save_table[state_key] = best_result
    return best_result


def find_best_moves_at_depth(
    board: tuple[int, ...],
    player_to_move: int,
    ko_point: int,
    white_pass_used: bool,
    black_ever_placed: bool,
    white_ever_placed: bool,
    depth: int,
):
    moves = legal_moves(board, player_to_move, ko_point, white_pass_used)
    results = []

    for mv in moves:
        result = play_move(board, player_to_move, mv, ko_point, white_pass_used)
        if result is None:
            continue

        new_board, next_player, new_ko, new_white_pass_used, _ = result

        new_black_ever = black_ever_placed or (player_to_move == BLACK and mv != "PASS")
        new_white_ever = white_ever_placed or (player_to_move == WHITE and mv != "PASS")

        child_result = solve_depth(
            new_board,
            next_player,
            new_ko,
            new_white_pass_used,
            new_black_ever,
            new_white_ever,
            depth - 1,
            frozenset({
                (
                    board,
                    player_to_move,
                    ko_point,
                    white_pass_used,
                    black_ever_placed,
                    white_ever_placed,
                )
            }),
        )

        results.append((mv, child_result))

    def sort_key(item):
        _, res = item
        if player_to_move == BLACK:
            order = {
                BLACK_WIN: 3,
                UNKNOWN: 2,
                DRAW: 1,
                WHITE_WIN: 0,
            }
        else:
            order = {
                WHITE_WIN: 3,
                UNKNOWN: 2,
                DRAW: 1,
                BLACK_WIN: 0,
            }
        return order[res]

    results.sort(key=sort_key, reverse=True)
    return results


def iterative_deepening_search(
    board: tuple[int, ...],
    player_to_move: int,
    ko_point: int = -1,
    white_pass_used: bool = False,
    black_ever_placed: bool = False,
    white_ever_placed: bool = False,
    max_depth: int = 1000,
):
    last_results = []
    root_result = UNKNOWN

    for depth in range(1, max_depth + 1):
        root_result = solve_depth(
            board,
            player_to_move,
            ko_point,
            white_pass_used,
            black_ever_placed,
            white_ever_placed,
            depth,
            frozenset(),
        )

        print(f"\ndepth = {depth}")
        print(f"root result = {result_to_string(root_result)}")

        results = find_best_moves_at_depth(
            board,
            player_to_move,
            ko_point,
            white_pass_used,
            black_ever_placed,
            white_ever_placed,
            depth,
        )

        for mv, res in results:
            print(f"  move={mv}, result={result_to_string(res)}")

        if results:
            best_move, best_result = results[0]
            print(f"目前最佳步: {best_move}, {result_to_string(best_result)}")
        else:
            print("無合法步")

        print(f"save table size = {len(save_table)}")
        print(f"table size = {len(table)}")

        last_results = results

        found_forced_win = False
        has_unknown = False

        for _, res in results:
            if res == UNKNOWN:
                has_unknown = True
            if player_to_move == BLACK and res == BLACK_WIN:
                found_forced_win = True
            if player_to_move == WHITE and res == WHITE_WIN:
                found_forced_win = True

        if found_forced_win:
            print("已找到當前玩家的必勝步，停止加深。")
            break

        if not has_unknown:
            print("所有合法步都已經不是 UNKNOWN，停止加深。")
            break

        table.clear()

    return root_result, last_results


if __name__ == "__main__":
    init_board = tuple([0] * 16)

    print("初始棋盤：")
    board_to_string(init_board, False, BLACK)

    root_result, results = iterative_deepening_search(
        board=init_board,
        player_to_move=BLACK,
        ko_point=-1,
        white_pass_used=False,
        black_ever_placed=False,
        white_ever_placed=False,
        max_depth=1000,
    )

    print("\n初始局面最終結果：", result_to_string(root_result))

    print("\n最後深度的排序：")
    for mv, res in results:
        print(mv, result_to_string(res))
    with open("data.pkl", "wb") as f:
        pickle.dump(save_table, f)
