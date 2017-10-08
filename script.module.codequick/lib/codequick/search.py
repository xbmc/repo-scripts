# -*- coding: utf-8 -*-
from __future__ import absolute_import

# Package imports
from codequick.storage import PersistentList
from codequick.support import dispatcher
from codequick.listing import Listitem
from codequick.utils import keyboard
from codequick.route import Route

# Localized string Constants
ENTER_SEARCH_STRING = 16017
REMOVE = 1210
SEARCH = 137


@Route.register
class SavedSearches(Route):
    """
    Class used to list all saved searches for the addon that called it.

    Useful to add search support to addon that will also keep track of previous searches.
    Also contains option via context menu to remove old search terms.
    """

    def __init__(self):
        super(SavedSearches, self).__init__()

        # Persistent list of currently saved searches
        self.search_db = PersistentList(u"_searches.pickle")

    def run(self, remove=None, search=False, **extras):
        """List all saved searches."""

        # Update the current listings only if a serch term was removed or added
        if remove or search:
            self.update_listing = True

        # Remove search term from saved searches if remove argument was given
        if remove in self.search_db:
            self.search_db.remove(remove)
            self.search_db.flush()

        # Show search dialog if search argument is True, or if there is no search term saved
        elif (not self.search_db or search) and not self.search_dialog():
            return False

        # List all saved search terms
        return self.list_terms(extras)

    def search_dialog(self):
        """Show dialog for user to enter a new search term."""
        search_term = keyboard(self.localize(ENTER_SEARCH_STRING))
        if search_term and search_term not in self.search_db:
            self.search_db.append(search_term)
            self.search_db.flush()

        # Return True if text was returned
        return bool(search_term)

    def list_terms(self, extras):
        """
        List all saved searches.

        :returns: A generator of listitems.
        :rtype: :class:`types.GeneratorType`
        """
        # Add listitem for adding new search terms
        search_item = Listitem()
        search_item.label = u"[B]%s[/B]" % self.localize(SEARCH)
        search_item.set_callback(self, search=True, **extras)
        search_item.art.global_thumb("search_new.png")
        yield search_item

        # Set the callback function to the route that was given
        callback_params = extras.copy()
        callback = dispatcher[callback_params.pop("route")].callback

        # Prefetch the localized string for the context menu lable
        str_remove = self.localize(REMOVE)

        # List all saved searches
        for search_term in self.search_db:
            item = Listitem()
            item.label = search_term.title()

            # Creatre Context Menu item for removing search term
            item.context.container(str_remove, self, remove=search_term, **extras)

            # Update params with full url and set the callback
            item.params.update(callback_params, search_query=search_term)
            item.set_callback(callback)
            yield item

        self.search_db.close()
