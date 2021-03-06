import numpy as np
import pandas as pd
import cv2
import os
import matplotlib.pyplot as plt
import torch
import torch.nn as nn


def mask2rle(img):
    '''
    img: numpy array, 1 - mask, 0 - background
    Returns run length as string formated
    '''
    pixels = img.T.flatten()
    pixels = np.concatenate([[0], pixels, [0]])
    runs = np.where(pixels[1:] != pixels[:-1])[0] + 1
    runs[1::2] -= runs[::2]

    return ' '.join(str(x) for x in runs)


def rle2mask(mask_rle, shape=(1600, 256)):
    '''
    mask_rle: run-length as string formated (start length)
    shape: (width,height) of array to return
    Returns numpy array, 1 - mask, 0 - background

    '''
    s = mask_rle.split()
    starts, lengths = [np.asarray(x, dtype=np.int) for x in (s[0::2], s[1::2])]
    starts -= 1
    ends = starts + lengths
    img = np.zeros(shape[0]*shape[1], np.uint8)
    for st, en in zip(starts, ends):
        img[st:en] = 255

    return img.reshape(shape).T


def make_mask(row_idx, df):
    fname = df.iloc[row_idx].name
    labels = df.iloc[row_idx][:4].values

    mask = np.zeros((256, 1600, 4), dtype=np.uint8)
    for i, label in enumerate(labels):
        if not pd.isna(label):
            mask[:, :, i] = rle2mask(label)
    return fname, mask


def show_mask(row_idx, df, data_dir='severstal-steel-data/train_images',
              pallet=((250, 230, 20), (30, 200, 241), (200, 30, 250), (250, 60, 20)),
              contour=True, show=False):
    image_name, mask = make_mask(row_idx, df)
    img = cv2.imread(os.path.join(data_dir, image_name))

    if contour:
        for ch in range(4):
            contours, _ = cv2.findContours(mask[:, :, ch],
                            cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
            for i in range(0, len(contours)):
                cv2.polylines(img, contours[i], True, pallet[ch], 3)
    else:
        for ch in range(4):
            img[mask[:, :, ch] == 1] = pallet[ch]
    plt.imshow(img)

    if show:
        plt.show()


def show_pallet(pallet=((250, 230, 20), (30, 200, 241), (200, 30, 250), (250, 60, 20))):
    fig, ax = plt.subplots(1, 4, figsize=(6, 2))
    for i in range(4):
        ax[i].axis('off')
        ax[i].imshow(np.ones((10, 40, 3), dtype=np.uint8) * pallet[i])
        ax[i].set_title("class{}".format(i+1))

    plt.show()


def show_images_with_defects(df, idxs_to_show=None, images_per_defect=2):
    if not idxs_to_show:
        idxs_to_show = [np.random.choice(np.where(
            ~pd.isna(df[class_id].values))[0]) for class_id in [1, 2, 3, 4] * images_per_defect]

    fig = plt.figure(figsize=(12, 10))
    pos = 1

    for idx in idxs_to_show:
        plt.subplot(4, 2, pos)
        show_mask(idx, df)
        pos += 1

    fig.suptitle('Типы деффектов', fontsize=14)
    fig.subplots_adjust(top=0.95)
    plt.show()


def forward_constants(module, **constants):
    module.__globals__.update(constants)


def load_model_resnet(model_weights='imagenet', is_inference=True):
    from torchvision.models import resnet34
    if model_weights == 'imagenet':
        model = resnet34(pretrained=True)
        model.fc = nn.Linear(model.fc.in_features, 1)
        if is_inference:
            model.eval()
        return model

    else:
        model = resnet34(pretrained=False)
        model.fc = nn.Linear(model.fc.in_features, 1)

        if is_inference:
            model.eval()

    if model_weights is not None:
        device = torch.device('cuda:0')
        model.to(device)
        state = torch.load(model_weights)
        model.load_state_dict(state['state_dict'])
        optimizer_state = state['optimizer']

        return model, optimizer_state
    return model


def load_model_efficientnet(model_weights='imagenet', is_inference=True):
    from efficient_pytorch import EfficientNet
    if model_weights == 'imagenet':
        model = EfficientNet.from_pretrained('efficientnet-b1')
        model.fc = nn.Linear(model._fc.in_features, 1)
        if is_inference:
            model.eval()
        return model

    else:
        model = EfficientNet.from_name('efficientnet-b1')
        model._fc = nn.Linear(model._fc.in_features, 1)

        if is_inference:
            model.eval()

    if model_weights is not None:
        device = torch.device('cuda:0')
        model.to(device)
        state = torch.load(model_weights)
        model.load_state_dict(state['state_dict'])
        optimizer_state = state['optimizer']

        return model, optimizer_state
    return model


def load_model_fpn():
    pass


def post_process(probability, threshold, min_size):
    '''Post processing of each predicted mask, components with lesser number of pixels
    than `min_size` are ignored'''
    mask = cv2.threshold(probability, threshold, 1, cv2.THRESH_BINARY)[1]
    num_component, component = cv2.connectedComponents(mask.astype(np.uint8))
    predictions = np.zeros((256, 1600), np.float32)
    num = 0
    for c in range(1, num_component):
        p = (component == c)
        if p.sum() > min_size:
            predictions[p] = 1
            num += 1
    return predictions, num