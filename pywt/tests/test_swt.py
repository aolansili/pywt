#!/usr/bin/env python

from __future__ import division, print_function, absolute_import

import warnings
from copy import deepcopy
from itertools import combinations
import numpy as np
from numpy.testing import (run_module_suite, dec, assert_allclose, assert_,
                           assert_equal, assert_raises, assert_array_equal)

import pywt
from pywt._extensions._swt import swt_axis

# Check that float32 and complex64 are preserved.  Other real types get
# converted to float64.
dtypes_in = [np.int8, np.float32, np.float64, np.complex64, np.complex128]
dtypes_out = [np.float64, np.float32, np.float64, np.complex64, np.complex128]


# tolerances used in accuracy comparisons
tol_single = 1e-6
tol_double = 1e-13

####
# 1d multilevel swt tests
####


def test_swt_decomposition():
    x = [3, 7, 1, 3, -2, 6, 4, 6]
    db1 = pywt.Wavelet('db1')
    (cA3, cD3), (cA2, cD2), (cA1, cD1) = pywt.swt(x, db1, level=3)
    expected_cA1 = [7.07106781, 5.65685425, 2.82842712, 0.70710678,
                    2.82842712, 7.07106781, 7.07106781, 6.36396103]
    assert_allclose(cA1, expected_cA1)
    expected_cD1 = [-2.82842712, 4.24264069, -1.41421356, 3.53553391,
                    -5.65685425, 1.41421356, -1.41421356, 2.12132034]
    assert_allclose(cD1, expected_cD1)
    expected_cA2 = [7, 4.5, 4, 5.5, 7, 9.5, 10, 8.5]
    assert_allclose(cA2, expected_cA2, rtol=tol_double)
    expected_cD2 = [3, 3.5, 0, -4.5, -3, 0.5, 0, 0.5]
    assert_allclose(cD2, expected_cD2, rtol=tol_double, atol=1e-14)
    expected_cA3 = [9.89949494, ] * 8
    assert_allclose(cA3, expected_cA3)
    expected_cD3 = [0.00000000, -3.53553391, -4.24264069, -2.12132034,
                    0.00000000, 3.53553391, 4.24264069, 2.12132034]
    assert_allclose(cD3, expected_cD3)

    # level=1, start_level=1 decomposition should match level=2
    res = pywt.swt(cA1, db1, level=1, start_level=1)
    cA2, cD2 = res[0]
    assert_allclose(cA2, expected_cA2, rtol=tol_double)
    assert_allclose(cD2, expected_cD2, rtol=tol_double, atol=1e-14)

    coeffs = pywt.swt(x, db1)
    assert_(len(coeffs) == 3)
    assert_(pywt.swt_max_level(len(x)) == 3)


def test_swt_axis():
    x = [3, 7, 1, 3, -2, 6, 4, 6]

    db1 = pywt.Wavelet('db1')
    (cA2, cD2), (cA1, cD1) = pywt.swt(x, db1, level=2)

    # test cases use 2D arrays based on tiling x along an axis and then
    # calling swt along the other axis.
    for order in ['C', 'F']:
        # test SWT of 2D data along default axis (-1)
        x_2d = np.asarray(x).reshape((1, -1))
        x_2d = np.concatenate((x_2d, )*5, axis=0)
        if order == 'C':
            x_2d = np.ascontiguousarray(x_2d)
        elif order == 'F':
            x_2d = np.asfortranarray(x_2d)
        (cA2_2d, cD2_2d), (cA1_2d, cD1_2d) = pywt.swt(x_2d, db1, level=2)

        for c in [cA2_2d, cD2_2d, cA1_2d, cD1_2d]:
            assert_(c.shape == x_2d.shape)
        # each row should match the 1D result
        for row in cA1_2d:
            assert_array_equal(row, cA1)
        for row in cA2_2d:
            assert_array_equal(row, cA2)
        for row in cD1_2d:
            assert_array_equal(row, cD1)
        for row in cD2_2d:
            assert_array_equal(row, cD2)

        # test SWT of 2D data along other axis (0)
        x_2d = np.asarray(x).reshape((-1, 1))
        x_2d = np.concatenate((x_2d, )*5, axis=1)
        if order == 'C':
            x_2d = np.ascontiguousarray(x_2d)
        elif order == 'F':
            x_2d = np.asfortranarray(x_2d)
        (cA2_2d, cD2_2d), (cA1_2d, cD1_2d) = pywt.swt(x_2d, db1, level=2,
                                                      axis=0)

        for c in [cA2_2d, cD2_2d, cA1_2d, cD1_2d]:
            assert_(c.shape == x_2d.shape)
        # each column should match the 1D result
        for row in cA1_2d.transpose((1, 0)):
            assert_array_equal(row, cA1)
        for row in cA2_2d.transpose((1, 0)):
            assert_array_equal(row, cA2)
        for row in cD1_2d.transpose((1, 0)):
            assert_array_equal(row, cD1)
        for row in cD2_2d.transpose((1, 0)):
            assert_array_equal(row, cD2)

    # axis too large
    assert_raises(ValueError, pywt.swt, x, db1, level=2, axis=5)


