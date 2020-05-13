# -*- coding: utf-8 -*-
"""utils.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1suUTaR_oAPuZSP-NLx6fYr05yVZ7cSeE
"""

import os; os.chdir('/content/drive/My Drive/Colab Notebooks/Lazy courses/Recurrent Neural Network')

import numpy as np
import string
import os
import sys
import operator
from nltk import pos_tag, word_tokenize
from datetime import datetime

def get_tags(s):
    tuples = pos_tag(word_tokenize(s))
    return [y for x, y in tuples]

def init_weight(Mi, Mo):
    return np.random.randn(Mi, Mo) / np.sqrt(Mi + Mo)

def all_parity_pairs(nbit):
    #total number of samples (Ntotal) will be a multiple of 100
    N = 2**nbit
    remainder = 100 - (N % 100)
    Ntotal = N + remainder
    X = np.zeros((Ntotal, nbit))
    Y = np.zeros(Ntotal)
    for ii in range(Ntotal):
        i = ii % N
        #now generate the ith sample 
        for j in range(nbit):
            if i % (2**(j+1)) != 0:
                i -= 2**j
                X[ii,j] = 1
        Y[ii] = X[ii].sum() % 2 
    return X, Y

def all_parity_pairs_with_sequence_labels(nbit):
    X, Y = all_parity_pairs(nbit)
    N, t = X.shape

    #we want every time step to have label
    Y_t = np.zeros(X.shape, dtype=np.int32)
    for n in range(N):
        ones_count = 0
        for i in range(t):
            if X[n, i] == 1:
                ones_count += 1
            if ones_count % 2 ==1:
                Y_t[n,i] = 1

    X = X.reshape(N, t, 1).astype(np.float32)
    return X, Y_t

def remove_punctuation(s):
    return s.translate(str.maketrans('','',string.punctuation))

def my_tokenizer(s):
    s = remove_punctuation(s)
    s = s.lower()
    return s.split()

def get_robert_frost():
    word2idx = {'START': 0, 'END': 1}
    current_idx = 2
    sentences = []
    for line in open('/content/drive/My Drive/Colab Notebooks/Lazy courses/NLP2/Markov Models/robert_frost.txt'):
        line = line.strip()
        if line:
            tokens = remove_punctuation(line.lower()).split()
            sentence = []
            for t in tokens:
                if t not in word2idx:
                    word2idx[t] = current_idx
                    current_idx += 1
                idx = word2idx[t]
                sentence.append(idx)
            sentences.append(sentence)
    return sentences, word2idx

def get_wikipedia_data(n_files, n_vocab, by_paragraph=False):

    wiki_data_location = '/content/drive/My Drive/Colab Notebooks/Lazy courses/NLP2/wiki_data'

    input_files = [f for f in os.listdir(wiki_data_location) if f.startswith('enwiki') and f.endswith('txt')]

    if len(input_files) == 0:
        print('No data files... quitting')
        exit()

    #return variables
    sentences = []
    word2idx = {'START':0, 'END':1}
    idx2word = ['START', 'END']
    current_idx = 2
    word_idx_count = {0: float('inf'), 1: float('inf')}

    if n_files is not None:
        input_files = input_files[:n_files]

    for f in input_files:
        print("reading:", f)
        for line in open(wiki_data_location+'/' + f):
            line = line.strip()
            #ignore headers, structured data, lists etc...
            if line and line[0] not in ('[', '*', '-', '|', '=', '{', '}'):
                if by_paragraph:
                    sentence_lines = [line]
                else:
                    sentence_lines = line.split('. ')

                for sentence in sentence_lines:
                    tokens = my_tokenizer(sentence)
                    for t in tokens:
                        if t not in word2idx:
                            word2idx[t] = current_idx
                            idx2word.append(t)
                            current_idx += 1
                        idx = word2idx[t]
                        word_idx_count[idx] = word_idx_count.get(idx, 0) + 1    
                    sentence_by_idx = [word2idx[t] for t in tokens]
                    sentences.append(sentence_by_idx)

    #restrict vocab size
    sorted_word_idx_count = sorted(word_idx_count.items(), key=operator.itemgetter(1), reverse=True)
    word2idx_small = {}
    new_idx = 0
    idx_new_idx_map = {}
    for idx, count in sorted_word_idx_count[:n_vocab]:
        word = idx2word[idx]
        print(word, count)
        word2idx_small[word] = new_idx
        idx_new_idx_map[idx] = new_idx
        new_idx += 1
    #let 'unknown' be the last token
    word2idx_small['UNKNOWN'] = new_idx
    unknown = new_idx

    #map old idx to new idx
    sentences_small = []
    for sentence in sentences:
        if len(sentence) > 1:
            new_sentence = [idx_new_idx_map[idx] if idx in idx_new_idx_map else unknown for idx in sentence]
            sentences_small.append(new_sentence)

    return sentences_small, word2idx_small

def find_analogies(w1, w2, w3, We, word2idx, idx2word):
    V, D = We.shape

    king = We[word2idx[w1]]
    man = We[word2idx[w2]]
    woman = We[word2idx[w3]]
    v0 = king - man + woman

    for dist in ('euclidean', 'cosine'):
        distances = pairwise_distances(v0.reshape(1, D), We, metric=dist).reshape(V)
        idx = distances.argsort()[:4]
        best_idx = -1
        keep_out = [word2idx[w] for w in (w1, w2, w3)]
        for i in idx:
            if i not in keep_out:
                best_idx = i
                break
        best_word = idx2word[best_idx]

        print("Closest match by", dist, "distance:", best_word)
        print(w1, "-", w2, "=", best_word, "-", w3)

def get_bigram_probs(sentences, V, start_idx, end_idx, smoothing=1):
    # structure of bigram probability matrix will be:
    # (last word, current word) --> probability
    # we will use add-1 smoothing
    # note: we will always ignore this from the END token
    bigram_probs = np.ones((V,V)) * smoothing
    
    for sentence in sentences:
        for i in range(len(sentence)):
            if i == 0:
                #beginning word
                bigram_probs[start_idx, sentence[i]] += 1
            else:
                #middle word
                bigram_probs[sentence[i-1], sentence[i]] += 1

            #if we are at the final word 
            #we update the bigram for last --> current 
            #and current --> END token
            if i == len(sentence) - 1:
                #final word
                bigram_probs[sentence[i], end_idx] += 1

    #normalize the counts along the rows to get probabilities
    bigram_probs /= bigram_probs.sum(axis=1, keepdims=True)
    return bigram_probs
