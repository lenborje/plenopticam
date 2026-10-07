"""Small, offline regression tests for current NumPy/SciPy and RAW dispatch."""
import unittest
from unittest.mock import patch
import numpy as np
from plenopticam.misc import img_resize


class ModernCompatibilityTests(unittest.TestCase):
    def test_resize_preserves_row_column_orientation_and_channels(self):
        y, x = np.mgrid[:5, :8]
        image = np.stack([y+10*x, 2*y-x, y*x], axis=-1).astype(float)
        resized = img_resize(image, new_shape=(9, 13), method='linear')
        yy, xx = np.meshgrid(np.linspace(0, 4, 9), np.linspace(0, 7, 13), indexing='ij')
        expected = np.stack([yy+10*xx, 2*yy-xx, yy*xx], axis=-1)
        np.testing.assert_allclose(resized, expected, atol=1e-12)
        self.assertEqual(resized.dtype, image.dtype)

    def test_resize_retains_cubic_and_quintic_degrees(self):
        for method, degree in [('cubic', 3), ('quintic', 5)]:
            y, x = np.mgrid[:7, :9]
            image = (y**degree + 2*x**degree).astype(float)
            yy, xx = np.meshgrid(np.linspace(0, 6, 10), np.linspace(0, 8, 12), indexing='ij')
            np.testing.assert_allclose(img_resize(image, new_shape=(10, 12), method=method),
                                       yy**degree+2*xx**degree, atol=1e-9)


    def test_local_resampling_retains_linear_default(self):
        from plenopticam.lfp_aligner.lfp_local_resampler import LfpLocalResampler
        from plenopticam.lfp_aligner.lfp_microlenses import LfpMicroLenses
        from scipy.interpolate import RegularGridInterpolator

        def init(obj, *args, **kwargs):
            obj._size_pitch = 3
            obj._DIMS = (5, 5, 1)
            obj._flip = False

        with patch.object(LfpMicroLenses, '__init__', init):
            obj = LfpLocalResampler()
        y, x = np.mgrid[:5, :5]
        window = (y**2+2*x**2+y*x).astype(float)
        result = obj._patch_align(window[..., None], (.2, .3))[1:-1, 1:-1, 0]
        yy, xx = np.meshgrid(np.arange(1, 4)+.2, np.arange(1, 4)+.3, indexing='ij')
        expected = RegularGridInterpolator((np.arange(5), np.arange(5)), window)(
            np.stack([yy, xx], axis=-1))
        np.testing.assert_allclose(result, expected, atol=1e-12)


if __name__ == '__main__':
    unittest.main()
