import numpy as np
def get_document_vectors(A):
    vectors = np.array(A)
    return vectors


def vector_norm(v):
    return np.linalg.norm(v)

def inner_product(v1,v2):
    return np.dot(v1,v2)

def cos_similarity(v1,v2):
    norm1 = vector_norm(v1)
    norm2 = vector_norm(v2)
    if norm1==0 or norm2==0:
        return 0
    return inner_product(v1,v2)/(norm1*norm2)


def normalize_vectors(A):
    norm = []
    for v in A:
        vn = vector_norm(v)
        if vn==0:
            norm.append(np.zeros_like(v))
        else:
            normalized_v = v/vn
            norm.append(normalized_v)
    return norm
    

def build_similarity_matrix(A):
    normalized = np.array(normalize_vectors(A))
    similarity = np.dot(normalized, normalized.T)
    return similarity