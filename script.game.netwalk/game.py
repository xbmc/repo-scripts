#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2013 Tristan Fischer (sphere@dersphere.de)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import os
import random
import time
import thread
import string
import sys

import xbmc
import xbmcaddon
import xbmcgui

addon = xbmcaddon.Addon()

ADDON_NAME = addon.getAddonInfo('name')
ADDON_PATH = addon.getAddonInfo('path').decode('utf-8')
MEDIA_PATH = os.path.join(
    xbmc.translatePath(ADDON_PATH),
    'resources',
    'skins',
    'default',
    'media'
)

STRINGS = {
    'you_won_head': 32007,
    'you_won_text': 32008,
    'exit_head': 32009,
    'exit_text': 32012
}


COLUMNS = 9
ROWS = 9

# bits to detect the connection directions, UP=1, UP+LEFT=9, ...
UP = 1
RIGHT = 2
DOWN = 4
LEFT = 8
DIRECTIONS = [UP, RIGHT, DOWN, LEFT]

WIRE = 0
SERVER = 1
TERMINAL = 2
TYPES = [WIRE, SERVER, TERMINAL]

# TODO: Row and column is switched but everything works atm, needs fix later


def opposite(direction):
    '''helper which returns the opposite direction.
    Examples:
     - if UP (1) is passed, return DOWN (4)
     - if DOWN+LEFT (12) is passed, return UP+RIGHT (3)'''
    opposite_direction = direction * 4
    if opposite_direction > 8:
        opposite_direction = opposite_direction / 16
    return opposite_direction


def get_image(filename):
    return os.path.join(MEDIA_PATH, filename)


def _(string_id):
    if string_id in STRINGS:
        return addon.getLocalizedString(STRINGS[string_id])
    else:
        xbmc.log('String is missing: %s' % string_id, level=xbmc.LOGDEBUG)
        return string_id


def log(msg):
    xbmc.log('[ADDON][%s] %s' % (ADDON_NAME, msg.encode('utf-8')),
             level=xbmc.LOGNOTICE)


class Tile(object):

    def __init__(self, row, column, grid, width, height):
        self._row = row
        self._column = column
        self.grid = grid
        self._x_position = self.grid._x_position + width * row
        self._y_position = self.grid._y_position + height * column
        self._width = width
        self._height = height
        self.button_control = None
        self.image_control = None
        self.reset()

    def reset(self):
        self.type = WIRE
        self.connections = 0
        self._is_connected = False
        self.set_is_locked(False)

    def set_type(self):
        # this needs to be called AFTER tree is grown (Grid.build_tree())!
        # if already set to server, don't change
        if self.type == SERVER:
            pass
        # elif it has only one connection
        elif self.connections in DIRECTIONS:
            # make it a terminal
            self.type = TERMINAL
        # else this tile is still a wire (it has more than one connection)
        else:
            pass
        # store the correct solution
        self._correct_connections = int(self.connections)

    def build_controls(self):
        self.button_control = xbmcgui.ControlButton(
            x=self._x_position,
            y=self._y_position,
            width=self._width,
            height=self._height,
            label='',
            focusTexture=get_image('selected.png'),
            noFocusTexture=get_image('not_selected.png'),
        )
        self.image_control = xbmcgui.ControlImage(
            x=self._x_position,
            y=self._y_position,
            width=self._width,
            height=self._height,
            filename=get_image('empty.png'),
        )

    def neighbor_at(self, direction):
        if direction == UP:
            return self.up
        elif direction == RIGHT:
            return self.right
        elif direction == DOWN:
            return self.down
        elif direction == LEFT:
            return self.left

    def update_image(self):
        self.image_control.setImage(self.image_file)

    def rotate_cw(self):
        # shift all bits to the right
        if not self._is_locked:
            new_connections = self.connections << 1
            if new_connections > 15:
                new_connections -= 15
            self.connections = new_connections
            return True

    def rotate_ccw(self):
        # shift all bits to the left
        if not self._is_locked:
            new_connections = self.connections >> 1
            if self.connections & UP:
                new_connections += LEFT
            self.connections = new_connections
            return True

    def set_button_navigation(self):
        self.button_control.setNavigation(
            up=self.up.button_control,
            right=self.right.button_control,
            down=self.down.button_control,
            left=self.left.button_control,
        )

    def get_is_connected(self):
        return self.type == SERVER or self._is_connected

    def set_is_connected(self, value):
        self._is_connected = value

    is_connected = property(get_is_connected, set_is_connected)

    def get_is_locked(self):
        return self._is_locked

    def set_is_locked(self, value):
        self._is_locked = value
        if self.image_control:
            diffuse = 'EE55EE55' if self._is_locked else 'FFFFFFFF'
            self.image_control.setColorDiffuse(diffuse)

    is_locked = property(get_is_locked, set_is_locked)

    @property
    def pos(self):
        return self._row, self._column

    @property
    def button_id(self):
        return self.button_control.getId()

    @property
    def up(self):
        return self.grid.at(self._row, self._column - 1)

    @property
    def right(self):
        return self.grid.at(self._row + 1, self._column)

    @property
    def down(self):
        return self.grid.at(self._row, self._column + 1)

    @property
    def left(self):
        return self.grid.at(self._row - 1, self._column)

    @property
    def image_file(self):
        connected = 'c' if self.is_connected else ''
        filename = '%d_%d%s.png' % (self.type, self.connections, connected)
        return get_image(filename)

    @property
    def has_free_neighbor(self):
        for direction in DIRECTIONS:
            if self.neighbor_at(direction).connections == 0:
                return True
        return False

    @property
    def num_connections(self):
        num = len([d for d in DIRECTIONS if d & self.connections])
        return num

    def __str__(self):
        return '(%d, %d)' % (self._row, self._column)


