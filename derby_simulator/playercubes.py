"""Module containing the base Player class and characters with special abilities."""

import random as rand
from typing import Sequence

cube_descriptions = {
    "Roccia": "If Roccia is the last to move, she advances 2 extra pads",
    "Brant": "If Brant is the first to move, he advances 2 extra pads.",
    "Cantarella": "The first time Cantarella passes by other cubes, she stacks with them and carries them forward. This can only be triggered once per match.",
    "Zani": "The dice will only roll a 1 or 3. When moving with other Cubes stacking above, there is a 40%% chance to advance 2 extra pads next turn.",
    "Phoebe": "There is a 50%% chance to advance an extra pad",
    "Cartethiya": "If ranked last after own action, there is a 60% chance to advance 2 extra pads in all remaining turns. This can only be triggered once in each match.",
    "Camellya": "There is a 50%% chance of triggering this effect on Camellya's turn. For every other cube on the same pad besides Camellya, she advances 1 extra pad, while other Cubes stay in place.",
    "Jinhsi": "If other cubes are stacked on top of Jinhsi, there is a 40%% chance she will move to the top of the stack.",
    "Carlotta": "There is a 28%% chance to advance twice with one rolled number.",
    "Calcharo": "If Calcharo is the last to move, he advances 3 extra pads.",
    "Changli": "If other cubes are stacked below Changli, there is a 65%% chance she will be the last to move in a turn",
    "Shorekeeper": "The dice will only roll a 2 or 3",
}


class Player:
    """A player object to keep track of rolling mechanics and current position on the board."""

    def __init__(self, name: str, description: str = "", position: int = 0):
        self.name = name
        self.description = description
        self.position = position
        self.ability_expended = False
        self.ability_active = False

    def roll(
        self,
        round_order: Sequence["Player"],
        stacked_on: Sequence["Player"] = tuple(),
        stacked_by: Sequence["Player"] = tuple(),
    ) -> tuple[int, int]:
        """Returns a tuple containing the regular roll and bonus roll."""
        return (rand.randint(1, 3), 0)

    def calculate_actions(
        self,
        round_order: Sequence["Player"],
        current_rank: tuple[int, int],
        step_size: int = 1,
        stacked_on: Sequence["Player"] = tuple(),
        stacked_by: Sequence["Player"] = tuple(),
        first_step: bool = False,
        last_step: bool = False,
    ) -> list[tuple["Player", int, int]]:
        """Pass as arguments information about the game state.
        Returns a list of action requests to the game controller.
        Requests are formatted (Player, step_size: int = 1, to_bottom: bool)"""
        actions = [(self, step_size, None)]

        # Queue stacked-above cubes to move with the player, preserving order
        for other in stacked_by:
            actions.append((other, step_size, None))
        return actions

    def post_round(
        self, round_order: Sequence["Player"], current_rank: tuple[int, int]
    ) -> dict[str, list]:
        """Trigger any post-round abilities, if applicable."""
        return {"actions": [], "next_round_order": []}

    def update_pos(self, new_pos: int):
        """Updates internal tracking of player position to new_pos."""
        self.position = new_pos
        return self.position

    def forward(self, num_move_squares: int):
        """Increments internal tracking of player position by num_move_squares."""
        self.position += num_move_squares
        return self.position

    def __repr__(self):
        return str(self.name)


class RocciaCube(Player):
    """Roccia. If Roccia is the last to move, she advances 2 extra pads."""

    def __init__(self):
        super().__init__(name="Roccia")

    def roll(
        self,
        round_order: Sequence[Player],
        stacked_on: Sequence["Player"] = tuple(),
        stacked_by: Sequence["Player"] = tuple(),
    ) -> tuple[int, int]:
        standard_roll = super().roll(round_order=round_order)
        if round_order.index(self) == len(round_order) - 1:
            return (standard_roll[0], 2)
        else:
            return (standard_roll[0], 0)


class BrantCube(Player):
    """Brant. If Brant is the first to move, he advances 2 extra pads."""

    def __init__(self, position: int = 0):
        super().__init__(name="Brant", position=position)

    def roll(
        self,
        round_order: Sequence[Player],
        stacked_on: Sequence["Player"] = tuple(),
        stacked_by: Sequence["Player"] = tuple(),
    ) -> tuple[int, int]:
        standard_roll = super().roll(round_order=round_order)
        if round_order.index(self) == 0:
            return (standard_roll[0], 2)
        else:
            return (standard_roll[0], 0)


