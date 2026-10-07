"""Exercise the adopted Depthy fork through PlenoptiCam's public depth stage."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
from plenopticam.cfg import PlenopticamConfig
from plenopticam.misc import PlenopticamStatus
from plenopticam.lfp_extractor.lfp_depth import LfpDepth


class DepthCompatibilityTests(unittest.TestCase):
    def test_textured_plane_depth_and_exports(self):
        with tempfile.TemporaryDirectory() as temp:
            cfg = PlenopticamConfig()
            cfg.params.update({cfg.lfp_path: str(Path(temp)/'synthetic.lfr'),
                               cfg.ptc_leng: 3, cfg.opt_prnt: False})
            Path(cfg.exp_path).mkdir()
            rng = np.random.default_rng(32)
            image = rng.random((32, 40, 3))
            views = np.empty((3, 3, 32, 40, 3))
            for y in range(3):
                for x in range(3):
                    views[y, x] = np.roll(image, (y-1, x-1), (0, 1))
            obj = LfpDepth(vp_img_arr=views, cfg=cfg, sta=PlenopticamStatus())
            obj.main()
            self.assertEqual(obj.depth_map.shape, (32, 40))
            self.assertTrue(np.isfinite(obj.depth_map).all())
            for name in ('depth.pfm', 'depth.ply', 'depth.png'):
                self.assertGreater((Path(cfg.exp_path)/name).stat().st_size, 0)
