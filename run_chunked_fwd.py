#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 30 13:58:38 2018

@author: wanglab
"""

import os, numpy as np, sys, time
import collections

import torch
from torch.nn import functional as F
import dataprovider as dp

import forward
import utils
import models

def load_memmap_arr(pth, mode='r', dtype = 'float32', shape = False):
    '''Function to load memmaped array.
    
    by @tpisano

    '''
    if shape:
        assert mode =='w+', 'Do not pass a shape input into this function unless initializing a new array'
        arr = np.lib.format.open_memmap(pth, dtype = dtype, mode = mode, shape = shape)
    else:
        arr = np.lib.format.open_memmap(pth, dtype = dtype, mode = mode)
    return arr

def main(noeval, **args):

    sys.stdout.write('\n      Using torch version: {}\n\n'.format(torch.__version__)) #check torch version is correct - use 0.4.1

    #args should be the info you need to specify the params
    # for a given experiment, but only params should be used below
    params = fill_params(**args)

    utils.set_gpus(params["gpus"])

    net = utils.create_network(**params)
    if not noeval:
        net.eval()

    utils.log_tagged_modules(params["modules_used"], params["log_dir"],
                             params["log_tag"], params["chkpt_num"])

    #lightsheet mods
    inputs = load_memmap_arr(os.path.join(params["data_dir"], "patched_memmap_array.npy")) #load input patched array 
    output_arr = load_memmap_arr(os.path.join(params["data_dir"], 'patched_prediction_array.npy'), mode = 'w+', dtype = 'float32', shape = inputs.shape) #initialise output probability map
    
    initial = time.time()
    
    for i in range(len(inputs[:,0,0,0])): #iterates through each large patch to run inference #len(inputs[0])       
                
        start = time.time()
        
        dset = inputs[i,:,:,:]
                
        fs = make_forward_scanner(dset, **params)
                
        output = forward.forward(net, fs, params["scan_spec"],
                                 activation=params["activation"])

        output_arr[i,:,:,:] = save_output(output, output_arr[i,:,:,:], **params)
        
        sys.stdout.write("Patch {}: {} minutes\n".format((i+1), round((time.time()-start)/60, 1))); sys.stdout.flush()

    sys.stdout.write("Total time spent predicting: {}hr{}min".format(round((time.time()-initial)/3600, 0), round((time.time()-initial)/60, 0))); sys.stdout.flush()
    
def fill_params(expt_name, chkpt_num, gpus,
                nobn, model_name, dset_names, tag):

    params = {}

    #Model params
    params["in_dim"]      = 1
    params["output_spec"] = collections.OrderedDict(soma_label=1)
    params["depth"]       = 4
    params["batch_norm"]  = not(nobn)
    params["activation"]  = F.sigmoid
    params["chkpt_num"]   = chkpt_num

    #GPUS
    params["gpus"] = gpus

    #IO/Record params
    params["expt_name"]   = expt_name
    params["expt_dir"]    = "/jukebox/wang/zahra/conv_net/training/experiment_dirs/{}".format(expt_name)
    params["model_dir"]   = os.path.join(params["expt_dir"], "models")
    params["log_dir"]     = os.path.join(params["expt_dir"], "logs")
    params["fwd_dir"]     = os.path.join(params["expt_dir"], "forward")
    params["log_tag"]     = "fwd_" + tag if len(tag) > 0 else "fwd"
    params["output_tag"]  = tag

    #Dataset params
    params["data_dir"]    = os.path.expanduser("/jukebox/LightSheetTransfer/cnn/chunk_testing/20170116_tp_bl6_lob45_ml_11")
    assert os.path.isdir(params["data_dir"]),"nonexistent data directory"
    params["dsets"]       = dset_names
    params["input_spec"]  = collections.OrderedDict(input=(18,160,160)) #dp dataset spec
    params["scan_spec"]   = collections.OrderedDict(psd=(1,18,160,160))
    params["scan_params"] = dict(stride=(0.5,0.5,0.5), blend="bump")

    #Use-specific Module imports
    model_module = getattr(models,model_name)
    params["model_class"]  = model_module.Model

    #"Schema" for turning the parameters above into arguments
    # for the model class
    params["model_args"]   = [params["in_dim"], params["output_spec"],
                             params["depth"] ]
    params["model_kwargs"] = { "bn" : params["batch_norm"] }

    #Modules used for record-keeping
    params["modules_used"] = [__file__, model_module.__file__, "models/layers.py"]

    return params


def make_forward_scanner(dset_name, data_dir, input_spec,
                         scan_spec, scan_params, **params):
    """ Creates a DataProvider ForwardScanner from a dset name """

    # Reading chunk of lightsheet memory mapped array
    img = (dset_name / 2000.).astype("float32")

    # Creating DataProvider Dataset
    vd = dp.VolumeDataset()

    vd.add_raw_data(key="input", data=img)
    vd.set_spec(input_spec)

    # Returning DataProvider ForwardScanner
    return dp.ForwardScanner(vd, scan_spec, params=scan_params)


def save_output(output, output_arr, **params):
    """ Saves the volumes within a DataProvider ForwardScanner """

    for k in output.outputs.data.iterkeys():

        output_data = output.outputs.get_data(k)

        output_arr = output_data[0,:,:,:]

    return output_arr

#============================================================



if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("expt_name",
                        help="Experiment Name")
    parser.add_argument("model_name",
                        help="Model Template Name")
    parser.add_argument("chkpt_num", type=int,
                        help="Checkpoint Number")
    parser.add_argument("dset_names", nargs="+",
                        help="Inference Dataset Names")
    parser.add_argument("--nobn", action="store_true",
                        help="Whether net uses batch normalization")
    parser.add_argument("--gpus", default=["0"], nargs="+")
    parser.add_argument("--noeval", action="store_true",
                        help="Whether to use eval version of network")
    parser.add_argument("--tag", default="",
                        help="Output (and Log) Filename Tag")


    args = parser.parse_args()

    main(**vars(args))
