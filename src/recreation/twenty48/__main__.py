#!/usr/bin/env python
import random

import pyglet

TILE_SIZE = 100
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
    "over_fade": 2000,
}

pyglet.resource.add_font("res/FiraMono-Regular.ttf")

window = pyglet.window.Window(WIDTH, HEIGHT, caption="2048")
pyglet.gl.glClearColor(0.9, 0.9, 0.9, 1)
# window.set_vsync(True)
fps_display = pyglet.window.FPSDisplay(window=window)


class Game:
    def __init__(self):
        self.batch = pyglet.graphics.Batch()
        self.tiles = {}
        self.merged_tiles = []
        self.pending = []
        self.over_batch = pyglet.graphics.Batch()
        self.over_overlay = OverOverlay(self.over_batch)

    def start(self):
        for _ in range(2):
            pos, tile = self.new_tile()
            tile.show()
            tile.animate_enter(pos)
        self.over_overlay.toggle(False)

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

        self.over_overlay.update(dt)
        if not self.over_overlay.toggled and not self.animating() and self.over():
            print("Vegetable")  # noqa: T201
            self.over_overlay.toggle(True)
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
                    merged_tile.hide()
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
            tile.hide()
            self.pending.append((tile.show, tile.animate_enter, pos))
        print(self.tiles)  # noqa: T201

    def over(self):
        return len(self.tiles) == 4 * 4 and all(
            self.tiles[row, col].n not in (self.tiles[row + 1, col].n, self.tiles[row, col + 1].n)
            for row in range(3)
            for col in range(3)
        )


def shape_pos(pos):
    row, col = pos
    return TILE_FULL_SIZE * col + TILE_MARGIN, TILE_FULL_SIZE * row + TILE_MARGIN, 0


COLOR_MAP = {
    1 << (i + 1): h
    for i, h in enumerate(
        # tab10 from matplotlib
        ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
    )
}


def tile_shape_image(shape_image, color):
    from io import BytesIO

    from PIL import Image

    shape_im = Image.open(shape_image)
    color_im = Image.new("RGBA", shape_im.size, color=color)
    im = Image.new("RGBA", shape_im.size, color=(0, 0, 0, 0))
    im.paste(color_im, mask=shape_im)
    buf = BytesIO()
    im.save(buf, format="png")
    return pyglet.image.load("shape.png", buf)


tile_image = pyglet.resource.file("res/TileShape.png")
tile_shape_images = {n: tile_shape_image(tile_image, color) for n, color in COLOR_MAP.items()}
tile_shape_image_fallback = tile_shape_image(tile_image, "#111")


class Tile:
    def __init__(self, n, batch):
        self.n = n
        # self.shape = pyglet.shapes.Rectangle(0, 0, 0, 0, color=COLOR_MAP.get(n, (16, 16, 16)), batch=batch)
        self.shape = pyglet.sprite.Sprite(tile_shape_images.get(n), batch=batch, subpixel=True)
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
        pos = shape_pos(pos)
        x, y, z = pos
        self.shape.position = (x + TILE_SIZE / 2, y + TILE_SIZE / 2, z)
        self.shape.width = self.shape.height = 0
        self.text.x = self.shape.x
        self.text.y = self.shape.y
        self.text.font_size = 0
        self.animation = {"type": "enter", "step": 0, "shape_pos": pos}

    def animate_move(self, pos):
        assert self.animation is None
        x, y, _z = shape_pos(pos)
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
        pos = shape_pos(pos)
        self.shape.position = pos
        # self.shape.anchor_position = (TILE_SIZE / 2, TILE_SIZE / 2)
        self.text.x = self.shape.x + TILE_SIZE / 2
        self.text.y = self.shape.y + TILE_SIZE / 2
        self.animation = {"type": "merge", "step": 0, "shape_pos": pos}

    def update(self, dt):
        if self.animation is None:
            return

        ty = self.animation["type"]
        step = min(self.animation["step"] + dt / (ANIMATION_DURATION_MS[ty] / 1000), 1)
        match ty:
            case "enter":
                x, y, z = self.animation["shape_pos"]
                offset = TILE_SIZE / 2 * (1 - step)
                self.shape.position = (x + offset, y + offset, z)
                self.shape.width = self.shape.height = TILE_SIZE * step
                self.text.font_size = TILE_FONT_SIZE * step
            case "move":
                x_offset, y_offset = self.animation["pos_offset"]
                x, y, z = self.animation["shape_pos"]
                self.shape.position = (x + x_offset * step, y + y_offset * step, z)
                x, y, z = self.animation["text_pos"]
                self.text.position = (x + x_offset * step, y + y_offset * step, z)
            case "merge":
                factor = (0.5 - abs(step - 0.5)) / 5  # 0 @ step=0 -> 0.1 @ step=0.5 -> 0 @ step=1
                offset = -TILE_SIZE / 2 * factor
                x, y, z = self.animation["shape_pos"]
                self.shape.position = (x + offset, y + offset, z)
                tile_size = TILE_SIZE * (1 + factor)
                # self.shape.anchor_position = (tile_size / 2, tile_size / 2)
                self.shape.width = self.shape.height = tile_size
                self.text.font_size = TILE_FONT_SIZE * (1 + factor)

        if step < 1:
            self.animation["step"] = step
        else:
            self.animation = None


class OverOverlay:
    def __init__(self, batch):
        self.shape = pyglet.shapes.Rectangle(0, 0, WIDTH, HEIGHT - UI_HEIGHT, color=(255, 255, 255), batch=batch)
        self.text = pyglet.text.Label(
            "Game Over",
            WIDTH / 2,
            (HEIGHT - UI_HEIGHT) / 2,
            anchor_x="center",
            anchor_y="center",
            font_name="Fira Mono",
            font_size=32,
            color=(0, 0, 0),
            batch=batch,
        )
        self.toggled = False
        self.animation_step = None

    def toggle(self, visible):
        self.shape.visible = visible
        self.text.visible = visible
        if visible and not self.toggled:
            self.shape.opacity = 0
            self.text.opacity = 0
            self.animation_step = 0
        self.toggled = visible

    def update(self, dt):
        if self.animation_step is None:
            return
        step = min(self.animation_step + dt / (ANIMATION_DURATION_MS["over_fade"] / 1000), 1)
        opacity = int(step * 255 * 0.8)
        self.shape.opacity = opacity
        self.text.opacity = opacity
        if step < 1:
            self.animation_step = step
        else:
            self.animation_step = None


game = Game()
game.start()


@window.event
def on_draw():
    window.clear()
    game.batch.draw()
    game.over_batch.draw()
    fps_display.draw()


@window.event
def on_key_press(symbol, _modifier):
    if game.animating():
        return
    if not game.over():
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
