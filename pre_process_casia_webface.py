import os

import cv2
import mxnet as mx
from tqdm import tqdm

rec_path = "./faces_webface_112x112"  # path to folder with train.rec files
save_path = os.path.join(rec_path, "MS1M_112x112")
if not os.path.exists(save_path):
    os.makedirs(save_path)

imgrec = mx.recordio.MXIndexedRecordIO(
    os.path.join(rec_path, "train.idx"), os.path.join(rec_path, "train.rec"), "r"
)
img_info = imgrec.read_idx(0)
header, _ = mx.recordio.unpack(img_info)
max_idx = int(header.label[0])
for idx in tqdm(range(1, max_idx)):
    img_info = imgrec.read_idx(idx)
    header, img = mx.recordio.unpack_img(img_info)
    label = int(header.label)
    label_path = os.path.join(save_path, str(label).zfill(6))
    if not os.path.exists(label_path):
        os.makedirs(label_path)
    if not os.path.exists(os.path.join(label_path, str(idx).zfill(8) + ".jpg")):
        cv2.imwrite(os.path.join(label_path, str(idx).zfill(8) + ".jpg"), img)
