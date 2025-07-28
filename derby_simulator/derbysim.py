import random as rand
import time
from typing import Sequence
from collections import Counter
import numpy as np
import pandas as pd
from tqdm import tqdm
import playercubes as cubes


class DerbySim:
    """Simulator for a Wuthering Waves Derby round."""

    def __init__(
        self,
        num_squares: int = 23,
        players: Sequence[str] | Sequence[cubes.Player] = tuple(),
        shuffle_players: bool = False,
        show_steps: bool = False,
        action_delay: float = 0,
    ):
        self.num_squares = num_squares
        if len(players) == 0:
            self.players = [cubes.Player("Player1"), cubes.Player("Player2")]
        else:
            self.players = []
            for p in players:
                if isinstance(p, str):
                    self.players.append(cubes.Player(p))
                elif isinstance(p, cubes.Player):
                    self.players.append(p)

        self.shuffle_players = shuffle_players
        self.show_steps = show_steps
        self.action_delay = action_delay
        self.next_round_order = []
        self.cumulative_steps = dict()
        self.match_setup(self.players, num_squares)
        

    def get_player_desc(self) -> dict:
        return {player.name: player.description for player in self.players}

    def get_summary(self) -> list[tuple[int, list[cubes.Player]]]:
        """Returns a dense, sorted representation of the current game state.
        Output is a list containing (position, [Player, ...]) from smallest to largest.
        """
        dense_track = [
            (pos, players) for pos, players in enumerate(self.track) if len(players) > 0
        ]
        return dense_track

    def get_summary_message(self) -> str:
        """Returns a string summary of the current game state."""
        dense_track = self.get_summary()
        # Re-order the track and squares in descending order
        dense_track = [(pos, players[::-1]) for pos, players in reversed(dense_track)]
        summary = ""
        for square in dense_track:
            for player in square[1]:
                summary += str((player, square[0]))
                summary += "\n"
        return summary

    def get_summary_visual(self) -> str:
        """Returns a visual representation of the current game state"""
        dense_track = self.get_summary()
        pos, stacks = list(zip(*dense_track))
        df = pd.DataFrame(stacks, index=pos)
        df = df.fillna("")
        return ""
        # return df.T
        # max_stack_size = 0
        # for square in dense_track:
        #     if len(square[1]) > max_stack_size:
        #         max_stack_size = len(square[1])
        # # Construct the visual as a matrix, counting from the bottom-left
        # # We construct this matrix top-down, left-right
        # visual = ""
        # for row in range(max_stack_size-1, -1, -1):
        #     for col, square in enumerate(dense_track):
        #         visual += "\t\t"*col
        #         try:
        #             visual += str(square[1][row])
        #         except IndexError:
        #             pass
        #     visual += "\n"
        # return visual

    def get_ranks(self) -> dict[cubes.Player, int]:
        """Returns the current rank of the player given."""
        dense_track = self.get_summary()
        _, stacks = list(zip(*dense_track))  # Extract player groups
        ranks = []
        for stack in stacks:  # Flatten groups to one-dimensional
            ranks.extend(stack)
        ranks = enumerate(
            ranks[::-1], 1
        )  # Assign ranks based on furthest position, then height
        ranks = {player: rank for rank, player in ranks}
        return ranks

    def get_winners(self) -> list[cubes.Player]:
        """Returns the winners of the game."""
        if len(self.track[-1]) > 0:
            return self.track[-1].copy()
        return []

    def match_setup(
        self, players: list[cubes.Player], num_squares: int = 23, first_half=True
    ):
        """Sets/resets a match to starting conditions.
        If first_half is True, places everyone on the first square.
        If first_half is False, use the results of the previous game.
        The winner begins on the finish line, and everyone else is placed
        in sequence behind them based on their previous relative positions."""
        if first_half:
            # Build an empty track (a list of lists)
            self.track = []
            for _ in range(num_squares):
                self.track.append([])

            # Add players and manually reset their position
            if self.shuffle_players is True:
                rand.shuffle(self.players)
            self.track[0].extend(self.players)
            for player in players:
                player.position = 0
        else:
            summary = self.get_summary()
            # Build an empty track
            self.track = []
            # Add extra squares to the track based on how many groups
            # there were in the previous game. This simulates "starting
            # from behind the finish line".
            track_len = num_squares + len(summary)
            for _ in range(track_len):
                self.track.append([])

            # Add players to the track based on their positions in
            # the previous game
            for group_idx, group in enumerate(summary):
                players = group[1]
                self.track[group_idx] = players
                for p in players:
                    p.position = group_idx

    def roll_round_order(
        self, modify_order: list[tuple[cubes.Player, int | None]] | None = None
    ):
        """Returns a random ordered list of Players. Optionally change the order after generation.
        Specify (Player, None) to move to the end of the list."""
        round_order = rand.sample(self.players, len(self.players))
        if modify_order is None:
            return round_order
        for player, pos in modify_order:
            round_order.remove(player)
            if pos is None:
                round_order.append(player)
            else:
                round_order.insert(pos, player)
        return round_order

    def roll_turns(
        self, round_order: tuple[cubes.Player] | list[cubes.Player]
    ) -> list[tuple[cubes.Player, int, int]]:
        """Returns the dice roll results for every player given. Preserves order.
        Returned in the format [(Player, roll, bonus_roll), ...]"""
        moves = []
        num_players = len(self.players)
        for move_order, player in enumerate(round_order):
            move_order = (move_order + 1, num_players)
            moves.append((player, *player.roll(round_order=round_order)))
        return moves

    def move_player_to(
        self, player: cubes.Player, new_pos: int, stack_position: int | None = None
    ):
        """Removes the player from their current position and places them at their
        new position. If Player.position does not match their current position, this
        method fails."""
        self.track[player.position].remove(player)
        if stack_position is None:
            self.track[new_pos].append(player)
        else:
            self.track[new_pos].insert(stack_position, player)
        player.update_pos(new_pos)

    def move_forward(
        self, player: cubes.Player, step_size: int, stack_position: int | None = None
    ):
        """Increments the player position by step_size.
        Does not apply game logic; Instead, see DerbySim.step()."""
        self.move_player_to(
            player=player, new_pos=player.position + step_size, stack_position=stack_position
        )

    def post_round(
        self,
        player: cubes.Player,
        round_order: Sequence[cubes.Player],
        current_rank: tuple[int, int],
        stacked_on: Sequence["Player"] = tuple(),
        stacked_by: Sequence["Player"] = tuple(),
    ):
        """Prompts the cube to trigger their post-round abilities."""
        actions = []
        next_round_order = []
        for player in self.players:
            results = player.post_round(round_order, current_rank)
            actions.extend(results["actions"])
            next_round_order.extend(results["next_round_order"])

        for action in actions:
            moving_player, step_size, stack_position = action
            self.move_forward(moving_player, step_size, stack_position)

        self.next_round_order = next_round_order

    def get_stacked_players(
        self, player: cubes.Player
    ) -> tuple[list[cubes.Player], list[cubes.Player]]:
        current_square_rank = self.track[player.position].index(player)
        stacked_on = self.track[player.position][:current_square_rank]
        # stacked_by nonempty only if cube is not at top
        if current_square_rank < len(self.track[player.position]) - 1:
            stacked_by = self.track[player.position][current_square_rank + 1 :]
        else:
            stacked_by = []
        return (stacked_on, stacked_by)

    def step(
        self,
        player: cubes.Player,
        round_order: Sequence[cubes.Player],
        current_rank: tuple[int, int],
        step_size: int = 1,
        first_step: bool = False,
        last_step: bool = False,
    ):
        """Queries the player for actions. Updates the game state by one step."""
        # First, calculate relevant parameters        
        stacked_on, stacked_by = self.get_stacked_players(player)

        # Calculate and apply actions
        actions = player.calculate_actions(
            round_order=round_order,
            current_rank=current_rank,
            step_size=step_size,
            stacked_on=stacked_on,
            stacked_by=stacked_by,
            first_step=first_step,
            last_step=last_step,
        )
        for action in actions:
            moving_player, step_size, stack_position = action
            # print(f"On {player}'s turn, {moving_player} moves {step_size} step(s).")
            self.move_forward(moving_player, step_size, stack_position)
            self.cumulative_steps.setdefault(moving_player, 0)
            self.cumulative_steps[moving_player] += step_size
        return actions

    def one_round(self) -> list[cubes.Player]:
        """Updates the game state to play through one round."""
        winners = self.get_winners()
        if len(winners) > 0:
            print(f"Aborted round; already have winners. {str(winners)[1:-1]}")
            return winners

        round_order = self.roll_round_order(modify_order=self.next_round_order)
        self.next_round_order = []
        round_turns = self.roll_turns(round_order)
        if self.show_steps is True:
            msg = "\nRound order and rolls:\n"
            for p, standard, bonus in round_turns:
                msg += f"{p}: {standard+bonus}. "
            print(msg)
                

        for turn in round_turns:
            player, roll, bonus_roll = turn[0], turn[1], turn[2]
            current_rank = (self.get_ranks()[player], len(self.players))
            steps_until_end = (len(self.track) - 1) - player.position
            num_steps = min(roll + bonus_roll, steps_until_end)
            if num_steps <= 0:
                pass  # Skip their turn if no steps are left
            elif num_steps == 1:
                self.step(
                    player,
                    round_order=round_order,
                    current_rank=current_rank,
                    first_step=True,
                    last_step=True,
                )
            else:
                self.step(
                    player,
                    round_order=round_order,
                    current_rank=current_rank,
                    first_step=True,
                )
                for _ in range(num_steps - 2):
                    self.step(
                        player, round_order=round_order, current_rank=current_rank
                    )
                self.step(
                    player,
                    round_order=round_order,
                    current_rank=current_rank,
                    last_step=True,
                )

            if self.show_steps is True:
                # If no previous player, do not register a change
                # Otherwise, print accumulated changes
                msg = f"It is {player}'s turn. "
                for p, n_steps in self.cumulative_steps.items():
                    msg += f"{p} advances {n_steps} step(s). "
                print(msg)
                print(self.get_summary_message())
                self.cumulative_steps = dict()
                time.sleep(self.action_delay)

            # Check for winners
            winners = self.get_winners()
            if len(winners) > 0:
                # print(f"Winner! {str(winners)[1:-1]}")
                return winners
        
        # Trigger any post-round effects
        for player in self.players:
            current_rank = (self.get_ranks()[player], len(self.players))
            stacked_on, stacked_by = self.get_stacked_players(player)
            self.post_round(
                player, round_order, current_rank, stacked_on, stacked_by
            )

        return []

    def half_game(self, first_half=True):
        """Resets game and plays through rounds until a winner is found.
        Only simulates one half; if first_half=False, sets relative starting
        positions based on the previous game."""
        self.match_setup(self.players, first_half=first_half)
        winners = []
        while len(winners) < 1:
            winners = self.one_round()
        return winners

    def full_game(self) -> tuple[list[cubes.Player], list[cubes.Player]]:
        """Plays through a full game with first and second halves, returns
        the winners in the first and second halves."""
        first_winners = self.half_game(first_half=True)
        second_winners = self.half_game(first_half=False)
        return (first_winners, second_winners)

    def __repr__(self):
        return f"Player(players={self.players}, show_steps={self.show_steps}, action_delay={self.action_delay})"

    def __str__(self):
        return str(self.track)

    # def one_round_old(self):
    #     """Moves the game forward by one round."""
    #     round_order = self.roll_round_order()
    #     for move_order, player in enumerate(round_order):
    #         roll = player.roll()
    #         current_square = self.track[player.position]
    #         stacked_on = current_square[: current_square.index(player)]
    #         stacked_by = current_square[current_square.index(player) + 1 :]
    #         new_pos = min(player.position + roll[0], self.num_squares - 1)
    #         num_move_squares = new_pos - player.position
    #         stacked_on = self.track[player.position]
    #         passes_by = []
    #         for square_pos in range(
    #             player.position + 1, min(new_pos + 1, self.num_squares - 1)
    #         ):
    #             square = self.track[square_pos]
    #             if len(square) != 0:
    #                 passes_by.append(square)
    #         actions = player.calculate_actions(
    #             num_move_squares=num_move_squares,
    #             move_order=(move_order, len(self.players) - 1),
    #             stacked_on=stacked_on,
    #             stacked_by=stacked_by,
    #             passes_by=passes_by,
    #         )
    #         for player, num_move_squares in actions:
    #             self.move_player(
    #                 player,
    #                 min(player.position + num_move_squares, self.num_squares - 1),
    #             )