class CantarellaCube(Player):
    """Cantarella. The first time Cantarella passes by other cubes, she stacks with them and carries them forward. This can only be triggered once per match.
    Note: Cantarella sticks onto cubes and carries them from above."""

    def __init__(self, position: int = 0):
        super().__init__(name="Cantarella", position=position)
        self.ability_expended = False
        self.ability_active = False
        self.num_carried = 0

    def calculate_actions(
        self,
        round_order: Sequence[Player],
        current_rank: tuple[int, int],
        step_size: int = 1,
        stacked_on: Sequence["Player"] = tuple(),
        stacked_by: Sequence["Player"] = tuple(),
        first_step: bool = False,
        last_step: bool = False,
    ):
        if first_step:
            # First step, yet to pass anyone
            action = super().calculate_actions(
                round_order,
                current_rank,
                step_size,
                stacked_on,
                stacked_by,
                first_step,
                last_step,
            )
        elif len(stacked_on) < 1:
            # Not first step, but intersected nobody in previous step
            action = super().calculate_actions(
                round_order,
                current_rank,
                step_size,
                stacked_on,
                stacked_by,
                first_step,
                last_step,
            )
        elif not self.ability_expended:
            # Not first step, stacked on somebody, and ability available
            self.ability_expended = True
            self.ability_active = True
            self.num_carried = len(stacked_on)
            action = [(self, step_size, None)]
            # Carried cubes move first to simulate Cantarella "carrying" them
            # Carried --> Cantarella --> Stacked by
            for other in stacked_on:
                action.insert(0, (other, step_size, None))
            for other in stacked_by:
                action.append((other, step_size, None))
        elif self.ability_active:
            # Ability already used and currently active
            action = [(self, step_size, None)]
            # Only carry the amount of cubes originally taken.
            for other in stacked_on[-self.num_carried :]:
                action.insert(0, (other, step_size, None))
            for other in stacked_by:
                action.append((other, step_size, None))
        else:
            # Ability already used and not active
            action = super().calculate_actions(
                round_order,
                current_rank,
                step_size,
                stacked_on,
                stacked_by,
                first_step,
                last_step,
            )
        if last_step:
            self.ability_active = False
        return action


class ZaniCube(Player):
    """Zani.
    The dice will only roll a 1 or 3. When moving with other Cubes stacking
    above, there is a 40%% chance to advance 2 extra pads next turn."""

    def __init__(self, position: int = 0):
        super().__init__(name="Zani", position=position)
        self.ability_active = False

    def roll(
        self,
        round_order: Sequence[Player],
        stacked_on: Sequence["Player"] = tuple(),
        stacked_by: Sequence["Player"] = tuple(),
    ) -> tuple[int, int]:
        """Returns a tuple containing the regular roll and bonus roll."""

        def roll_ability() -> bool:
            """Returns True if conditions and roll chance checks pass."""
            condition = len(stacked_by) > 0
            random_trigger = rand.choices((False, True), (0.6, 0.4))[0]
            return condition and random_trigger

        if self.ability_active:
            self.ability_active = False
            if roll_ability():
                self.ability_active = True
            return (rand.choice((1, 3)), 2)
        else:
            if roll_ability():
                self.ability_active = True
            return (rand.choice((1, 3)), 0)


class PhoebeCube(Player):
    """Phoebe. There is a 50%% chance to advance an extra pad."""

    def __init__(self, position: int = 0):
        super().__init__(name="Phoebe", position=position)

    def roll(
        self,
        round_order: Sequence[Player],
        stacked_on: Sequence["Player"] = tuple(),
        stacked_by: Sequence["Player"] = tuple(),
    ) -> tuple[int, int]:
        standard_roll = super().roll(round_order, stacked_on, stacked_by)
        bonus_roll = rand.choice((0, 1))
        return (standard_roll[0], bonus_roll)


class CartethiyaCube(Player):
    """Cartethiya.
    If ranked last after own action, there is a 60% chance to advance 2 extra
    pads in all remaining turns. This can only be triggered once in each match."""

    def __init__(self, position: int = 0):
        super().__init__(name="Cartethiya", position=position)
        self.ability_active = False

    def roll(
        self,
        round_order: Sequence[Player],
        stacked_on: Sequence[Player] = tuple(),
        stacked_by: Sequence[Player] = tuple(),
    ) -> tuple[int, int]:
        standard_roll = super().roll(round_order, stacked_on, stacked_by)
        if self.ability_active:
            bonus_roll = rand.choices((0, 2), (0.4, 0.6))[0]
        else:
            bonus_roll = 0
        return (standard_roll[0], bonus_roll)

    def post_round(
        self,
        round_order: Sequence[Player],
        current_rank: tuple[int, int],
        stacked_on: Sequence["Player"] = tuple(),
        stacked_by: Sequence["Player"] = tuple(),
    ):
        if current_rank[0] == current_rank[1]:
            self.ability_active = True
        return super().post_round(round_order, current_rank)