def test_swt_iswt_integration():
    # This function performs a round-trip swt/iswt transform test on
    # all available types of wavelets in PyWavelets - except the
    # 'dmey' wavelet. The latter has been excluded because it does not
    # produce very precise results. This is likely due to the fact
    # that the 'dmey' wavelet is a discrete approximation of a
    # continuous wavelet. All wavelets are tested up to 3 levels. The
    # test validates neither swt or iswt as such, but it does ensure
    # that they are each other's inverse.

    max_level = 3
    wavelets = pywt.wavelist()
    if 'dmey' in wavelets:
        # The 'dmey' wavelet seems to be a bit special - disregard it for now
        wavelets.remove('dmey')
    for current_wavelet_str in wavelets:
        current_wavelet = pywt.DiscreteContinuousWavelet(current_wavelet_str)
        if isinstance(current_wavelet, pywt.Wavelet):
            input_length_power = int(np.ceil(np.log2(max(
                current_wavelet.dec_len,
                current_wavelet.rec_len))))
            input_length = 2**(input_length_power + max_level - 1)
            X = np.arange(input_length)
            coeffs = pywt.swt(X, current_wavelet, max_level)
            Y = pywt.iswt(coeffs, current_wavelet)
            assert_allclose(Y, X, rtol=1e-5, atol=1e-7)


def test_swt_dtypes():
    wavelet = pywt.Wavelet('haar')
    for dt_in, dt_out in zip(dtypes_in, dtypes_out):
        errmsg = "wrong dtype returned for {0} input".format(dt_in)

        # swt
        x = np.ones(8, dtype=dt_in)
        (cA2, cD2), (cA1, cD1) = pywt.swt(x, wavelet, level=2)
        assert_(cA2.dtype == cD2.dtype == cA1.dtype == cD1.dtype == dt_out,
                "swt: " + errmsg)

        # swt2
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', FutureWarning)
            x = np.ones((8, 8), dtype=dt_in)
            cA, (cH, cV, cD) = pywt.swt2(x, wavelet, level=1)[0]
            assert_(cA.dtype == cH.dtype == cV.dtype == cD.dtype == dt_out,
                    "swt2: " + errmsg)


def test_swt_roudtrip_dtypes():
    # verify perfect reconstruction for all dtypes
    rstate = np.random.RandomState(5)
    wavelet = pywt.Wavelet('haar')
    for dt_in, dt_out in zip(dtypes_in, dtypes_out):
        # swt, iswt
        x = rstate.standard_normal((8, )).astype(dt_in)
        c = pywt.swt(x, wavelet, level=2)
        xr = pywt.iswt(c, wavelet)
        assert_allclose(x, xr, rtol=1e-6, atol=1e-7)

        # swt2, iswt2
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', FutureWarning)
            x = rstate.standard_normal((8, 8)).astype(dt_in)
            c = pywt.swt2(x, wavelet, level=2)
            xr = pywt.iswt2(c, wavelet)
            assert_allclose(x, xr, rtol=1e-6, atol=1e-7)


def test_swt2_ndim_error():
    x = np.ones(8)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', FutureWarning)
        assert_raises(ValueError, pywt.swt2, x, 'haar', level=1)


@dec.slow
def test_swt2_iswt2_integration():
    # This function performs a round-trip swt2/iswt2 transform test on
    # all available types of wavelets in PyWavelets - except the
    # 'dmey' wavelet. The latter has been excluded because it does not
    # produce very precise results. This is likely due to the fact
    # that the 'dmey' wavelet is a discrete approximation of a
    # continuous wavelet. All wavelets are tested up to 3 levels. The
    # test validates neither swt2 or iswt2 as such, but it does ensure
    # that they are each other's inverse.

    max_level = 3
    wavelets = pywt.wavelist()
    if 'dmey' in wavelets:
        # The 'dmey' wavelet seems to be a bit special - disregard it for now
        wavelets.remove('dmey')
    for current_wavelet_str in wavelets:
        current_wavelet = pywt.DiscreteContinuousWavelet(current_wavelet_str)
        if isinstance(current_wavelet, pywt.Wavelet):
            input_length_power = int(np.ceil(np.log2(max(
                current_wavelet.dec_len,
                current_wavelet.rec_len))))
            input_length = 2**(input_length_power + max_level - 1)
            X = np.arange(input_length**2).reshape(input_length, input_length)

            with warnings.catch_warnings():
                warnings.simplefilter('ignore', FutureWarning)
                coeffs = pywt.swt2(X, current_wavelet, max_level)
                Y = pywt.iswt2(coeffs, current_wavelet)
            assert_allclose(Y, X, rtol=1e-5, atol=1e-5)


