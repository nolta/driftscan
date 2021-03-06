"""Functional test suite for checking integrity of the analysis product
generation."""

import argparse
import tempfile
import shutil
import os
import sys

import unittest

import h5py
import numpy as np

# Ensure we're using the correct package
_basedir = os.path.realpath(os.path.dirname(__file__))
_scriptdir = os.path.realpath(_basedir + '/../scripts/')
_pkgdir = os.path.realpath(_basedir + '/../')
sys.path.insert(0, _pkgdir)

from drift.core import manager


def array_approx_equal(a, b, tol=1e-10):
    cmp_arr = np.abs(a-b) < tol * (0.5 * (a.max() + b.max()))

    return cmp_arr.all()



class TestSimulate(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Generate the analysis products.
        """

        # parser = argparse.ArgumentParser(description='Test the consistency of 
        # the analysis code.')
        # parser.add_argument('--keep', action='store_true')

        # args = parser.parse_args()

        cls.testdir = _basedir + '/tmptestdir/'
        if os.path.exists(cls.testdir):
            shutil.rmtree(cls.testdir)
        os.makedirs(cls.testdir)

        shutil.copy('testparams.yaml', cls.testdir + '/params.yaml')

        import multiprocessing
        nproc = max(multiprocessing.cpu_count() / 3, 1)

        cmd = """
                 cd %s
                 export OMP_NUM_THREADS=1
                 export PYTHONPATH=%s:$PYTHONPATH
                 mpirun -np %i python %s/drift-makeproducts run params.yaml &> output.log
              """

        cmd = cmd % (cls.testdir, _pkgdir, nproc, _scriptdir)

        print "Running test in: %s" % cls.testdir

        print "Generating products:", cmd
        cls.retval = os.system(cmd)
        #cls.retval = 0
        print "Done."

        cls.manager = manager.ProductManager.from_config(cls.testdir + '/params.yaml')


    def test_return_code(self):
        """Test that the products exited cleanly.
        """
        code = self.retval / 256
        self.assertEqual(code, 0, msg=('Exited with non-zero return code %i.' % code))


    def test_signal_exit(self):
        """Test that the products exited cleanly.
        """
        signal = self.retval % 256
        self.assertEqual(signal, 0, msg=('Killed with signal %i' % signal))


    def test_manager(self):
        """Check that the product manager code loads properly.
        """

        mfile = self.manager.directory
        tfile = self.testdir + '/testdir'
        self.assertTrue(os.path.samefile(mfile, tfile), msg='Manager does not see same directory.')


    @unittest.skip("Stopping generating beam_f soon.")
    def test_beam_f(self):
        """Check the consistency of the f-ordered beams.
        """

        with h5py.File('saved_products/beam_f_2.hdf5', 'r') as f:
            bf_saved = f['beam_freq'][:]
        bf = self.manager.beamtransfer.beam_freq(2, single=True)

        self.assertEqual(bf_saved.shape, bf.shape, msg='Beam matrix (f=2) shape has changed.')
        self.assertTrue((bf == bf_saved).all(), msg='Beam matrix (f=2) is incorrect.')


    def test_beam_m(self):
        """Check the consistency of the m-ordered beams.
        """

        with h5py.File('saved_products/beam_m_14.hdf5', 'r') as f:
            bm_saved = f['beam_m'][:]
        bm = self.manager.beamtransfer.beam_m(14)

        self.assertEqual(bm_saved.shape, bm.shape, msg='Beam matrix (m=14) shape has changed.')
        self.assertTrue(array_approx_equal(bm, bm_saved), msg='Beam matrix (m=14) is incorrect.')


    def test_svd_spectrum(self):
        """Test the SVD spectrum.
        """
        with h5py.File('saved_products/svdspectrum.hdf5', 'r') as f:
            svd_saved = f['singularvalues'][:]

        svd = self.manager.beamtransfer.svd_all()

        self.assertEqual(svd_saved.shape, svd.shape, msg='SVD spectrum shapes not equal.')
        self.assertTrue(array_approx_equal(svd, svd_saved), msg='SVD spectrum is incorrect.')


    @unittest.skip("Broken test.")
    def test_svd_mode(self):
        """Test that the SVD modes are correct.
        """

        with h5py.File('saved_products/svd_m_14.hdf5', 'r') as f:
            svd_saved = f['beam_svd'][:]
            invsvd_saved = f['invbeam_svd'][:]
            ut_saved = f['beam_ut'][:]

        svd = self.manager.beamtransfer.beam_svd(14)
        invsvd = self.manager.beamtransfer.invbeam_svd(14)
        ut = self.manager.beamtransfer.beam_ut(14)

        self.assertEqual(svd_saved.shape, svd.shape, msg='SVD beam matrix (m=14) shape has changed.')
        self.assertTrue((svd == svd_saved).all(), msg='SVD beam matrix (m=14) is incorrect.')
        self.assertTrue((invsvd == invsvd_saved).all(), msg='Inverse SVD beam matrix (m=14) is incorrect.')
        self.assertTrue((ut == ut_saved).all(), msg='SVD UT matrix (m=14) is incorrect.')


    def test_kl_spectrum(self):
        """Check the KL spectrum (for the foregroundless model).
        """

        with h5py.File('saved_products/evals_kl.hdf5', 'r') as f:
            ev_saved = f['evals'][:]

        ev = self.manager.kltransforms['kl'].evals_all()

        self.assertEqual(ev_saved.shape, ev.shape, msg='KL spectrum shapes not equal.')
        self.assertTrue(array_approx_equal(ev, ev_saved, tol=1e-6), msg='KL spectrum is incorrect.')


    @unittest.skip("Broken test.")
    def test_kl_mode(self):
        """Check a KL mode (m=26) for the foregroundless model.
        """

        with h5py.File('saved_products/ev_kl_m_26.hdf5', 'r') as f:
            evecs_saved = f['evecs'][:]

        evals, evecs = self.manager.kltransforms['kl'].modes_m(26)

        self.assertEqual(evecs_saved.shape, evecs.shape, msg='KL mode shapes not equal.')
        self.assertTrue((evecs == evecs_saved).all(), msg='KL mode is incorrect.')


    @unittest.skip("Broken test.")
    def test_dk_spectrum(self):
        """Check the KL spectrum (for the model with foregrounds).
        """

        with h5py.File('saved_products/evals_dk.hdf5', 'r') as f:
            ev_saved = f['evals'][:]

        ev = self.manager.kltransforms['dk'].evals_all()

        self.assertEqual(ev_saved.shape, ev.shape, msg='DK spectrum shapes not equal.')
        self.assertTrue(array_approx_equal(ev, ev_saved, tol=1e-6), msg='DK spectrum is incorrect.')


    @unittest.skip("Broken test.")
    def test_dk_mode(self):
        """Check a KL mode (m=26) for the model with foregrounds.
        """

        with h5py.File('saved_products/ev_dk_m_33.hdf5', 'r') as f:
            evecs_saved = f['evecs'][:]

        evals, evecs = self.manager.kltransforms['dk'].modes_m(33)

        self.assertEqual(evecs_saved.shape, evecs.shape, msg='DK mode shapes not equal.')
        self.assertTrue((evecs == evecs_saved).all(), msg='DK mode is incorrect.')


    def test_kl_fisher(self):
        """Test the Fisher matrix consistency. Use an approximate test as Monte-Carlo.
        """

        with h5py.File('saved_products/fisher_kl.hdf5', 'r') as f:
            fisher_saved = f['fisher'][:]
            bias_saved = f['bias'][:]            
            kc_saved = f['k_center']
            tc_saved = f['theta_center']

        ps = self.manager.psestimators['ps1']
        fisher, bias = ps.fisher_bias()

        self.assertEqual(fisher_saved.shape, fisher.shape, msg='KL Fisher shapes not equal.')

        fisher_rdiff = np.abs((fisher - fisher_saved) / (np.abs(fisher_saved) + 1e-4 * np.abs(fisher_saved).max()))
        fisher_adiff = np.abs((fisher - fisher_saved) / np.abs(fisher_saved.max()))

        rtest = (fisher_rdiff < 0.1).all()
        atest = (fisher_adiff < 0.05).all()

        if not (rtest and atest):
            print "Fisher difference: %f (rel) %f (abs)" % (fisher_rdiff.max(), fisher_adiff.max())

        self.assertTrue(rtest, msg='KL Fisher is incorrect (relative).')
        self.assertTrue(atest, msg='KL Fisher is incorrect (absolute).')        

        self.assertEqual(bias_saved.shape, bias.shape, msg='KL bias shapes not equal.')
        bias_diff = np.abs((bias - bias_saved) / (np.abs(bias_saved) + 1e-2 * np.abs(bias_saved).max()))        
        self.assertTrue((bias_diff < 0.02).all(), msg='KL bias is incorrect.')


    def test_dk_fisher(self):
        """Test the Fisher matrix consistency. Use an approximate test as Monte-Carlo.
        """

        with h5py.File('saved_products/fisher_dk.hdf5', 'r') as f:
            fisher_saved = f['fisher'][:]
            bias_saved = f['bias'][:]            
            kc_saved = f['k_center']
            tc_saved = f['theta_center']

        ps = self.manager.psestimators['ps2']
        fisher, bias = ps.fisher_bias()

        self.assertEqual(fisher_saved.shape, fisher.shape, msg='DK Fisher shapes not equal.')
     
        fisher_rdiff = np.abs((fisher - fisher_saved) / (np.abs(fisher_saved) + 1e-4 * np.abs(fisher_saved).max()))
        fisher_adiff = np.abs((fisher - fisher_saved) / np.abs(fisher_saved.max()))

        rtest = (fisher_rdiff < 0.1).all()
        atest = (fisher_adiff < 0.05).all()

        if not (rtest and atest):
            print "Fisher difference: %f (rel) %f (abs)" % (fisher_rdiff.max(), fisher_adiff.max())

        self.assertTrue(rtest, msg='DK Fisher is incorrect (relative).')
        self.assertTrue(atest, msg='DK Fisher is incorrect (absolute).')        

        self.assertEqual(bias_saved.shape, bias.shape, msg='DK bias shapes not equal.')
        bias_diff = np.abs((bias - bias_saved) / (np.abs(bias_saved) + 1e-4 * np.abs(bias_saved).max()))        
        self.assertTrue((bias_diff < 0.1).all(), msg='DK bias is incorrect.')



if __name__ == '__main__':
    unittest.main(verbosity=2)