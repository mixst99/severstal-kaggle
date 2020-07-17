import torch
from sklearn.metrics import roc_auc_score as roc_auc_skl
import warnings
warnings.filterwarnings('ignore')


def roc_auc_score(targets, outputs):
    probs = torch.sigmoid(outputs)
    return roc_auc_skl(targets, probs)


def accuracy_score(targets, outputs, threshold=0.5):
    probs = torch.sigmoid(outputs)
    preds = (probs > threshold).float()
    return (targets == preds).float().mean().item()
