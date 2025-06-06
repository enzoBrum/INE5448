# -*- coding: utf-8 -*-
"""
Created on Sun Jan  5 13:57:15 2020

@author: Lim
"""
# isort: skip_file
import math
import os
import subprocess
import sys
import time

sys.path.append(r"./backbone")
import numpy as np
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

from Loss import CtdetLoss
from dataset import ctDataset
from dlanet import DlaNet
from resnet import ResNet
import scipy.io




# from dlanet_dcn import DlaNet


def get_gpu_memory_usage(device_id=0):
    try:
        result = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,nounits"]
        )
        gpu_memory = [int(x) for x in result.strip().split(b"\n")[1:]][device_id]
        return gpu_memory
    except Exception as e:
        print(f"Error: {e}")
        return None


def check_cuda_memory(device_id=0, threshold=5000):
    try:
        while True:
            gpu_memory = get_gpu_memory_usage(device_id)
            if gpu_memory is not None:
                print(f"GPU Memory Used: {gpu_memory} MB")

                if gpu_memory < threshold:
                    print("GPU Memory is below the threshold. Exiting...")
                    break

            time.sleep(20)

    except KeyboardInterrupt:
        print("Detection stopped by user.")


check_cuda_memory(device_id=0, threshold=3000)

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
use_gpu = torch.cuda.is_available()
model = ResNet(34)
# model = DlaNet(34)
print("cuda", torch.cuda.current_device(), torch.cuda.device_count())

loss_weight = {"hm_weight": 1, "wh_weight": 0.1, "ang_weight": 1, "reg_weight": 0.5}
criterion = CtdetLoss(loss_weight)

device = torch.device("cuda")
if use_gpu:
    model.cuda()
model.train()

learning_rate = 0.0002
num_epochs = 60

# different learning rate
params = []
params_dict = dict(model.named_parameters())
for key, value in params_dict.items():
    params += [{"params": [value], "lr": learning_rate}]

# optimizer = torch.optim.SGD(params, lr=learning_rate, momentum=0.9, weight_decay=5e-4)
optimizer = torch.optim.Adam(params, lr=learning_rate, weight_decay=1e-4)


train_dataset = ctDataset(split="train")
train_loader = DataLoader(
    train_dataset, batch_size=4, shuffle=False, num_workers=12
)  # num_workers是加载数据（batch）的线程数目

test_dataset = ctDataset(split="val")
test_loader = DataLoader(test_dataset, batch_size=4, shuffle=False, num_workers=12)
print("the dataset has %d images" % (len(train_dataset)))


num_iter = 0

best_test_loss = np.inf

for epoch in tqdm(range(num_epochs)):
    model.train()
    if epoch == 90:
        learning_rate = learning_rate * 0.1
    if epoch == 120:
        learning_rate = learning_rate * (0.1**2)
    for param_group in optimizer.param_groups:
        param_group["lr"] = learning_rate

    total_loss = 0.0

    for i, sample in enumerate(train_loader):
        for k in sample:
            sample[k] = sample[k].to(device=device, non_blocking=True)
        pred = model(sample["input"])
        loss = criterion(pred, sample)
        total_loss += loss.item()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        if (i + 1) % 5 == 0:
            print(
                "Epoch [%d/%d], Iter [%d/%d] Loss: %.4f, average_loss: %.4f"
                % (
                    epoch + 1,
                    num_epochs,
                    i + 1,
                    len(train_loader),
                    loss.data,
                    total_loss / (i + 1),
                )
            )
            num_iter += 1

    # validation
    validation_loss = 0.0
    model.eval()
    for i, sample in enumerate(test_loader):
        if use_gpu:
            for k in sample:
                sample[k] = sample[k].to(device=device, non_blocking=True)

        pred = model(sample["input"])
        loss = criterion(pred, sample)
        validation_loss += loss.item()
    validation_loss /= len(test_loader)

    if best_test_loss > validation_loss:
        best_test_loss = validation_loss
        print("get best test loss %.5f" % best_test_loss)
        torch.save(model.state_dict(), "all_res34_best.pth")
    torch.save(model.state_dict(), "all_res34_last.pth")
