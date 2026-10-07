"""Viewer regression tests: run with a graphical session and CPython Tk."""
import tempfile
import unittest
from pathlib import Path
import tkinter as tk
import numpy as np
from PIL import Image
from plenopticam.cfg import PlenopticamConfig
from plenopticam.misc import PlenopticamStatus
from plenopticam.misc.os_ops import get_img_list
from plenopticam.gui.widget_view import ViewWidget


class ViewerCompatibilityTests(unittest.TestCase):
    def test_saved_viewpoint_array_shape(self):
        with tempfile.TemporaryDirectory() as temp:
            for row in range(3):
                for col in range(3):
                    image = np.arange(20*24*3,dtype=np.uint8).reshape(20,24,3)
                    Image.fromarray(image).save(Path(temp)/f'{row}_{col}.png')
            views = get_img_list(temp)
            self.assertEqual(views.shape, (3,3,20,24,3))

    def test_empty_viewer_displays_notification(self):
        with tempfile.TemporaryDirectory() as temp:
            cfg = PlenopticamConfig()
            cfg.params[cfg.lfp_path] = str(Path(temp)/'missing.lfr')
            root = tk.Tk()
            try:
                viewer = ViewWidget(root,cfg=cfg,sta=PlenopticamStatus())
                root.update()
                self.assertGreater(viewer.tk_frame.width(), 0)
                self.assertIsNone(viewer.vp_img_arr)
                self.assertIsNone(viewer.refo_stack)
                viewer.switch_mode()
                root.update()
                self.assertFalse(viewer.vp_mode)
            finally:
                root.destroy()
