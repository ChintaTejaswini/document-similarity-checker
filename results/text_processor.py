# `clean_text()` – lowercase and remove punctuation.
# `tokenize()` – split text into individual words.
# `build_vocabulary()` – collect unique words.
# `build_feature_matrix()` – count each vocabulary word in every document.
import string
from collections import Counter
def clean_text(text):
    text = text.lower()
    table = str.maketrans("","",string.punctuation)
    text = text.translate(table)
    return text

def tokenize(text):
    words = text.split()
    return words

def build_vocab(doc):
    vocab = []
    seen = set()              # same order as before, but O(1) look-ups so large collections stay fast
    for text in doc:
        for word in text:
            if word not in seen:
                seen.add(word)
                vocab.append(word)
    return vocab

def build_feature_matrix(doc,vocab):
    feat_mat = []
    for text in doc:
        counts = Counter(text)            # one pass per document instead of text.count() per word
        feat_mat.append([counts[word] for word in vocab])
    return feat_mat


if __name__ == "__main__":
    doc = [
        "cat dog pet",
        "dog pet pet",
        "cat engine",
        "car cat engine"
    ]


    tokenized_docs = []
    for text in doc:
        clean = clean_text(text)
        token = tokenize(clean)
        tokenized_docs.append(token)

    vocab = build_vocab(tokenized_docs)

    feat = build_feature_matrix(tokenized_docs,vocab)
    print(vocab)
    print(feat)