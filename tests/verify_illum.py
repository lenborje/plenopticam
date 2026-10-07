"""Read-only originals; run the real Illum pipeline on isolated input copies.

Usage: python -m tests.verify_illum RAW_LFP CALDATA_TAR OUTPUT_DIRECTORY
Use --resume to reuse calibration/alignment produced by a previous run.
"""
import argparse
import hashlib
import json
import os
import shutil
import time
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/plenopticam-mpl')
import numpy as np
from plenopticam.cfg import PlenopticamConfig, constants
from plenopticam.misc import PlenopticamStatus
from plenopticam.lfp_reader import LfpReader
from plenopticam.lfp_calibrator import CaliFinder, LfpCalibrator
from plenopticam.lfp_aligner import LfpAligner
from plenopticam.lfp_extractor import LfpExtractor
from plenopticam.lfp_refocuser import LfpRefocuser


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('raw', type=Path)
    ap.add_argument('calibration', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--resampling', choices=('global', 'local'), default='global')
    args = ap.parse_args()
    out = args.output.resolve()
    for original in (args.raw.resolve(), args.calibration.resolve()):
        if out == original or out in original.parents:
            ap.error('Output directory must be separate from the original inputs')
    out.mkdir(parents=True, exist_ok=True)
    raw = out / 'illum.lfr'
    cal = out / args.calibration.name
    for source, target in ((args.raw, raw), (args.calibration, cal)):
        if source.resolve() == target.resolve():
            ap.error('Input and output copies must differ')
        if target.exists():
            with source.open('rb') as source_file, target.open('rb') as target_file:
                if hashlib.file_digest(source_file, 'sha256').digest() != hashlib.file_digest(target_file, 'sha256').digest():
                    ap.error('Existing working copy differs from input: '+str(target))
        else:
            shutil.copyfile(source, target)
    cfg = PlenopticamConfig()
    cfg._dir_path = str(out)
    cfg.default_values()
    cfg.params.update({cfg.lfp_path: str(raw), cfg.cal_path: str(cal),
                       cfg.cal_meth: constants.CALI_METH[3], cfg.smp_meth: args.resampling,
                       cfg.ptc_leng: 7, cfg.ran_refo: [0, 2], cfg.opt_dpth: False,
                       cfg.opt_prnt: True, cfg.opt_colo: True})
    sta = PlenopticamStatus()
    sta.prog_opt = False
    sta.bind_to_prog(lambda progress: print('PROGRESS', sta.stat_var, progress, flush=True)
                     if isinstance(progress, int) and progress % 10 == 0 else None)
    summary = {'stages': [], 'output': str(out), 'python': os.sys.version,
               'resampling': args.resampling}
    settings = {'resampling': args.resampling, 'patch': 7}
    settings_file = out / 'alignment-settings.json'
    if args.resume and not cfg.cond_lfp_align():
        if not settings_file.exists() or json.loads(settings_file.read_text()) != settings:
            ap.error('Cached alignment settings differ or are unknown; rerun without --resume')
    started = time.monotonic()

    def stage(name, shape=None):
        assert not sta.error and not sta.interrupt, (name, sta.stat_var)
        item = {'stage': name, 'elapsed_seconds': round(time.monotonic()-started, 2)}
        if shape is not None:
            item['shape'] = list(shape)
        summary['stages'].append(item)
        (out / 'acceptance.json').write_text(json.dumps(summary, indent=2))
        print('ACCEPTANCE', json.dumps(item), flush=True)

    reader = LfpReader(cfg, sta)
    assert reader.main()
    bayer = reader.lfp_img
    assert bayer.shape == (5368, 7728)
    stage('raw decoded', bayer.shape)
    finder = CaliFinder(cfg, sta)
    assert finder.main()
    white = finder.wht_bay
    assert white is not None and white.shape == bayer.shape
    summary['calibration_member'] = finder._cal_fn
    summary['serial'] = finder._serial
    stage('matching calibration decoded', white.shape)
    summary['cached_calibration'] = args.resume and cfg.cond_meta_file()
    if not summary['cached_calibration']:
        obj = LfpCalibrator(white, cfg, sta)
        assert obj.main()
        del obj
    cfg.load_cal_data()
    stage('microlens calibration', np.asarray(cfg.calibs[cfg.mic_list]).shape)
    summary['cached_alignment'] = args.resume and not cfg.cond_lfp_align()
    if not summary['cached_alignment']:
        obj = LfpAligner(bayer, cfg, sta, white)
        assert obj.main()
        aligned = obj.lfp_img
        settings_file.write_text(json.dumps(settings, indent=2))
        del obj
    else:
        import pickle
        with open(Path(cfg.exp_path) / 'lfp_img_align.pkl', 'rb') as f:
            aligned = pickle.load(f)
    del reader, bayer, finder, white
    stage('alignment', aligned.shape)
    extractor = LfpExtractor(aligned, cfg, sta)
    assert extractor.main()
    views = extractor.vp_img_linear
    assert views.shape[:2] == (7, 7) and np.isfinite(views).all()
    stage('viewpoint extraction', views.shape)
    del aligned, extractor
    refocuser = LfpRefocuser(views, cfg=cfg, sta=sta)
    assert refocuser.main()
    assert len(refocuser.refo_stack) == 2 and np.isfinite(refocuser.refo_stack).all()
    stage('refocusing', np.asarray(refocuser.refo_stack).shape)
    print('Outputs:', cfg.exp_path, flush=True)


if __name__ == '__main__':
    main()
