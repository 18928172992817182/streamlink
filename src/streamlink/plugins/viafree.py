import json
import logging
import re

from streamlink.plugin import Plugin, PluginArgument, PluginArguments, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.stream.http import HTTPStream
from streamlink.utils.l10n import Localization

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?
    (?:viafree\.)?
    (?P<topLevelDomain>se|dk|no|fi)
""", re.VERBOSE))
class Viafree(Plugin):
    stream_link_re = re.compile(r'streamLink:*(?P<json>[^?]+)},')

    _stream_schema = {
        "links": {
            "stream": {
                "href": validate.text,
            }
        }
    }

    _subtitle_schema = {
        "link": {
            "href": validate.text,
        },
        "data": {
            "language": validate.text,
            "format": validate.text,
        }
    }

    _video_schema = validate.Schema({
        validate.optional('embedded'): {
            'prioritizedStreams': validate.any(
                [_stream_schema]
            ),
            validate.optional('subtitles'): [_subtitle_schema],
        }
    })

    arguments = PluginArguments(
        PluginArgument("mux-subtitles", is_global=True),
        PluginArgument(
            "language",
            argument_name="viafree-language",
            choices=["sv", "da", "no", "fi"],
            help="""
                The subtitle language to use for the stream.
                If not provided all available will be muxed as selections.
                """
        ),
    )

    def _get_locale(self):
        top_level_domain = self.match.group("topLevelDomain")
        if top_level_domain == 'se':
            return 'sv'
        elif top_level_domain == 'dk':
            return 'da'

        return top_level_domain

    def _get_api_data(self):
        res = self.session.http.get(self.url)

        match = self.stream_link_re.search(res.text)

        if match is None:
            return

        json_content = bytes(match.group('json'), 'UTF-8').decode('unicode-escape')
        json_content = json.loads('{"streamLink' + json_content + '}}')

        stream_link = json_content['streamLink']
        streams = stream_link['href']

        res = self.session.http.get(streams)
        return self.session.http.json(res, schema=self._video_schema)

    def _get_subtitles(self, api_data):
        embedded = api_data['embedded']
        sub_streams = {}
        if 'subtitles' in embedded:
            default_language = self.get_option('language')
            for subtitle in embedded['subtitles']:
                data = subtitle['data']
                if data and data['format'].casefold() == 'webvtt':
                    url = subtitle['link']['href']
                    log.debug("Subtitle={0}".format(url))
                    language_alpha3 = Localization.get_language(data['language']).alpha3
                    if default_language is not None:
                        if default_language == data['language']:
                            sub_streams[language_alpha3] = HTTPStream(
                                self.session,
                                url,
                            )
                    else:
                        sub_streams[language_alpha3] = HTTPStream(
                            self.session,
                            url,
                        )
        return sub_streams

    def _get_vod_url(self, api_data):
        embedded = api_data['embedded']
        prioritized_streams = embedded and embedded['prioritizedStreams']

        json_content = prioritized_streams and prioritized_streams[0]
        json_content = json_content and json_content['links']
        json_content = json_content and json_content['stream']
        return json_content and json_content['href']

    def _get_streams(self):
        api_data = self._get_api_data()

        if api_data is None:
            return

        video_url = self._get_vod_url(api_data)
        sub_streams = self._get_subtitles(api_data)

        if ".m3u8" in video_url:
            for q, s in HLSStream.parse_variant_playlist(self.session, video_url).items():
                if self.get_option('mux_subtitles') and sub_streams:
                    # acodec needed because of a bug somewhere deeper down in MuxedStream with using HLS
                    yield q, MuxedStream(self.session, s, subtitles=sub_streams, acodec='aac')
                else:
                    yield q, s
        else:
            log.error("only HLS streams currently supported")


__plugin__ = Viafree
