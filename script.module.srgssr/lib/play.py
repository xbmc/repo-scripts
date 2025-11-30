# Copyright (C) 2018 Alexander Seiler
#
#
# This file is part of script.module.srgssr.
#
# script.module.srgssr is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# script.module.srgssr is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with script.module.srgssr.
# If not, see <http://www.gnu.org/licenses/>.

from urllib.parse import parse_qsl, ParseResult
from urllib.parse import urlparse as urlps

import json
import xbmcgui
import xbmcplugin

import inputstreamhelper

import utils


class Player:
    """Handles playback logic for the SRGSSR plugin."""

    def __init__(self, srgssr_instance):
        self.srgssr = srgssr_instance
        self.handle = srgssr_instance.handle

    def play_video(self, media_id_or_urn):
        """
        Gets the stream information starts to play it.

        Keyword arguments:
        media_id_or_urn -- the urn or id of the media to play
        """
        if media_id_or_urn.startswith("urn:"):
            urn = media_id_or_urn
            media_id = media_id_or_urn.split(":")[-1]
        else:
            # TODO: Could fail for livestreams
            media_type = "video"
            urn = f"urn:{self.srgssr.bu}:{media_type}:{media_id_or_urn}"
            media_id = media_id_or_urn
        self.srgssr.log("play_video, urn = " + urn + ", media_id = " + media_id)

        detail_url = (
            "https://il.srgssr.ch/integrationlayer/2.0/mediaComposition/byUrn/" + urn
        )
        json_response = json.loads(self.srgssr.open_url(detail_url))
        title = utils.try_get(json_response, ["episode", "title"], str, urn)

        chapter_list = utils.try_get(
            json_response, "chapterList", data_type=list, default=[]
        )
        if not chapter_list:
            self.srgssr.log("play_video: no stream URL found (chapterList empty).")
            return

        first_chapter = utils.try_get(chapter_list, 0, data_type=dict, default={})
        chapter = next(
            (e for e in chapter_list if e.get("id") == media_id), first_chapter
        )
        resource_list = utils.try_get(
            chapter, "resourceList", data_type=list, default=[]
        )
        if not resource_list:
            self.srgssr.log("play_video: no stream URL found. (resourceList empty)")
            return

        stream_urls = {
            "SD": "",
            "HD": "",
        }

        mf_type = "hls"
        drm = False
        for resource in resource_list:
            if utils.try_get(resource, "drmList", data_type=list, default=[]):
                drm = True
                break

            if utils.try_get(resource, "protocol") == "HLS":
                for key in ("SD", "HD"):
                    if utils.try_get(resource, "quality") == key:
                        stream_urls[key] = utils.try_get(resource, "url")

        if drm:
            self.play_drm(urn, title, resource_list)
            return

        if not stream_urls["SD"] and not stream_urls["HD"]:
            self.srgssr.log("play_video: no stream URL found.")
            return

        stream_url = (
            stream_urls["HD"]
            if (stream_urls["HD"] and self.srgssr.prefer_hd) or not stream_urls["SD"]
            else stream_urls["SD"]
        )
        self.srgssr.log(f"play_video, stream_url = {stream_url}")

        auth_url = self.srgssr.get_auth_url(stream_url)

        start_time = end_time = None
        if utils.try_get(json_response, "segmentUrn"):
            segment_list = utils.try_get(
                chapter, "segmentList", data_type=list, default=[]
            )
            for segment in segment_list:
                if (
                    utils.try_get(segment, "id") == media_id
                    or utils.try_get(segment, "urn") == urn
                ):
                    start_time = utils.try_get(
                        segment, "markIn", data_type=int, default=None
                    )
                    if start_time:
                        start_time = start_time // 1000
                    end_time = utils.try_get(
                        segment, "markOut", data_type=int, default=None
                    )
                    if end_time:
                        end_time = end_time // 1000
                    break

            if start_time and end_time:
                parsed_url = urlps(auth_url)
                query_list = parse_qsl(parsed_url.query)
                updated_query_list = []
                for query in query_list:
                    if query[0] == "start" or query[0] == "end":
                        continue
                    updated_query_list.append(query)
                updated_query_list.append(("start", str(start_time)))
                updated_query_list.append(("end", str(end_time)))
                new_query = utils.assemble_query_string(updated_query_list)
                surl_result = ParseResult(
                    parsed_url.scheme,
                    parsed_url.netloc,
                    parsed_url.path,
                    parsed_url.params,
                    new_query,
                    parsed_url.fragment,
                )
                auth_url = surl_result.geturl()
        self.srgssr.log(f"play_video, auth_url = {auth_url}")
        play_item = xbmcgui.ListItem(title, path=auth_url)
        subs = self.srgssr.get_subtitles(stream_url, urn)
        if subs:
            play_item.setSubtitles(subs)

        play_item.setProperty("inputstream", "inputstream.adaptive")
        play_item.setProperty("inputstream.adaptive.manifest_type", mf_type)
        play_item.setProperty("IsPlayable", "true")

        xbmcplugin.setResolvedUrl(self.handle, True, play_item)

    def play_drm(self, urn, title, resource_list):
        self.srgssr.log(f"play_drm: urn = {urn}")
        preferred_quality = "HD" if self.srgssr.prefer_hd else "SD"
        resource_data = {
            "url": "",
            "lic_url": "",
        }
        for resource in resource_list:
            url = utils.try_get(resource, "url")
            if not url:
                continue
            quality = utils.try_get(resource, "quality")
            lic_url = ""
            if utils.try_get(resource, "protocol") == "DASH":
                drmlist = utils.try_get(resource, "drmList", data_type=list, default=[])
                for item in drmlist:
                    if utils.try_get(item, "type") == "WIDEVINE":
                        lic_url = utils.try_get(item, "licenseUrl")
                        resource_data["url"] = url
                        resource_data["lic_url"] = lic_url
            if resource_data["lic_url"] and quality == preferred_quality:
                break

        if not resource_data["url"] or not resource_data["lic_url"]:
            self.srgssr.log("play_drm: No stream found")
            return

        manifest_type = "mpd"
        drm = "com.widevine.alpha"
        helper = inputstreamhelper.Helper(manifest_type, drm=drm)
        if not helper.check_inputstream():
            self.srgssr.log("play_drm: Unable to setup drm")
            return

        play_item = xbmcgui.ListItem(
            title, path=self.srgssr.get_auth_url(resource_data["url"])
        )
        ia = "inputstream.adaptive"
        play_item.setProperty("inputstream", ia)
        lic_key = (
            f"{resource_data['lic_url']}|"
            "Content-Type=application/octet-stream|R{SSM}|"
        )
        play_item.setProperty(f"{ia}.manifest_type", manifest_type)
        play_item.setProperty(f"{ia}.license_type", drm)
        play_item.setProperty(f"{ia}.license_key", lic_key)
        xbmcplugin.setResolvedUrl(self.handle, True, play_item)
