import torch
import torch.nn as nn
from torchvision import models
import json
import numpy as np
import torch.nn.functional as F
from opts import parse_opts
import torchvision.ops as ops
import os

opt = parse_opts()

with open(os.path.join(opt.dataset_path, 'json_dataset', 'objects.json'), 'r') as f:
	objects = json.load(f)

word2int = {}
for i, obj in enumerate(objects):
	word2int[obj] = i

glove = {}
vocab = len(objects)
matrix_len = vocab
weights_matrix = np.zeros((matrix_len, 300))
with open(opt.glove_path, 'rb') as f:
	for l in f:
		line = l.decode().split()
		word = line[0]
		vect = np.array(line[1:]).astype(np.float)
		glove[word] = vect
for i, obj in enumerate(objects):
	try:
		weights_matrix[word2int[obj]] = glove[obj]
	except KeyError:
		weights_matrix[word2int[obj]] = np.random.normal(
			scale=0.6, size=(300, ))
weights_matrix = torch.Tensor(weights_matrix)


def create_emb_layer(weights_matrix, non_trainable=False):
	num_embeddings, embedding_dim = weights_matrix.size()
	emb_layer = nn.Embedding(num_embeddings, embedding_dim)
	emb_layer.load_state_dict({'weight': weights_matrix})
	if non_trainable:
		emb_layer.weight.requires_grad = False
	return emb_layer, embedding_dim


class LanguageModule(nn.Module):
	""" Language Moddule"""

	def __init__(self, hidden_dim, target_size):
		super(LanguageModule, self).__init__()
		#self.word_embeddings = nn.Embedding(vocab_size, embedding_dim)
		self.word_embeddings, embedding_dim = create_emb_layer(
			weights_matrix, True)
		# The LSTM takes word embeddings as inputs, and outputs hidden states
		# with dimensionality hidden_dim.
		self.lstm = nn.LSTM(embedding_dim, hidden_dim,
							num_layers=1, batch_first=True)
		# The linear layer that maps from hidden state space to tag space
		self.hidden2tag = nn.Linear(hidden_dim, target_size)

	def forward(self, x):
		x = self.word_embeddings(x)
		self.lstm.flatten_parameters()
		lstm_out, _ = self.lstm(x)
		x = lstm_out[:, -1, :]
		x = self.hidden2tag(x)
		#x = F.log_softmax(x, dim=1)
		return x


class VisionModule(nn.Module):
	""" Vision Moddule"""

	def __init__(self):
		super(VisionModule, self).__init__()
		vgg = models.resnet18(pretrained=True)
		modules = list(vgg.children())[:-1]
		self.vgg_backbone = nn.Sequential(*modules)
		self.fc = nn.Linear(512, 4096)

	def forward(self, x):
		x = self.vgg_backbone(x)
		x = x.view(x.size(0), -1)
		x = self.fc(x)
		x = F.relu(x)
		return x


# class VisionModule(nn.Module):
# 	""" Vision Moddule"""

# 	def __init__(self):
# 		super(VisionModule, self).__init__()
# 		vgg = models.vgg16(pretrained=True)
# 		modules = list(vgg.children())[:-1]
# 		self.vgg_backbone = nn.Sequential(*modules)
# 		self.roi_pool = ops.RoIPool(output_size=(7, 7), spatial_scale=0.03125)
# 		self.fc = nn.Linear(75264, 4096)

# 	def forward(self, x, rois_sub, rois_obj):
# 		x = self.vgg_backbone(x)
# 		x_sub = self.roi_pool(x, rois_sub)
# 		x_obj = self.roi_pool(x, rois_obj)
		
# 		x = x.view(x.size(0), -1)
# 		x_sub = x_sub.view(x_sub.size(0), -1)
# 		x_obj = x_obj.view(x_obj.size(0), -1)
	
# 		x = torch.cat([x, x_sub, x_obj], dim=1)
# 		x = self.fc(x)
# 		x = F.relu(x)
# 		return x


class MFURLN(nn.Module):
	def __init__(self, num_classes=10):
		super(MFURLN, self).__init__()
		self.visual_module = VisionModule()
		self.language_module = LanguageModule(300, 500)

		self.fc_vm = self.fc1 = nn.Linear(4096, 500)
		self.fc_lm = self.fc1 = nn.Linear(500, 500)
		self.fc_sp = self.fc1 = nn.Linear(8, 500)

		self.fc1 = nn.Linear(1500, 100)
		#self.fc1_bn = nn.BatchNorm1d(4096)
		self.fc2 = nn.Linear(100, 1)

		#self.fc1_bn = nn.BatchNorm1d(4096)
		self.fc3 = nn.Linear(1600, 500)
		self.fc4 = nn.Linear(500, num_classes)

	def forward(self, img, spatial_locations, word_vectors):
		vm_out = self.visual_module(img)
		lm_out = self.language_module(word_vectors)

		# vm_out = vm_out.view(vm_out.size(0), -1)
		# lm_out = lm_out.view(lm_out.size(0), -1)
		# sp_out = spatial_locations.view(spatial_locations.size(0), -1)

		vm_out = self.fc_vm(vm_out)
		vm_out = F.relu(vm_out)
		lm_out = self.fc_lm(lm_out)
		lm_out = F.relu(lm_out)
		sp_out = self.fc_sp(spatial_locations)
		sp_out = F.relu(sp_out)

		# concat
		multi_model_features = torch.cat([vm_out, lm_out, sp_out], dim=1)

		# confidence subnetwork
		c = self.fc1(multi_model_features)
		x_c = F.relu(c)
		c = self.fc2(x_c)

		# relation subnetwork
		r = torch.cat([x_c, multi_model_features], dim=1)
		r = self.fc3(r)
		r = F.relu(r)
		r = self.fc4(r)

		return c, r


if __name__ == "__main__":
	model = MFURLN(70)
	# load pretrained weights
	checkpoint = torch.load('/Users/pranoyr/Desktop/model26.pth', map_location='cpu')
	model.load_state_dict(checkpoint['model_state_dict'])
	print("Model Restored")

