# -*- coding: utf-8 -*-
from __future__ import absolute_import

# Package imports
from codequick.storage import PersistentList
from codequick.support import dispatcher
from codequick.listing import Listitem
from codequick.utils import keyboard
from codequick.route import Route, validate_listitems

# Localized string Constants
ENTER_SEARCH_STRING = 16017
REMOVE = 1210
SEARCH = 137

# Name of the database file
SEARCH_DB = u"_searches.pickle"


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
        self.search_db = PersistentList(SEARCH_DB)
        self.register_delayed_callback(self.close)

    def run(self, remove_entry=None, search=False, first_load=False, **extras):
        """List all saved searches."""

        # Remove search term from saved searches
        if remove_entry and remove_entry in self.search_db:
            self.update_listing = True
            self.search_db.remove(remove_entry)
            self.search_db.flush()

        # Show search dialog if search argument is True, or if there is no search term saved
        # First load is used to only allow auto search to work when first loading the saved search container.
        # Fixes an issue when there is no saved searches left after removing them.
        elif search or (first_load is True and not self.search_db):
            self.cache_to_disc = True
            search_term = keyboard(self.localize(ENTER_SEARCH_STRING))
            if search_term:
                return self.redirect_search(search_term, extras)
            elif not self.search_db:
                return False
            else:
                self.update_listing = True

        # List all saved search terms
        return self.list_terms(extras)

    def redirect_search(self, search_term, extras):
        """
        Checks if searh term returns valid results before adding to saved searches.
        Then directly farward the results to kodi.

        :param search_term: The serch term used to search for results.
        :param extras: Extra parameters that will be farwarded on to the callback function.
        :return: List if valid search results
        """
        self.category = search_term.title()
        callback_params = extras.copy()
        callback_params["search_query"] = search_term
        route = callback_params.pop("route")
        dispatcher.selector = route

        # Fetch search results from callback
        callback = dispatcher.current_route.callback
        listitems = callback(self, **callback_params)

        # Check that we have valid listitems
        valid_listitems = validate_listitems(listitems)

        # Add the search term to database and return the list of results
        if valid_listitems:
            if search_term not in self.search_db:  # pragma: no branch
                self.search_db.append(search_term)
                self.search_db.flush()

            return valid_listitems
        else:
            # Return False to indicate failure
            return False

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
            item.context.container(self, str_remove, remove_entry=search_term, **extras)

            # Update params with full url and set the callback
            item.params.update(callback_params, search_query=search_term)
            item.set_callback(callback)
            yield item

    def close(self):
        """Close the connection to the search database."""
        self.search_db.close()