class Grid(object):

    def __init__(self, rows, columns, x_position, y_position, width, height):
        self._rows = rows
        self._columns = columns
        self._x_position = x_position
        self._y_position = y_position
        self._width = width
        self._height = height
        self._tiles = []
        self._root_tile = None
        self._all_correct = False

    def generate_tiles(self):
        tile_width = self._width / self._columns
        tile_height = self._height / self._rows
        for row in xrange(self._rows):
            for column in xrange(self._columns):
                tile = Tile(row, column, self, tile_width, tile_height)
                self._tiles.append(tile)

    def build_tree(self):
        '''Pick a random tile, set is at root tile (the server).
        Build a tree of connections from the root tile until all tiles have
        exactly one connection back to the root.'''
        for tile in self._tiles:
            tile.reset()
        active_tiles = []
        # get random tile and make it the server
        self._root_tile = random.choice(self._tiles)
        self._root_tile.type = SERVER
        # add this server to the active tiles because it has free neighbors ;)
        active_tiles.append(self._root_tile)
        # as long as there are still active tiles
        while active_tiles:
            # pick any of these
            selected_tile = random.choice(active_tiles)
            # find neighbor tiles which are empty (have no connections)
            for direction in DIRECTIONS:
                if selected_tile.neighbor_at(direction).connections == 0:
                    selected_neighbor = selected_tile.neighbor_at(direction)
                    # we will connect selected_tile and selected_neighbor
                    selected_tile.connections += direction
                    selected_neighbor.connections = opposite(direction)
                    # add selected_neighbor to active_tiles
                    active_tiles.append(selected_neighbor)
                    # filter out chells which can't have new connections
                    # or  have already 3 connections
                    active_tiles = [
                        t for t in active_tiles if t.has_free_neighbor
                        and t.num_connections < 3
                    ]
                    break
        for tile in self._tiles:
            tile.set_type()
        log('Done, there is no tile with a free neighbor')

    def randomize_tree(self):
        self._target_moves = 0
        for tile in self._tiles:
            movement = random.choice([tile.rotate_cw, tile.rotate_ccw])
            for turn in xrange(random.randint(0, 2)):
                movement()
                self._target_moves += 1

    def update_connection_states(self):
        '''Mark all tiles as disconnected (except the root tile)
        Follow all connections from the root tile (the server) and mark the
        tiles on the tree as connected'''
        # clear all tiles' is_connected state
        for tile in self._tiles:
            tile.is_connected = False

        visited_tiles = set()
        to_visit_tiles = set()

        # the root tile is a server so it is definitely connected
        # it is our start point for the walk
        to_visit_tiles.add(self._root_tile)
        while to_visit_tiles:
            # put any of the definitely connected tiles
            active_tile = to_visit_tiles.pop()
            # set this tile's connection state to True
            active_tile.is_connected = True
            for direction in DIRECTIONS:
                # check if this tile has a connection to this direction
                if active_tile.connections & direction:
                    # check if the neighbor has an opposite connection
                    neighbor = active_tile.neighbor_at(direction)
                    if neighbor.connections & opposite(direction):
                        # if the neighbor wasn't already checked, do that later
                        if neighbor not in visited_tiles:
                            to_visit_tiles.add(neighbor)
                        # add the picked cell to the already visitied list
                        # to avoid endless loops
                        visited_tiles.add(active_tile)
        for tile in self._tiles:
            # update the images because some have changed their status
            tile.update_image()
        self._all_correct = len(visited_tiles) == len(self._tiles)
        log('Done with update_connection_states walk')

    @property
    def tiles(self):
        return self._tiles

    @property
    def root_tile(self):
        return self._root_tile

    @property
    def all_correct(self):
        return self._all_correct

    @property
    def target_moves(self):
        return self._target_moves

    def at(self, row, column):
        a = ((row + self._rows) % self._rows) * self._columns
        b = ((column + self._columns) % self._columns)
        idx = a + b
        return self._tiles[idx]