def simulate_batch(
    players, n: int = 100, shuffle_players: bool = True, normalized: bool = True
) -> Counter | list:
    """Do many game simulations and tally the results."""
    derby = DerbySim(players=players, shuffle_players=shuffle_players)
    winners = []
    for _ in tqdm(range(n)):
        results = derby.full_game()
        winners.extend(results[0])
        winners.extend(results[1])

    winners = Counter(winners)
    if normalized:
        winners = dict(winners)
        total = sum(winners.values())
        for key, value in winners.items():
            winners[key] = value / total
        winners = list(winners.items())
        return sorted(winners, key=lambda x: x[1], reverse=True)
    else:
        return winners


def main(which: str):
    '''Runs a Derby simulation and prints the winners.'''
    match which:
        case "batch":
            winners = simulate_batch(
                players=(
                    cubes.CalcharoCube(),
                    cubes.PhoebeCube(),
                    cubes.JinhsiCube(),
                    cubes.BrantCube(),
                ),
                n=10000,
                normalized=True,
                shuffle_players=True,
            )
        case "full":
            winners = DerbySim(
                players=(
                    cubes.CalcharoCube(),
                    cubes.PhoebeCube(),
                    cubes.JinhsiCube(),
                    cubes.BrantCube(),
                ),
                shuffle_players=True,
                show_steps=True,
            ).full_game()
        case "half":
            winners = DerbySim(
                players=(
                    cubes.CalcharoCube(),
                    cubes.PhoebeCube(),
                    cubes.JinhsiCube(),
                    cubes.BrantCube(),
                ),
                shuffle_players=True,
                show_steps=True,
                action_delay=0.5
            ).half_game(first_half=True)

    print(winners)


if __name__ == "__main__":
    main("half")
