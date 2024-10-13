#!/usr/bin/env python
import random

import pyglet

TILE_SIZE = 88
TILE_MARGIN = 6
TILE_FONT_SIZE = 24
UI_HEIGHT = 100

TILE_FULL_SIZE = TILE_SIZE + TILE_MARGIN * 2
WIDTH = TILE_FULL_SIZE * 4
HEIGHT = TILE_FULL_SIZE * 4 + UI_HEIGHT

ANIMATION_DURATION_MS = {
    "enter": 150,
    "move": 150,
    "merge": 150,
}

pyglet.font.add_file("res/FiraMono-Regular.ttf")

window = pyglet.window.Window(WIDTH, HEIGHT, caption="2048")
pyglet.gl.glClearColor(0.9, 0.9, 0.9, 1)
fps_display = pyglet.window.FPSDisplay(window=window)


class Game:
    def __init__(self):
        self.batch = pyglet.graphics.Batch()
        self.tiles = {}
        self.merged_tiles = []
        self.pending = []

    def start(self):
        for _ in range(2):
            pos, tile = self.new_tile()
            tile.show()
            tile.animate_enter(pos)

    def update(self, dt):
        if self.merged_tiles and all(tile.animation is None for tile in self.merged_tiles):
            for tile in self.merged_tiles:
                tile.delete()
            self.merged_tiles = []
        if self.pending and not self.merged_tiles and all(tile.animation is None for tile in self.tiles.values()):
            for show, animate, pos in self.pending:
                show()
                animate(pos)
            self.pending = []
        for tile in self.tiles.values():
            tile.update(dt)
        for tile in self.merged_tiles:
            tile.update(dt)

    def animating(self):
        return any(tile.animation is not None for tile in self.tiles.values()) or self.pending

    def new_tile(self):
        assert len(self.tiles) < 4 * 4
        while True:
            row, col = random.randrange(4), random.randrange(4)  # noqa: S311
            if (row, col) not in self.tiles:
                break
        if random.random() < 0.9:  # noqa: S311, PLR2004
            n = 2
        else:
            n = 4
        tile = Tile(n, self.batch)
        self.tiles[row, col] = tile
        return (row, col), tile

    def slide(self, direction):
        print(self.tiles)  # noqa: T201
        if direction in ("up", "right"):
            alpha = 1
        else:
            alpha = -1
        effective = False
        merged = set()
        for i in range(4):
            for jj in range(1, 4):
                if direction in ("up", "right"):
                    j = 4 - jj - 1
                else:
                    j = jj
                if direction in ("left", "right"):
                    row, col = i, j
                else:
                    row, col = j, i
                if (row, col) not in self.tiles:
                    continue
                tile = self.tiles[row, col]

                merge_row, merge_col = row, col
                for _ in range(jj):
                    if direction in ("left", "right"):
                        merge_col += alpha
                    else:
                        merge_row += alpha
                    if (merge_row, merge_col) in self.tiles:
                        break
                if (
                    (merge_row, merge_col) not in merged
                    and (merge_row, merge_col) in self.tiles
                    and self.tiles[merge_row, merge_col].n == tile.n
                ):
                    print("merge", (row, col), "->", (merge_row, merge_col))  # noqa: T201
                    effective = True
                    merged_tile = Tile(tile.n * 2, self.batch)

                    self.tiles[row, col].animate_move((merge_row, merge_col))
                    self.pending.append((merged_tile.show, merged_tile.animate_merge, (merge_row, merge_col)))
                    self.merged_tiles += [self.tiles[row, col], self.tiles[merge_row, merge_col]]

                    del self.tiles[row, col]
                    self.tiles[merge_row, merge_col] = merged_tile
                    merged.add((merge_row, merge_col))

                    continue

                move_row, move_col = merge_row, merge_col
                if (move_row, move_col) in self.tiles:
                    if direction in ("left", "right"):
                        move_col -= alpha
                    else:
                        move_row -= alpha
                if (move_row, move_col) != (row, col):
                    print("move", (row, col), "->", (move_row, move_col))  # noqa: T201
                    effective = True
                    self.tiles[row, col].animate_move((move_row, move_col))
                    self.tiles[move_row, move_col] = self.tiles[row, col]
                    del self.tiles[row, col]

        if effective:
            pos, tile = self.new_tile()
            if len(self.tiles) == 4 * 4:
                raise AssertionError("game over")  # TODO: ending scene  # noqa: TRY003, EM101
            self.pending.append((tile.show, tile.animate_enter, pos))
        print(self.tiles)  # noqa: T201