class Game(xbmcgui.WindowXML):
    CONTROL_ID_GRID = 3001
    CONTROL_ID_RESTART = 3002
    CONTROL_ID_MOVES_COUNT = 3003
    CONTROL_ID_TARGET_COUNT = 3004
    CONTROL_ID_TIME = 3005
    CONTROL_ID_EXIT = 3006
    CONTROL_ID_GAME_ID = 3007
    AID_EXIT = [9, 13]  # exit the game
    AID_ENTER = [7, 100]  # rotate the selected tile clockwise
    AID_BACK = [10]  # rotate the selected tile counter clockwise
    AID_INFO = [11]  # lock the selected tile
    AID_SPACE = [12]  # lock the selected tile
    AID_MIDDLE_MOUSE = [102]  # lock the selected tile
    AID_LOCK = AID_INFO + AID_SPACE + AID_MIDDLE_MOUSE

    def onInit(self):
        # init vars
        self._tile_button_ids = {}
        self._game_in_progress = False
        self._game_id = ''
        # get controls
        self.grid_control = self.getControl(self.CONTROL_ID_GRID)
        self.target_control = self.getControl(self.CONTROL_ID_TARGET_COUNT)
        self.moves_control = self.getControl(self.CONTROL_ID_MOVES_COUNT)
        self.time_control = self.getControl(self.CONTROL_ID_TIME)
        self.game_id_control = self.getControl(self.CONTROL_ID_GAME_ID)
        self.new_game_control = self.getControl(self.CONTROL_ID_RESTART)
        # init the grid
        self.grid = self.get_grid()
        self.grid.generate_tiles()
        self.add_tile_controls()
        # start the timer thread
        thread.start_new_thread(self.timer_thread, ())
        # start the game
        self.start_game()

    def onAction(self, action):
        action_id = action.getId()
        focus_id = self.getFocusId()
        if self._game_in_progress and focus_id in self._tile_button_ids:
            tile = self._tile_button_ids[self.getFocusId()]
            if action_id in self.AID_ENTER:
                if not tile.is_locked:
                    tile.rotate_ccw()
                    self.movement_done()
            elif action_id in self.AID_BACK:
                if not tile.is_locked:
                    tile.rotate_cw()
                    self.movement_done()
            elif action_id in self.AID_LOCK:
                tile.is_locked = not tile.is_locked
            if self.grid.all_correct:
                self.game_over()
        if action_id in self.AID_EXIT:
            self.exit()

    def onFocus(self, control_id):
        pass

    def onClick(self, control_id):
        if control_id == self.CONTROL_ID_RESTART:
            self.start_game()
        elif control_id == self.CONTROL_ID_EXIT:
            self.exit()

    def get_grid(self):
        # get xml defined position and dimension for the grid
        x, y = self.grid_control.getPosition()
        width = self.grid_control.getWidth()
        height = self.grid_control.getHeight()
        return Grid(ROWS, COLUMNS, x, y, width, height)

    def start_game(self, game_id=None):
        if not game_id:
            random.seed()
            game_id = ''.join(
                random.choice(string.ascii_uppercase) for n in xrange(15)
            )
        self._game_id = game_id
        random.seed(self._game_id)
        self.grid.build_tree()
        self.grid.randomize_tree()
        self.grid.update_connection_states()
        self._game_in_progress = True
        self._start_time = time.time()
        self._moves = 0
        self._target_moves = self.grid.target_moves
        self.moves_control.setLabel(str(self._moves))
        self.target_control.setLabel(str(self._target_moves))
        self.game_id_control.setLabel(str(self._game_id))

    def timer_thread(self):
        while not xbmc.abortRequested:
            if self._game_in_progress:
                game_time = time.time() - self._start_time
                self.time_control.setLabel(str(int(game_time)))
            xbmc.sleep(1000)

    def add_tile_controls(self):
        # let the tiles generate their button and image control
        for tile in self.grid.tiles:
            tile.build_controls()
        # add the controls to the window
        self.addControls([t.image_control for t in self.grid.tiles])
        self.addControls([t.button_control for t in self.grid.tiles])
        # store the button_id in a dict for later resolving and set up the
        # tile's button navigation
        for tile in self.grid.tiles:
            self._tile_button_ids[tile.button_id] = tile
            tile.set_button_navigation()
        # set onleft on the new game button to the upper right tile
        upper_right_tile = self.grid.at(ROWS - 1, 0)
        self.new_game_control.controlLeft(upper_right_tile.button_control)
        # set onRight on the upper right tile to the new game button
        upper_right_tile.button_control.controlRight(self.new_game_control)

    def clear_tile_controls(self):
        self.removeControls([t.button_control for t in self.grid.tiles])
        self.removeControls([t.image_control for t in self.grid.tiles])
        while self.grid.tiles:
            tile = self.grid.tiles.pop()
            del tile

    def game_over(self):
        self._game_in_progress = False
        dialog = xbmcgui.Dialog()
        dialog.ok(_('you_won_head'), _('you_won_text'))

    def exit(self):
        dialog = xbmcgui.Dialog()
        confirmed = dialog.yesno(_('exit_head'), _('exit_text'))
        if confirmed:
            self.clear_tile_controls()
            self.grid = None
            self.close()

    def movement_done(self):
        self.grid.update_connection_states()
        self._moves += 1
        self.moves_control.setLabel(str(self._moves))


if __name__ == '__main__':
    game = Game(
        'script-%s-main.xml' % ADDON_NAME,
        ADDON_PATH,
        'default',
        '720p'
    )
    game.doModal()
    del game

sys.modules.clear()
