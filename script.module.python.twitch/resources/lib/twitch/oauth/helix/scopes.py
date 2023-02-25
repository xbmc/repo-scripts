# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/authentication#scopes

    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

analytics_read_extensions = 'analytics:read:extensions'  # View analytics data for the Twitch Extensions owned by the authenticated account.
analytics_read_games = 'analytics:read:games'  # View analytics data for the games owned by the authenticated account.
bits_read = 'bits:read'  # View Bits information for a channel.
channel_edit_commercial = 'channel:edit:commercial'  # Run commercials on a channel.
channel_manage_broadcast = 'channel:manage:broadcast'  # Manage a channel’s broadcast configuration, including updating channel configuration and managing stream markers and stream tags.
channel_manage_extensions = 'channel:manage:extensions'  # Manage a channel’s Extension configuration, including activating Extensions.
channel_manage_polls = 'channel:manage:polls'  # Manage a channel’s polls.
channel_manage_predictions = 'channel:manage:predictions'  # Manage of channel’s Channel Points Predictions
channel_manage_redemptions = 'channel:manage:redemptions'  # Manage Channel Points custom rewards and their redemptions on a channel.
channel_manage_schedule = 'channel:manage:schedule'  # Manage a channel’s stream schedule.
channel_manage_videos = 'channel:manage:videos'  # Manage a channel’s videos, including deleting videos.
channel_read_editors = 'channel:read:editors'  # View a list of users with the editor role for a channel.
channel_read_goals = 'channel:read:goals'  # View Creator Goals for a channel.
channel_read_hype_train = 'channel:read:hype_train'  # View Hype Train information for a channel.
channel_read_polls = 'channel:read:polls'  # View a channel’s polls.
channel_read_predictions = 'channel:read:predictions'  # View a channel’s Channel Points Predictions.
channel_read_redemptions = 'channel:read:redemptions'  # View Channel Points custom rewards and their redemptions on a channel.
channel_read_stream_key = 'channel:read:stream_key'  # View an authorized user’s stream key.
channel_read_subscriptions = 'channel:read:subscriptions'  # View a list of all subscribers to a channel and check if a user is subscribed to a channel.
clips_edit = 'clips:edit'  # Manage Clips for a channel.
moderation_read = 'moderation:read'  # View a channel’s moderation data including Moderators, Bans, Timeouts, and Automod settings.
moderator_manage_banned_users = 'moderator:manage:banned_users'  # Ban and unban users.
moderator_read_blocked_terms = 'moderator:read:blocked_terms'  # View a broadcaster’s list of blocked terms.
moderator_manage_blocked_terms = 'moderator:manage:blocked_terms'  # Manage a broadcaster’s list of blocked terms.
moderator_manage_automod = 'moderator:manage:automod'  # Manage messages held for review by AutoMod in channels where you are a moderator.
moderator_read_automod_settings = 'moderator:read:automod_settings'  # View a broadcaster’s AutoMod settings.
moderator_manage_automod_settings = 'moderator:manage:automod_settings'  # Manage a broadcaster’s AutoMod settings.
moderator_read_chat_settings = 'moderator:read:chat_settings'  # View a broadcaster’s chat room settings.
moderator_manage_chat_settings = 'moderator:manage:chat_settings'  # Manage a broadcaster’s chat room settings.
user_edit = 'user:edit'  # Manage a user object.
user_edit_follows = 'user:edit:follows'  # Deprecated. Was previously used for “Create User Follows” and “Delete User Follows.” See Deprecation of Create and Delete Follows API Endpoints.
user_manage_blocked_users = 'user:manage:blocked_users'  # Manage the block list of a user.
user_read_blocked_users = 'user:read:blocked_users'  # View the block list of a user.
user_read_broadcast = 'user:read:broadcast'  # View a user’s broadcasting configuration, including Extension configurations.
user_read_email = 'user:read:email'  # View a user’s email address.
user_read_follows = 'user:read:follows'  # View the list of channels a user follows.
user_read_subscriptions = 'user:read:subscriptions'  # View if an authorized user is subscribed to specific channels.
channel_moderate = 'channel:moderate'  # Perform moderation actions in a channel. The user requesting the scope must be a moderator in the channel.
chat_edit = 'chat:edit'  # Send live stream chat and rooms messages.
chat_read = 'chat:read'  # View live stream chat and rooms messages.
whispers_read = 'whispers:read'  # View your whisper messages.
whispers_edit = 'whispers:edit'  # Send whisper messages.
