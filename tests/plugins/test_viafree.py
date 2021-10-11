import unittest
from unittest.mock import ANY, MagicMock, call

from streamlink import Streamlink
from streamlink.plugins.viafree import Viafree
from tests.plugins import PluginCanHandleUrl

class TestPluginCanHandleUrlViafree(PluginCanHandleUrl):
    __plugin__ = Viafree

    should_match = [
        "https://www.viafree.dk/programmer/reality/forside-fruer/saeson-2/872877",
        "https://www.viafree.dk/programmer/reality/forside-fruer/saeson-2/episode-1",
        "https://www.viafree.no/programmer/underholdning/paradise-hotel-sverige/sesong-8/episode-19",
        "https://www.viafree.no/programmer/underholdning/paradise-hotel/sesong-9/822763",
        "https://www.viafree.se/program/underhallning/det-stora-experimentet/sasong-1/897870",
        "https://www.viafree.se/program/underhallning/det-stora-experimentet/sasong-1/avsnitt-19",
        "https://www.viafree.fi/ohjelmat/entertainment/rupauls-drag-race/kausi-10/jakso-1",
    ]

class TestPluginViafree(unittest.TestCase):
    def test_arguments(self):
        from streamlink_cli.main import setup_plugin_args
        session = Streamlink()
        parser = MagicMock()
        group = parser.add_argument_group("Plugin Options").add_argument_group("Viafree")

        session.plugins = {
            'viafree': Viafree
        }

        setup_plugin_args(session, parser)
        self.assertSequenceEqual(
            group.add_argument.mock_calls,
            [
                call('--viafree-language', choices=["sv", "da", "no", "fi"], help=ANY)
            ]
        )
