import unittest
from unittest.mock import Mock
from plenopticam.lfp_reader.lfp_decoder import LfpDecoder


class RawDispatchTests(unittest.TestCase):
    def test_raw_and_bundle_extensions_dispatch_separately(self):
        for name, expected in [('MOD_0000.RAW', 'decode_raw'), ('data.c.0', 'decode_bundle'),
                               ('data.lfr', 'decode_lfc'), ('data.lfp', 'decode_lfc')]:
            obj = LfpDecoder.__new__(LfpDecoder)
            obj.sta = Mock(interrupt=False)
            obj._lfp_path = name
            obj.decode_raw = Mock()
            obj.decode_bundle = Mock()
            obj.decode_lfc = Mock()
            obj.main()
            getattr(obj, expected).assert_called_once_with()
            for other in {'decode_raw', 'decode_bundle', 'decode_lfc'}-{expected}:
                getattr(obj, other).assert_not_called()