def test_swt2_axes():
    atol = 1e-14
    current_wavelet = pywt.Wavelet('db2')
    input_length_power = int(np.ceil(np.log2(max(
        current_wavelet.dec_len,
        current_wavelet.rec_len))))
    input_length = 2**(input_length_power)
    X = np.arange(input_length**2).reshape(input_length, input_length)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', FutureWarning)
        (cA1, (cH1, cV1, cD1)) = pywt.swt2(X, current_wavelet, level=1)[0]
        # opposite order
        (cA2, (cH2, cV2, cD2)) = pywt.swt2(X, current_wavelet, level=1,
                                           axes=(1, 0))[0]
        assert_allclose(cA1, cA2, atol=atol)
        assert_allclose(cH1, cV2, atol=atol)
        assert_allclose(cV1, cH2, atol=atol)
        assert_allclose(cD1, cD2, atol=atol)

        # duplicate axes not allowed
        assert_raises(ValueError, pywt.swt2, X, current_wavelet, 1,
                      axes=(0, 0))
        # too few axes
        assert_raises(ValueError, pywt.swt2, X, current_wavelet, 1, axes=(0, ))


def test_swtn_axes():
    atol = 1e-14
    current_wavelet = pywt.Wavelet('db2')
    input_length_power = int(np.ceil(np.log2(max(
        current_wavelet.dec_len,
        current_wavelet.rec_len))))
    input_length = 2**(input_length_power)
    X = np.arange(input_length**2).reshape(input_length, input_length)
    coeffs = pywt.swtn(X, current_wavelet, level=1, axes=None)[0]
    # opposite order
    coeffs2 = pywt.swtn(X, current_wavelet, level=1, axes=(1, 0))[0]
    assert_allclose(coeffs['aa'], coeffs2['aa'], atol=atol)
    assert_allclose(coeffs['ad'], coeffs2['da'], atol=atol)
    assert_allclose(coeffs['da'], coeffs2['ad'], atol=atol)
    assert_allclose(coeffs['dd'], coeffs2['dd'], atol=atol)

    # 0-level transform
    empty = pywt.swtn(X, current_wavelet, level=0)
    assert_equal(empty, [])

    # duplicate axes not allowed
    assert_raises(ValueError, pywt.swtn, X, current_wavelet, 1, axes=(0, 0))

    # data.ndim = 0
    assert_raises(ValueError, pywt.swtn, np.asarray([]), current_wavelet, 1)

    # start_level too large
    assert_raises(ValueError, pywt.swtn, X, current_wavelet,
                  level=1, start_level=2)

    # level < 1 in swt_axis call
    assert_raises(ValueError, swt_axis, X, current_wavelet, level=0,
                  start_level=0)
    # odd-sized data not allowed
    assert_raises(ValueError, swt_axis, X[:-1, :], current_wavelet, level=0,
                  start_level=0, axis=0)


@dec.slow
def test_swtn_iswtn_integration():
    # This function performs a round-trip swtn/iswtn transform for various
    # possible combinations of:
    #   1.) 1 out of 2 axes of a 2D array
    #   2.) 2 out of 3 axes of a 3D array
    #
    # To keep test time down, only wavelets of length <= 8 are run.
    #
    # This test does not validate swtn or iswtn individually, but only
    # confirms that iswtn yields an (almost) perfect reconstruction of swtn.
    max_level = 3
    wavelets = pywt.wavelist()
    if 'dmey' in wavelets:
        # The 'dmey' wavelet seems to be a bit special - disregard it for now
        wavelets.remove('dmey')
    for ndim_transform in range(1, 2):
        ndim = ndim_transform + 1
        for axes in combinations(range(ndim), ndim_transform):
            for current_wavelet_str in wavelets:
                wav = pywt.DiscreteContinuousWavelet(current_wavelet_str)
                if isinstance(wav, pywt.Wavelet):
                    if wav.dec_len > 8:
                        continue  # avoid excessive test duration
                    input_length_power = int(np.ceil(np.log2(max(
                        wav.dec_len,
                        wav.rec_len))))
                    N = 2**(input_length_power + max_level - 1)
                    X = np.arange(N**ndim).reshape((N, )*ndim)

                    coeffs = pywt.swtn(X, wav, max_level, axes=axes)
                    coeffs_copy = deepcopy(coeffs)
                    Y = pywt.iswtn(coeffs, wav, axes=axes)
                    assert_allclose(Y, X, rtol=1e-5, atol=1e-5)

                    # verify the inverse transform didn't modify any coeffs
                    for c, c2 in zip(coeffs, coeffs_copy):
                        for k, v in c.items():
                            assert_array_equal(c2[k], v)


def test_iswtn_errors():
    x = np.arange(8**3).reshape(8, 8, 8)
    max_level = 2
    axes = (0, 1)
    w = pywt.Wavelet('db1')
    coeffs = pywt.swtn(x, w, max_level, axes=axes)

    # more axes than dimensions transformed
    assert_raises(ValueError, pywt.iswtn, coeffs, w, axes=(0, 1, 2))
    # duplicate axes not allowed
    assert_raises(ValueError, pywt.iswtn, coeffs, w, axes=(0, 0))
    # mismatched coefficient size
    coeffs[0]['da'] = coeffs[0]['da'][:-1, :]
    assert_raises(RuntimeError, pywt.iswtn, coeffs, w, axes=axes)


if __name__ == '__main__':
    run_module_suite()
