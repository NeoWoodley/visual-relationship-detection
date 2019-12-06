import os
import torch
import pandas as pd
from skimage import io, transform
import numpy as np
import matplotlib.pyplot as plt
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, utils
import torch.optim as optim
from PIL import Image, ImageFont, ImageDraw
import json
import torch.nn as nn
import argparse
import random
import cv2
from util import AverageMeter, calculate_accuracy



def validate(model, loader, criterion, epoch, device):

    model.eval()

    losses = AverageMeter()
    accuracies = AverageMeter()
    for imgs, spatial_locations, word_vectors, targets in loader:
        # computse outputs
        imgs, spatial_locations, word_vectors, targets = imgs.to(device), spatial_locations.to(device), word_vectors.to(device),  targets.to(device)
        outputs = model(imgs, spatial_locations, word_vectors)

        # compute loss
        loss = criterion(outputs, targets)
        acc = calculate_accuracy(outputs, targets)

        losses.update(loss.item(), imgs.size(0))
        accuracies.update(acc, imgs.size(0))

    # show information
    print('Validation set ({:d} samples): Average loss: {:.4f}\tAcc: {:.4f}%'.format(losses.count, losses.avg, accuracies.avg * 100))
    return losses.avg, accuracies.avg

