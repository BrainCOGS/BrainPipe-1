#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Fri Sep 28 15:10:47 2018

@author: wanglab
"""

import os, h5py
import numpy as np

src = '/jukebox/wang/pisano/conv_net/annotations/all_better_res/h129/otsu/inputRawImages'
for i, fn in enumerate(os.listdir(src)):
    f = h5py.File(os.path.join(src,fn))
    d = f["/main"].value
    f.close()
    print fn, d.shape, np.nonzero(d)[0].shape