def shape_pos(pos):
    row, col = pos
    return TILE_FULL_SIZE * col + TILE_MARGIN + TILE_SIZE / 2, TILE_FULL_SIZE * row + TILE_MARGIN + TILE_SIZE / 2


def color(h):
    return tuple(int(h[i : i + 2], 16) for i in range(1, 6, 2))


COLOR_MAP = {
    1 << (i + 1): color(h)
    for i, h in enumerate(
        [
            "#1f77b4",
            "#ff7f0e",
            "#2ca02c",
            "#d62728",
            "#9467bd",
            "#8c564b",
            "#e377c2",
            "#7f7f7f",
            "#bcbd22",
            "#17becf",
        ]
    )
}


class Tile:
    def __init__(self, n, batch):
        self.n = n
        self.shape = pyglet.shapes.Rectangle(0, 0, 0, 0, color=COLOR_MAP.get(n, (16, 16, 16)), batch=batch)
        self.text = pyglet.text.Label(str(n), font_name="Fira Mono", anchor_x="center", anchor_y="center", batch=batch)
        self.animation = None

    def __repr__(self):
        return repr({"n": self.n, "animation": self.animation})

    def delete(self):
        self.shape.delete()
        self.text.delete()

    def hide(self):
        self.shape.visible = False
        self.text.visible = False

    def show(self):
        self.shape.visible = True
        self.text.visible = True

    def animate_enter(self, pos):
        assert self.animation is None
        self.animation = {"type": "enter", "step": 0}
        self.shape.position = shape_pos(pos)
        self.shape.width = self.shape.height = 0
        self.text.x = self.shape.x
        self.text.y = self.shape.y
        self.text.font_size = 0

    def animate_move(self, pos):
        assert self.animation is None
        x, y = shape_pos(pos)
        x_offset, y_offset = x - self.shape.x, y - self.shape.y
        self.animation = {
            "type": "move",
            "step": 0,
            "shape_pos": self.shape.position,
            "text_pos": self.text.position,
            "pos_offset": (x_offset, y_offset),
        }

    def animate_merge(self, pos):
        assert self.animation is None
        self.shape.position = shape_pos(pos)
        self.shape.anchor_position = (TILE_SIZE / 2, TILE_SIZE / 2)
        self.text.x = self.shape.x
        self.text.y = self.shape.y
        self.animation = {"type": "merge", "step": 0}

    def update(self, dt):
        if self.animation is None:
            return

        ty = self.animation["type"]
        step = min(self.animation["step"] + dt / (ANIMATION_DURATION_MS[ty] / 1000), 1)
        match ty:
            case "enter":
                self.shape.anchor_position = (TILE_SIZE / 2 * step, TILE_SIZE / 2 * step)
                self.shape.width = self.shape.height = TILE_SIZE * step
                self.text.font_size = TILE_FONT_SIZE * step
            case "move":
                x_offset, y_offset = self.animation["pos_offset"]
                x, y = self.animation["shape_pos"]
                self.shape.position = (x + x_offset * step, y + y_offset * step)
                x, y, z = self.animation["text_pos"]
                self.text.position = (x + x_offset * step, y + y_offset * step, z)
            case "merge":
                factor = (0.5 - abs(step - 0.5)) / 5  # 0 @ step=0 -> 0.1 @ step=0.5 -> 0 @ step=1
                tile_size = TILE_SIZE * (1 + factor)
                self.shape.anchor_position = (tile_size / 2, tile_size / 2)
                self.shape.width = self.shape.height = tile_size
                self.text.font_size = TILE_FONT_SIZE * (1 + factor)

        if step < 1:
            self.animation["step"] = step
        else:
            self.animation = None


game = Game()
game.start()


@window.event
def on_draw():
    window.clear()
    game.batch.draw()
    fps_display.draw()


@window.event
def on_key_press(symbol, _modifier):
    if game.animating():
        return
    match symbol:
        case pyglet.window.key.W:
            game.slide("up")
        case pyglet.window.key.A:
            game.slide("left")
        case pyglet.window.key.S:
            game.slide("down")
        case pyglet.window.key.D:
            game.slide("right")


pyglet.clock.schedule_interval(game.update, 1 / 120)
pyglet.app.run()
