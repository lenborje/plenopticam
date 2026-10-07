"""Offline coverage of native Illum camera and legacy calibration tar layouts."""
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from plenopticam.cfg import PlenopticamConfig
from plenopticam.misc import PlenopticamStatus
from plenopticam.lfp_calibrator import CaliFinder


class IllumArchiveTests(unittest.TestCase):
    def test_camera_and_legacy_tar_select_matching_geometry_reference(self):
        serial = 'B5151215780'
        for prefix in ('unitdata', serial):
            with self.subTest(prefix=prefix), tempfile.TemporaryDirectory() as temp:
                base = Path(temp)
                archive = base / ('caldata-'+serial+'.tar')
                manifest = {'calibrationFiles': [
                    {'name': 'MOD_0000.GCT', 'hash': 'sha1-other'},
                    {'name': 'MOD_0023.GCT', 'hash': 'sha1-matching'}]}
                files = {'cal_file_manifest.json': json.dumps(manifest).encode(),
                         'MOD_0023.RAW': b'calibration-pixels', 'MOD_0023.TXT': b'{"master": {}}'}
                with tarfile.open(archive, 'w') as tar:
                    for name, content in files.items():
                        member = tarfile.TarInfo(prefix+'/'+name)
                        member.size = len(content)
                        tar.addfile(member, io.BytesIO(content))
                raw = base / 'illum.lfr'
                metadata = base / 'illum' / 'illum.json'
                metadata.parent.mkdir()
                metadata.write_text(json.dumps({'camera': {'serialNumber': serial},
                    'frames': [{'frame': {'geometryCorrectionRef': 'sha1-matching'}}]}))
                cfg = PlenopticamConfig()
                cfg.params.update({cfg.lfp_path: str(raw), cfg.cal_path: str(archive)})
                sta = PlenopticamStatus()
                finder = CaliFinder(cfg, sta)
                # Pixel decoding is covered by verify_illum with real camera data.
                finder._raw2img = lambda: True
                self.assertTrue(finder.main())
                self.assertFalse(sta.error)
                self.assertEqual(finder.raw_data, b'calibration-pixels')
                self.assertEqual(finder._cal_fn, 'MOD_0023.RAW')
                self.assertEqual(finder._serial, serial)
                self.assertEqual(Path(cfg.params[cfg.cal_meta]), base/serial/'mod_0023.json')
