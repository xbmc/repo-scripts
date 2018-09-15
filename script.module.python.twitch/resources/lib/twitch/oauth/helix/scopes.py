# -*- encoding: utf-8 -*-
# https://dev.twitch.tv/docs/authentication#scopes
"""
    scopes

    string constants
"""

analytics_read_extensions = 'analytics:read:extensions'  # View analytics data for your extensions.
analytics_read_games = 'analytics:read:games'  # View analytics data for your games.
bits_read = 'bits:read'  # View Bits information for your channel.
clips_edit = 'clips:edit'  # Manage a clip object.
user_edit = 'user:edit'  # Manage a user object.
user_edit_broadcast = 'user:edit:broadcast'  # Edit your channel’s broadcast configuration, including extension configuration. (This scope implies user:read:broadcast capability.)
user_read_broadcast = 'user:read:broadcast'  # View your broadcasting configuration, including extension configurations.
user_read_email = 'user:read:email'  # Read authorized user’s email address.