class JinhsiCube(Player):
    """Jinhsi. If other cubes are stacked on top of Jinhsi, there is a 40%% chance she will move to the top of the stack."""

    def __init__(self, position: int = 0):
        super().__init__(name="Jinhsi", position=position)
        self.ability_active = False

    def calculate_actions(
        self,
        round_order: Sequence[Player],
        current_rank: tuple[int, int],
        step_size: int = 1,
        stacked_on: Sequence[Player] = tuple(),
        stacked_by: Sequence[Player] = tuple(),
        first_step: bool = False,
        last_step: bool = False,
    ) -> list[tuple[Player, int, int]]:
        if first_step is True and len(stacked_by) > 0:
            self.ability_active = rand.choices((False, True), (0.6, 0.4))[0]

        if self.ability_active is True:
            # Move to top of stack, then step forwards
            actions = [(self, 0, None), (self, step_size, None)]
            self.ability_active = False
        else:
            actions = super().calculate_actions(
                round_order,
                current_rank,
                step_size,
                stacked_on,
                stacked_by,
                first_step,
                last_step,
            )
        return actions


class CamellyaCube(Player):
    """Camellya. There is a 50%% chance of triggering this effect on Camellya's turn. For every other cube on the same pad besides Camellya, she advances 1 extra pad, while other Cubes stay in place."""

    def __init__(self, position: int = 0):
        super().__init__(name="Camellya", position=position)
        self.ability_active = False

    def calculate_actions(
        self,
        round_order: Sequence[Player],
        current_rank: tuple[int, int],
        step_size: int = 1,
        stacked_on: Sequence[Player] = tuple(),
        stacked_by: Sequence[Player] = tuple(),
        first_step: bool = False,
        last_step: bool = False,
    ) -> list[tuple[Player, int, int]]:
        if first_step and self.ability_active is True:
            self.ability_active = rand.choice((False, True))

        if self.ability_active:
            self.ability_active = False
            num_others = len(stacked_on) + len(stacked_by)
            actions = [(self, num_others, None), (self, step_size, None)]
        else:
            actions = super().calculate_actions(
                round_order,
                current_rank,
                step_size,
                stacked_on,
                stacked_by,
                first_step,
                last_step,
            )
        return actions


class CarlottaCube(Player):
    """Carlotta. There is a 28%% chance to advance twice with one rolled number."""

    def __init__(self, position: int = 0):
        super().__init__(name="Carlotta", position=position)

    def roll(
        self,
        round_order: Sequence[Player],
        stacked_on: Sequence[Player] = tuple(),
        stacked_by: Sequence[Player] = tuple(),
    ) -> tuple[int, int]:
        standard_roll = super().roll(round_order, stacked_on, stacked_by)
        bonus_roll = rand.choices((standard_roll[0], 0), (0.28, 0.72))[0]
        return (standard_roll[0], bonus_roll)


class CalcharoCube(Player):
    """Calcharo. If Calcharo is the last to move, he advances 3 extra pads."""

    def __init__(self, position: int = 0):
        super().__init__(name="Calcharo", position=position)

    def roll(
        self,
        round_order: Sequence[Player],
        stacked_on: Sequence[Player] = tuple(),
        stacked_by: Sequence[Player] = tuple(),
    ) -> tuple[int, int]:
        standard_roll = super().roll(round_order, stacked_on, stacked_by)
        if round_order.index(self) == len(round_order) - 1:
            bonus_roll = 3
        else:
            bonus_roll = 0
        return (standard_roll[0], bonus_roll)


class ChangliCube(Player):
    """Changli. If other cubes are stacked below Changli, there is a 65%% chance she will be the last to move in the next turn."""

    def __init__(self, position: int = 0):
        super().__init__(name="Changli", position=position)
        self.ability_active = False

    def post_round(
        self,
        round_order: Sequence[Player],
        current_rank: tuple[int, int],
        stacked_on: Sequence["Player"] = tuple(),
        stacked_by: Sequence["Player"] = tuple(),
    ) -> dict[str, list]:
        
        if len(stacked_on) > 0:
            self.ability_active = rand.choices((False,True), (0.35,0.65))
        if self.ability_active:
            return {"actions":[], "next_round_order":[[self, None]]}
        else:
            return super().post_round(round_order, current_rank)


class ShorekeeperCube(Player):
    """Shorekeeper. The dice will only roll a 2 or 3"""

    def __init__(self, position: int = 0):
        super().__init__(name="Shorekeeper", position=position)

    def roll(self, round_order: Sequence[Player], stacked_on: Sequence[Player] = tuple(), stacked_by: Sequence[Player] = tuple()) -> tuple[int, int]:
        return (rand.choice((2,3)), 0)


def main():
    """For testing."""
    print(type(RocciaCube()))


if __name__ == "__main__":
    main()
