""" Default menu """

from resources.lib import helper
from resources.lib import sync
from resources.lib.connection import Connection
from resources.lib.connection import Http
from resources.lib.gui import dialog
from resources import config


def menu():

    if not helper.is_settings_okey():
        helper.settings.openSettings()
        return

    # [Movie, TV, Settings]
    options = [helper.language(32009), helper.language(32010), helper.language(32011)]
    connection = Connection(
        Http(config.__BASE_URL__)
    )

    while True:
        select = dialog.create_select(options)
        if select == -1:
            return
        else:
            if select == 0:  # Movie
                try:
                    sync.Movies(connection).sync()
                except Exception as error:
                    dialog.create_error_dialog(str(error))
            elif select == 1:  # TV
                try:
                    sync.Series(connection).sync()
                except Exception as error:
                    dialog.create_error_dialog(str(error))
            elif select == 2:  # Settings
                helper.settings.openSettings()

menu()
