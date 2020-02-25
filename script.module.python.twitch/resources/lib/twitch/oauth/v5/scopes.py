# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/authentication#scopes

    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

user_read = 'user_read'  # Read nonpublic user information, like email address.
user_blocks_edit = 'user_blocks_edit'  # Turn on/off ignoring a user. Ignoring a user means you cannot see him type, receive messages from him, etc.
user_blocks_read = 'user_blocks_read'  # Read a user’s list of ignored users.
user_follows_edit = 'user_follows_edit'  # Manage a user’s followed channels.
channel_read = 'channel_read'  # Read nonpublic channel information, including email address and stream key.
channel_editor = 'channel_editor'  # Write channel metadata (game, status, etc).
channel_commercial = 'channel_commercial'  # Trigger commercials on channel.
channel_stream = 'channel_stream'  # Reset a channel’s stream key.
channel_subscriptions = 'channel_subscriptions'  # Read all subscribers to your channel.
user_subscriptions = 'user_subscriptions'  # Read a user’s subscriptions.
channel_check_subscription = 'channel_check_subscription'  # Read whether a user is subscribed to your channel.
chat_login = 'chat_login'  # Log into chat and send messages.
channel_feed_read = 'channel_feed_read'  # View a channel feed.
channel_feed_edit = 'channel_feed_edit'  # Add posts and reactions to a channel feed.
collections_edit = 'collections_edit'  # Manage a user's collections (of videos).
communities_edit = 'communities_edit'  # Manage a user's communities. * DEPRECATED
communities_moderate = 'communities_moderate'  # Manage community moderators. * DEPRECATED
viewing_activity_read = 'viewing_activity_read'  # Turn on Viewer Heartbeat Service ability to record user data.
openid = 'openid'  # Use OpenID Connect authentication.
